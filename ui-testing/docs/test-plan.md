# Test plan: reading-list page (UI)

| | |
|---|---|
| Version | 1.0 |
| Date | 2026-10-30 |
| Covers | `ui-testing/site/` (the reading-list page: `index.html`, `app.js`, `style.css`) |
| Results | The JUnit report of every CI run (artifact of the `ui-tests` workflow, kept 7 days); traces and screenshots of failed tests (kept 7 days) |

## 1. Purpose and scope

This plan says what is tested, why, how, and what is **not** tested. The page is a small system written for this repository so that the browser tests have something real to run against.

**In scope:**
- what a user sees and does in the browser: adding, checking, removing and filtering books;
- the summary;
- persistence across a reload;
- keyboard submission;
- the accessibility hooks the tests rely on: labels, roles, error messages linked to their fields, invalid-field marking;
- the test set-up's own guarantee that no request leaves 127.0.0.1.

**Out of scope:** visual design and pixel comparison, browsers other than Chromium, mobile layouts, performance, security, and any site other than this page.

## 2. Approach: risk-based

| Risk | Impact | How it is tested | Residual risk |
|---|---|---|---|
| Bad input accepted (empty or long title, duplicate, pages not a whole number or out of range) | High: wrong data kept silently | One test per rule, plus the limits on both sides; each checks the message, the invalid marking, and that nothing was added | Rules not written down are not tested |
| Wrong totals or wrong item removed | High: silent | Totals compared with hand-computed sums; removal of a middle item checked by name | — |
| Data lost on reload | Medium | Add and remove, then reload, then check the list | Other storage problems (quota, private mode) not tested |
| Markup in a title runs as HTML | Medium | A title containing tags must appear as text, with no element created | Other injection paths not tested |
| Error messages not reachable by assistive technology | Medium | Messages are checked as the field's *accessible description*, not by CSS selector, so an unlinked message fails | No screen-reader or full accessibility audit |
| Tests depend on the network or a third-party site | Medium | Every request passes a guard; non-local requests are aborted and fail the test; the guard has its own test | — |
| Flaky tests (timing) | Medium | Auto-waiting `expect` only; no fixed sleeps; no retries, so flakiness shows instead of hiding | Real timing differences on slow machines |
| The suite is too weak | Medium | Six defects were injected on purpose into a copy of the page (empty title accepted, totals off by one, wrong item removed, no persistence, title as markup, unlinked error message); each made the suite fail | Defect types not anticipated |

## 3. Test levels and techniques

- **End-to-end browser tests** (pytest-playwright, Chromium, headless) against the page served on 127.0.0.1 by the test session.
- **Locators by role and label**, matched exactly.
- **Boundary values** for title length and pages.
- **Negative tests** for every input rule.
- **State tests** across a reload.

## 4. Environment

- **CI:** GitHub Actions workflow `ui-tests`, `ubuntu-24.04`, job inside `mcr.microsoft.com/playwright/python:v1.64.1-noble` pinned by digest. The image brings Python 3.12.3 and the browser builds for Playwright 1.64.1.
- **Dependencies:** pinned with `==` in `requirements.txt`; Playwright 1.64.1 matches the image version.
- **Browser settings fixed by the tests:** locale `en-US`, time zone UTC, viewport 1280×800, light colour scheme, reduced motion.
- **Before the workflow was added:** the suite passed (26 tests) in the pinned image on 2026-10-30.

## 5. Entry and exit criteria

- **Entry:** the change is complete, and the suite runs in the pinned image.
- **Exit:** every test passes in CI; no test is skipped; no non-local request was attempted.

## 6. Reproducibility risks

1. **Browser builds:** tied to the Playwright version. In CI they come with the pinned image. On a developer machine, `playwright install` downloads them from Playwright's own servers at install time; that download is not pinned by a checksum here.
2. **The image itself:** pinned by digest. The digest fixes the image, but the image's operating-system packages were chosen by its publisher.
3. **Fonts and rendering:** they differ between machines, so the tests assert text, roles and states, never pixels.
4. **Timing:** auto-waiting only, no sleeps and no retries. A timing problem fails the test instead of being hidden.
5. **Locale and time zone:** set explicitly in the browser context; the page shows no dates.
6. **Headless vs headed:** the tests run headless. Headed runs (for debugging) can differ slightly in focus and timing.
7. **Frequent Playwright releases:** versions are pinned and updated on purpose, with the image tag, the image digest and the package pins changed together.

## 7. Known gaps

- Chromium only; no Firefox, WebKit or mobile emulation.
- One Python version (the image's 3.12.3); Linux only in CI.
- The local-machine route (own Python plus `playwright install`) was not run for this release.
- No visual comparison and no full accessibility audit.

## 8. Change history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-30 | First version |
