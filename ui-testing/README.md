# UI testing: the reading-list page

A small static web page written for this repository, and the browser tests that check it, with Playwright and pytest. The page is served on 127.0.0.1 by the test session itself; the tests never reach any other host.

**Problem it shows:** UI tests often fail for reasons that have nothing to do with the page: brittle selectors, fixed sleeps, a different browser build or locale. These tests find elements the way a user or a screen reader does (by role and label), wait for conditions instead of sleeping, and run in a pinned browser environment, so a red test points at the page.

## The page

[`site/`](site/) holds a reading list in plain HTML, CSS and JavaScript, with no external assets:
- add a book with a **title** (1–100 characters, not already on the list, ignoring case and surrounding spaces), a number of **pages** (a whole number from 1 to 5000) and a **status**;
- a message under each field explains what's wrong, linked to the field, and the field is marked invalid;
- remove a book, filter the list by status, and see a summary (`N of M books shown, P pages`);
- the list is kept in the browser's `localStorage`, so it survives a reload.

## The tests

[`tests/test_reading_list.py`](tests/test_reading_list.py), 26 tests:

| Area | What is checked |
|---|---|
| Structure | Page title and headings; the form found by its accessible name; every field has a label |
| Adding books | A book appears with its details; the form is cleared and focus returns to Title; Enter submits; page totals add up; a title containing markup is shown as text |
| Input checks | Each rule for title and pages: the message is the field's accessible description, the field is marked invalid, nothing is added. Limits (1 and 100 characters, 1 and 5000 pages) are accepted; duplicate titles are refused; a message clears after a correct entry |
| List actions | Remove takes out the right book; the status filter and the summary agree |
| Persistence | Added and removed books survive a reload |
| Set-up | No request leaves 127.0.0.1; the guard that enforces this is itself tested |

How they are written:
- **Locators by role and label** (`get_by_role`, `get_by_label` with exact names).
- **Waiting:** Playwright's auto-waiting `expect` only; no fixed sleeps, no retries.
- **Network guard:** every request goes through a route handler that aborts and records anything not addressed to 127.0.0.1 or localhost, and the test fails.
- **Fixed browser settings:** locale `en-US`, time zone UTC, viewport 1280×800, light colour scheme, reduced motion.

The test plan, with the risks behind these choices and the known gaps, is in [`docs/test-plan.md`](docs/test-plan.md).

## Run

**In the Playwright container** (how CI runs them; browsers are already in the image):

```bash
docker run --rm -it -v "$PWD:/work" -w /work \
  mcr.microsoft.com/playwright/python:v1.64.1-noble \
  sh -c "pip install -r requirements.txt && python -m pytest -q"
```

**On your own machine** (Python 3.12 with Playwright 1.64.1; the browser download is Playwright's own):

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m pytest -q
```

Traces and screenshots are written to `test-results/` **only for failed tests**. Open a trace with `python -m playwright show-trace test-results/<test>/trace.zip`.

## CI

The `ui-tests` workflow ([`.github/workflows/ui-tests.yml`](../.github/workflows/ui-tests.yml)) runs on every push to `main` and on pull requests:
- **Environment:** inside `mcr.microsoft.com/playwright/python:v1.64.1-noble`, pinned by digest (Python 3.12.3 and the matching browser builds), on `ubuntu-24.04`.
- **Artifacts:** the JUnit report on every run; traces and screenshots only when a test fails. Both are kept 7 days.
- **Security:** actions pinned to commit SHAs, read-only token, no secrets.

## Testing status (2026-10-30)

- **Before the workflow was added:** the 26 tests passed in the pinned container image (Python 3.12.3, Chromium 156).
- **Injected defects:** six were injected on purpose into a copy of the page, and each made the suite fail:
  - an empty title accepted;
  - totals off by one;
  - Remove taking out the wrong book;
  - no persistence;
  - a title inserted as markup;
  - an error message not linked to its field.
- **Limits:**
  - Chromium only;
  - one Python version (the image's 3.12.3);
  - Linux only;
  - the local-machine route above (own Python plus `playwright install`) was not run for this release;
  - no visual (pixel) comparison;
  - no cross-browser or mobile testing.
