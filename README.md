# Quality engineering

[![api-tests](https://github.com/CoreSci/quality-engineering/actions/workflows/api-tests.yml/badge.svg?branch=main)](https://github.com/CoreSci/quality-engineering/actions/workflows/api-tests.yml)

Testing as an engineering discipline: deciding what to test from the risks, testing it at the right level, and showing what was tested. Every example runs locally and in CI, against small systems written for this repository.

## Scope

- **In:** API testing (functional, negative, boundary, and contract tests derived from an OpenAPI document), risk-based test plans, requirements traceability, continuous integration.
- **Out:** performance and load testing, security testing, and testing any third-party site or service. Everything here runs against systems written for this repository, on the local machine.

## Structure

| Folder | What it is |
|---|---|
| [`api-testing/`](api-testing/) | A small FastAPI service (local only) and its pytest suite: functional, negative, boundary and OpenAPI contract tests, a test plan, Docker and CI |

## Run

Each folder has its own README with the details. In short, for `api-testing/`:

```bash
cd api-testing
python -m pip install -r requirements-test.txt
python -m pytest -q          # starts the service on 127.0.0.1 for the test session
```

or run the service with `docker compose up --build` (port published on 127.0.0.1 only) and point the tests at it. CI: the [`api-tests`](.github/workflows/api-tests.yml) workflow, on Python 3.11 to 3.14 and against the Docker image.

## Applied example: tests that live with their code

Tests belong next to the code they test, so the tests of other projects are not copied here. The mzML tools in the lab-informatics repository show the same practice on a larger codebase:

- [Test plan](https://github.com/CoreSci/lab-informatics/blob/main/data-decoders/mzml-reader/docs/test-plan.md): risks, environment, entry and exit criteria, known gaps.
- [Traceability matrix](https://github.com/CoreSci/lab-informatics/blob/main/data-decoders/mzml-reader/docs/traceability-matrix.md): a snapshot generated from the JUnit results of a real test run.
- [Requirements](https://github.com/CoreSci/lab-informatics/blob/main/data-decoders/mzml-reader/traceability/requirements.tsv): the list the matrix is built from. The matrix shows the tests that verify each requirement, and lists the one that has no automated test yet as a known gap.
- [CI workflow](https://github.com/CoreSci/lab-informatics/blob/main/.github/workflows/tests.yml): the suites on every supported Python version.

## Approach

- **Risk first:** test hardest where a defect would be silent.
- **Tests next to the code** they test.
- **Contracts from the source:** contract tests derive from the system's own OpenAPI document, so drift fails the build.
- **Deterministic:** synthetic data generated per run; no fixed waits in the tests and no retries that hide flakiness.
- **Pinned:** dependencies, Docker base images and CI actions.
- **Known gaps written down** in each test plan.

## Status (2026-10-26)

- `api-testing/`: 106 tests, passing on Python 3.11, 3.12, 3.13 and 3.14 and against the Docker image (local Docker runs before CI was added; CI runs on every push to `main` and on pull requests).
- The systems under test are small and in memory, written to be tested, not production services. No performance or security testing. CI is Linux only.
