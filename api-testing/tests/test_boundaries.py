"""Boundary tests: values on, just inside and just outside every documented limit."""
import pytest

from conftest import new_isbn
from isbn import isbn13_check_digit


@pytest.mark.parametrize("limit, status", [(0, 422), (1, 200), (100, 200), (101, 422)])
def test_limit_bounds(http, base_url, limit, status):
    r = http.get(f"{base_url}/books", params={"limit": limit}, timeout=5)
    assert r.status_code == status
    if status == 200:
        assert r.json()["limit"] == limit and len(r.json()["items"]) <= limit


@pytest.mark.parametrize("offset, status", [(-1, 422), (0, 200)])
def test_offset_bounds(http, base_url, offset, status):
    assert http.get(f"{base_url}/books", params={"offset": offset}, timeout=5).status_code == status


def test_offset_at_and_past_the_end(http, base_url, create_book):
    author = create_book()["author"]
    create_book(author=author)
    for offset in (1, 2, 50):
        page = http.get(f"{base_url}/books", params={"author": author, "offset": offset}, timeout=5).json()
        assert page["total"] == 2 and len(page["items"]) == max(0, 2 - offset)


@pytest.mark.parametrize("year, status", [(1449, 422), (1450, 201), (2100, 201), (2101, 422)])
def test_year_bounds(http, base_url, auth, book_data, year, status):
    assert http.post(f"{base_url}/books", json=book_data(year=year), headers=auth, timeout=5).status_code == status


@pytest.mark.parametrize("field, length, status", [
    ("title", 0, 422), ("title", 1, 201), ("title", 200, 201), ("title", 201, 422),
    ("author", 0, 422), ("author", 1, 201), ("author", 100, 201), ("author", 101, 422),
])
def test_text_length_bounds(http, base_url, auth, book_data, field, length, status):
    r = http.post(f"{base_url}/books", json=book_data(**{field: "x" * length}), headers=auth, timeout=5)
    assert r.status_code == status, r.text


@pytest.mark.parametrize("tags, status", [
    ([], 201), ([f"t{i}" for i in range(10)], 201), ([f"t{i}" for i in range(11)], 422),
    (["x" * 30], 201), (["x" * 31], 422), ([""], 422),
], ids=["none", "10-tags", "11-tags", "tag-30-chars", "tag-31-chars", "empty-tag"])
def test_tag_bounds(http, base_url, auth, book_data, tags, status):
    assert http.post(f"{base_url}/books", json=book_data(tags=tags), headers=auth, timeout=5).status_code == status


def test_every_wrong_check_digit_is_refused(http, base_url, auth, book_data):
    valid = new_isbn()
    for d in "0123456789":
        if d == valid[-1]:
            continue
        r = http.post(f"{base_url}/books", json=book_data(isbn=valid[:12] + d), headers=auth, timeout=5)
        assert r.status_code == 422, d
    assert http.post(f"{base_url}/books", json=book_data(isbn=valid), headers=auth, timeout=5).status_code == 201


def test_check_digit_zero_case(http, base_url, auth, book_data):
    # the wrap-around case of the formula: (10 - sum mod 10) mod 10 == 0
    isbn = next(i for i in (new_isbn() for _ in range(30)) if i.endswith("0"))
    assert isbn13_check_digit(isbn[:12]) == "0"
    assert http.post(f"{base_url}/books", json=book_data(isbn=isbn), headers=auth, timeout=5).status_code == 201
