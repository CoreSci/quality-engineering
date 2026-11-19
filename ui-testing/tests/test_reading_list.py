"""UI tests for the reading-list demo page.

Elements are found by role and label (as a user or assistive technology finds
them), and every check uses Playwright's auto-waiting ``expect``: no fixed sleeps,
no retries.
"""
import re

import pytest
from playwright.sync_api import expect


def add_book(page, title, pages, status="To read"):
    page.get_by_label("Title", exact=True).fill(title)
    page.get_by_label("Pages", exact=True).fill(str(pages))
    page.get_by_label("Status", exact=True).select_option(label=status)
    page.get_by_role("button", name="Add book").click()


def books(page):
    return page.get_by_role("list", name="Books").get_by_role("listitem")


def summary(page):
    return page.get_by_role("status")


# ------------------------------------------------------------------ page basics
def test_page_structure(app):
    expect(app).to_have_title("Reading list")
    expect(app.get_by_role("heading", level=1)).to_have_text("Reading list")
    expect(app.get_by_role("form", name="Add a book")).to_be_visible()
    expect(summary(app)).to_have_text("0 of 0 books shown, 0 pages")
    expect(books(app)).to_have_count(0)


def test_every_field_has_a_label(app):
    for label in ("Title", "Pages", "Status", "Show"):
        expect(app.get_by_label(label, exact=True)).to_be_visible()


# ------------------------------------------------------------------ adding books
def test_add_a_book(app):
    add_book(app, "An Invented Novel", 320, status="Reading")
    expect(books(app)).to_have_count(1)
    expect(books(app).first).to_contain_text("An Invented Novel (320 pages, Reading)")
    expect(summary(app)).to_have_text("1 of 1 books shown, 320 pages")


def test_form_is_cleared_and_focus_returns_to_title(app):
    add_book(app, "A Short Story Collection", 150)
    expect(app.get_by_label("Title", exact=True)).to_have_value("")
    expect(app.get_by_label("Pages", exact=True)).to_have_value("")
    expect(app.get_by_label("Title", exact=True)).to_be_focused()


def test_enter_key_submits_the_form(app):
    app.get_by_label("Title", exact=True).fill("Keyboard Only")
    app.get_by_label("Pages", exact=True).fill("99")
    app.get_by_label("Pages", exact=True).press("Enter")
    expect(books(app)).to_have_count(1)
    expect(summary(app)).to_have_text("1 of 1 books shown, 99 pages")


def test_totals_add_up(app):
    for i, pages in enumerate((1, 250, 5000), start=1):
        add_book(app, f"Volume {i}", pages)
    expect(summary(app)).to_have_text("3 of 3 books shown, 5251 pages")


def test_titles_are_shown_as_text_not_markup(app):
    add_book(app, "<b>Not bold</b>", 10)
    expect(books(app).first.locator(".book-title")).to_have_text("<b>Not bold</b>")
    expect(books(app).first.locator("b")).to_have_count(0)


# ------------------------------------------------------------------ input checks
@pytest.mark.parametrize("title, message", [
    ("", "Enter a title."),
    ("   ", "Enter a title."),
    ("x" * 101, "Use at most 100 characters."),
], ids=["empty", "blank", "101-chars"])
def test_title_is_checked(app, title, message):
    add_book(app, title, 100)
    title_field = app.get_by_label("Title", exact=True)
    expect(title_field).to_have_accessible_description(message)
    expect(title_field).to_have_attribute("aria-invalid", "true")
    expect(title_field).to_be_focused()
    expect(books(app)).to_have_count(0)


@pytest.mark.parametrize("pages, message", [
    ("", "Enter the number of pages as a whole number."),
    ("abc", "Enter the number of pages as a whole number."),
    ("12.5", "Enter the number of pages as a whole number."),
    ("-3", "Enter the number of pages as a whole number."),
    ("0", "Enter a number from 1 to 5000."),
    ("5001", "Enter a number from 1 to 5000."),
], ids=["empty", "letters", "decimal", "negative", "zero", "5001"])
def test_pages_are_checked(app, pages, message):
    add_book(app, "Some Title", pages)
    pages_field = app.get_by_label("Pages", exact=True)
    expect(pages_field).to_have_accessible_description(message)
    expect(pages_field).to_have_attribute("aria-invalid", "true")
    expect(books(app)).to_have_count(0)


@pytest.mark.parametrize("title, pages", [("x", 1), ("y" * 100, 5000)], ids=["minimums", "maximums"])
def test_limits_are_accepted(app, title, pages):
    add_book(app, title, pages)
    expect(books(app)).to_have_count(1)
    expect(app.get_by_label("Title", exact=True)).not_to_have_attribute("aria-invalid", "true")


def test_duplicate_title_is_refused_ignoring_case_and_spaces(app):
    add_book(app, "The Same Book", 100)
    add_book(app, "  the same BOOK ", 200)
    expect(app.get_by_label("Title", exact=True)).to_have_accessible_description("This book is already on the list.")
    expect(books(app)).to_have_count(1)


def test_error_clears_after_a_correct_entry(app):
    add_book(app, "", 100)
    expect(app.get_by_label("Title", exact=True)).to_have_accessible_description("Enter a title.")
    add_book(app, "Now With A Title", 100)
    expect(app.get_by_label("Title", exact=True)).to_have_accessible_description("")
    expect(books(app)).to_have_count(1)


# ------------------------------------------------------------------ list actions
def test_remove_removes_the_right_book(app):
    for title in ("First", "Second", "Third"):
        add_book(app, title, 100)
    app.get_by_role("button", name="Remove Second").click()
    expect(books(app)).to_have_count(2)
    expect(books(app)).to_contain_text([re.compile("^First"), re.compile("^Third")])
    expect(summary(app)).to_have_text("2 of 2 books shown, 200 pages")


def test_filter_by_status(app):
    add_book(app, "Unread One", 100, status="To read")
    add_book(app, "Current One", 200, status="Reading")
    add_book(app, "Finished One", 300, status="Done")
    app.get_by_label("Show", exact=True).select_option(label="Done")
    expect(books(app)).to_have_count(1)
    expect(books(app).first).to_contain_text("Finished One")
    expect(summary(app)).to_have_text("1 of 3 books shown, 300 pages")
    app.get_by_label("Show", exact=True).select_option(label="All")
    expect(summary(app)).to_have_text("3 of 3 books shown, 600 pages")


# ------------------------------------------------------------------ persistence
def test_list_survives_a_reload(app):
    add_book(app, "Kept After Reload", 123, status="Done")
    app.reload()
    expect(books(app)).to_have_count(1)
    expect(books(app).first).to_contain_text("Kept After Reload (123 pages, Done)")
    expect(summary(app)).to_have_text("1 of 1 books shown, 123 pages")


def test_removal_survives_a_reload(app):
    add_book(app, "Gone Soon", 50)
    app.get_by_role("button", name="Remove Gone Soon").click()
    app.reload()
    expect(books(app)).to_have_count(0)


# ------------------------------------------------------------------ the test set-up itself
def test_only_local_requests(app, blocked_requests):
    """The page makes no request outside 127.0.0.1; the guard fixture enforces it."""
    add_book(app, "Local Only", 1)
    expect(books(app)).to_have_count(1)
    assert blocked_requests == []


def test_guard_blocks_non_local_requests(page, site_url, blocked_requests):
    """The guard itself: a request to another host is aborted and recorded."""
    page.goto(site_url)
    outcome = page.evaluate("() => fetch('http://example.invalid/').then(() => 'loaded', () => 'blocked')")
    assert outcome == "blocked"
    assert any("example.invalid" in url for url in blocked_requests)
    blocked_requests.clear()                       # expected here; don't fail the fixture check
