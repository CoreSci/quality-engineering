# API testing: the Bookshelf service

A small HTTP API written for this repository, and the test suite that checks it: functional, negative, boundary and contract tests, run locally, in Docker and in CI.

**Problem it shows:** an API is a contract. Clients rely on its status codes, fields and limits, and a change that breaks them often fails silently on the client's side. This suite derives its contract checks from the service's own OpenAPI document, so any drift between what the API says and what it does fails the build.

## The service

`service/app.py` (FastAPI) keeps an in-memory collection of invented books. Reading is open; writing needs the `X-API-Key` header to match the service's `BOOKSHELF_API_KEY` environment variable.

| Endpoint | What it does |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `GET /books` | List, in id order. `limit` 1–100 (default 20), `offset` ≥ 0, optional exact `author` and `tag` filters; returns `items`, `total`, `limit`, `offset` |
| `GET /books/{book_id}` | One book, or 404 |
| `POST /books` | Create (key required): `title` 1–200 characters, `author` 1–100, `year` 1450–2100, `isbn` 13 digits with a valid ISBN-13 check digit and unique, `tags` up to 10 of 1–30 characters. Unknown fields are refused. 201 with a `Location` header; 409 for a duplicate ISBN; 422 for invalid input |
| `PATCH /books/{book_id}` | Partial update (key required); fields may be left out but not set to null |
| `DELETE /books/{book_id}` | Delete (key required); 204. Ids are never reused |

The full contract is the OpenAPI document the service serves at `/openapi.json`. A copy is committed as [`openapi/openapi.json`](openapi/openapi.json).

## The tests

| File | What it checks |
|---|---|
| [`tests/test_functional.py`](tests/test_functional.py) | Create, read, list, filter, paginate, update, delete; ids not reused |
| [`tests/test_negative.py`](tests/test_negative.py) | 401 without or with a wrong key, 404, 405, 409, 422 (check digit, types, blanks, nulls, unknown fields, malformed JSON). After every refused write, the data is read back to show that nothing changed |
| [`tests/test_boundaries.py`](tests/test_boundaries.py) | Every documented limit on, just inside and just outside its edge; every wrong check digit for one ISBN; the check-digit-0 case |
| [`tests/test_contract.py`](tests/test_contract.py) | Every documented (operation, status) pair has a scenario, and each response is checked against the JSON Schema the OpenAPI document declares for it, strictly (undeclared properties fail). The live document must equal the committed snapshot |
| [`tests/test_isbn.py`](tests/test_isbn.py) | The ISBN-13 check digit, against values computed by hand |

The test plan, with the risks behind these choices and the known gaps, is in [`docs/test-plan.md`](docs/test-plan.md).

**Test data:** every record is invented. ISBNs are synthetic, for demonstration only: valid check digits, taken from the 979-9 range, which was unassigned according to the sources consulted on 2026-10-26. Each run uses its own block of numbers, so tests don't depend on each other.

## Run

Requires Python 3.11–3.14 (the versions tested) or Docker. All commands run from `api-testing/`.

**Tests, with the service started by the test session itself** (on 127.0.0.1, a free port, with a key generated for the run):

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q
```

**The service in Docker, then the tests against it:**

```bash
cp .env.example .env          # then replace the placeholder with a key of your choice
                              # Windows: `copy .env.example .env` (cmd) or `Copy-Item .env.example .env` (PowerShell)
docker compose up --build -d
BOOKSHELF_BASE_URL=http://127.0.0.1:8000 BOOKSHELF_API_KEY=<the same key> python -m pytest -q
docker compose down
```

The port is **published on 127.0.0.1 only**, so the service can't be reached from other machines. Inside the container the server listens on all of the container's own interfaces (`--host 0.0.0.0`): Docker's port publishing forwards traffic to the container's network interface, not to its loopback, so a server bound to the container's 127.0.0.1 would be unreachable even from the host. The image runs as a non-root user; compose and CI start it with a read-only file system.

**After an intended API change**, regenerate the contract snapshot, review the diff and commit it:

```bash
python tools/export_openapi.py
```

## CI

The `api-tests` workflow ([`.github/workflows/api-tests.yml`](../.github/workflows/api-tests.yml)) runs on every push to `main` and on pull requests:

- **`pytest` job:** Python 3.11, 3.12, 3.13 and 3.14 on `ubuntu-24.04`; the service runs as a plain process on 127.0.0.1.
- **`docker-smoke` job:** builds the image, starts it with the port published on 127.0.0.1 only, waits for its health check, and runs the whole suite against the container.

The API key is generated for each run and masked in the log; there are no secrets. Actions are pinned to commit SHAs, the token is read-only, and JUnit reports are kept as artifacts for 7 days.

## Testing status (2026-10-26)

- Before the workflow was added, the suite passed (106 tests) in Docker `python:3.x-slim` on Python 3.11, 3.12, 3.13 and 3.14, and against the built image through `127.0.0.1`.
- The suite caught each of four defects injected on purpose during development: no check-digit rule, an extra field in responses, an unprotected delete, and a pagination off-by-one.
- **Limits:** a toy service, in memory, single process. No performance, load or security testing beyond the API key check. CI is Linux only.
