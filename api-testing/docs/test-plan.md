# Test plan: Bookshelf API

| | |
|---|---|
| Version | 1.0 |
| Date | 2026-10-26 |
| Covers | `api-testing/service/` (the Bookshelf service: `app.py`, `isbn.py`, `Dockerfile`) |
| Results | The JUnit reports of every CI run (artifacts of the `api-tests` workflow, kept 7 days) |

## 1. Purpose and scope

This plan says what is tested, why, how, and what is **not** tested. The Bookshelf service is a small system written for this repository so that the tests have something real to run against: an in-memory collection of invented books with an HTTP API. The tests check that the API behaves as its own OpenAPI document says, and that wrong input and wrong use are refused without side effects.

**In scope:**
- every documented endpoint (`/health`, `/books`, `/books/{book_id}`) and status code;
- input rules: required fields, types, lengths, year range, tags, ISBN-13 check digit, unknown fields, nulls;
- API key protection of write operations;
- pagination and filtering;
- the OpenAPI document itself, compared with a committed snapshot;
- the Docker image: build, health check, port publishing, and the full suite run against the container.

**Out of scope:** performance and load, security testing beyond the API key check, persistence (the service keeps everything in memory), concurrent clients, and any system other than this service.

## 2. Approach: risk-based

Effort goes where a defect would be silent, and so most harmful: a wrong response that a client accepts without noticing. A defect that produces a clear error is the lesser risk.

| Risk | Impact | How it is tested | Residual risk |
|---|---|---|---|
| Responses drift from the documented contract (fields added, removed or retyped) | High: silent for clients | Every documented (operation, status) pair has a scenario; each response is checked against the JSON Schema its OpenAPI document declares, strictly (undeclared properties fail); the live document must equal the committed snapshot | Behaviour that the document can't express (e.g. ordering rules) is covered only by the functional tests |
| Bad input accepted (wrong ISBN check digit, out-of-range year, unknown or null fields) | High: silent data corruption | Negative tests for each rule; boundary tests on, just inside and just outside every limit; every wrong check digit for one ISBN | Rules not written down are not tested |
| Write operations reachable without the key | High | No key and a wrong key on every write endpoint: 401, and the data is unchanged | Key handling is a single shared key; no rotation, no rate limiting |
| Refused writes leave side effects | Medium | After each 401, 404, 409 and 422 on a write, the tests read the data back and check that nothing changed or was created | — |
| Pagination off by one | Medium | Walking all pages with limit 2; offsets at and past the end; limit 0, 1, 100, 101 | — |
| Tests depend on each other or on earlier runs | Medium | Each run uses its own block of synthetic ISBNs and author names; every list check filters on data the test created | A long-running local service reused across many runs could, very rarely, see an ISBN block repeat (1 in 100,000 for any two runs against the same running service: the block is drawn uniformly from 100,000 values) |
| Docker image differs from the tested code | Medium | CI builds the image and runs the full suite against the container, through the port published on 127.0.0.1 | — |
| The contract check itself is too weak | Medium | A self-test feeds the check a response with an extra property and expects it to fail. During development, four deliberately injected defects (no check-digit rule, an extra response field, an unprotected delete, a pagination off-by-one) were each caught by the suite | Defect types not anticipated |

## 3. Test levels and techniques

- **Unit tests** for the ISBN-13 check digit, with values computed by hand.
- **Functional tests** over HTTP: create, read, list with filters, paginate, update, delete; ids are never reused.
- **Negative tests:** 401, 404, 405, 409 and 422 cases, each followed by a read-back to show that nothing changed.
- **Boundary tests:** each documented limit at, inside and outside its edge.
- **Contract tests** derived from the service's own OpenAPI document (3.1): schema check of every documented response, snapshot comparison, and a completeness check (every documented response has a scenario, and no scenario returns an undocumented status).
- **Container smoke test:** the same suite against the Docker image.

## 4. Environment

- **CI:** GitHub Actions workflow `api-tests`, `ubuntu-24.04`.
  - Job `pytest`: Python 3.11, 3.12, 3.13 and 3.14; the service runs as a plain process bound to 127.0.0.1.
  - Job `docker-smoke`: the image is built and started with its port published on 127.0.0.1 only; the suite runs against it on Python 3.12.
- **Dependencies:** pinned with `==` in `service/requirements.txt` and `requirements-test.txt`; the same set installs on all four Python versions. The Docker base image is pinned by digest.
- **API key:** generated for each run; never stored in the repository.
- **Network:** the tests only talk to 127.0.0.1 or localhost, and refuse any other address.
- **Before the workflow was added:** the suite passed (106 tests) in Docker `python:3.x-slim` on 3.11, 3.12, 3.13 and 3.14, and against the built image, on 2026-10-26.

## 5. Entry and exit criteria

- **Entry:** the change is complete, and the suite runs locally on at least one supported version.
- **Exit:** every test passes on every Python version in the CI matrix and in the Docker smoke test; the OpenAPI snapshot matches the live document; no test is skipped.

## 6. Test data

All records are invented. ISBNs used by the tests are synthetic, for demonstration only: a per-run block of numbers with valid check digits, taken from the 979-9 range, which was unassigned according to the sources consulted on 2026-10-26 (they list 979-0, 979-8 and 979-10 to 979-13 as assigned). The registration authority's official range file could not be read that day, so this is not confirmed by it.

## 7. Known gaps

- **Toy service:** in memory, one process, no persistence; nothing about databases, restarts or concurrent writers is tested.
- **Security:** only the presence and correctness of the API key is tested; no penetration, fuzzing or rate-limit testing.
- **Performance:** no timing or load requirements.
- **Property-based testing:** not included; inputs are chosen by hand from the documented limits.
- **Platforms:** CI is Linux only.

## 8. Change history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-26 | First version |
