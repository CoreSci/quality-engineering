"""Negative tests: wrong input and wrong use are refused, and refused writes change nothing."""
import pytest

WRITES = [("POST", "/books"), ("PATCH", "/books/{id}"), ("DELETE", "/books/{id}")]


def _count(http, base_url, author):
    return http.get(f"{base_url}/books", params={"author": author}, timeout=5).json()["total"]


@pytest.mark.parametrize("method, path", WRITES)
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}], ids=["no-key", "wrong-key"])
def test_writes_need_the_right_key(http, base_url, create_book, book_data, method, path, headers):
    book = create_book()
    body = book_data() if method == "POST" else ({"year": 1990} if method == "PATCH" else None)
    r = http.request(method, base_url + path.format(id=book["id"]), json=body, headers=headers, timeout=5)
    assert r.status_code == 401 and r.json() == {"detail": "missing or wrong API key"}
    assert http.get(f"{base_url}/books/{book['id']}", timeout=5).json() == book     # unchanged
    if method == "POST":
        assert _count(http, base_url, body["author"]) == 0                            # nothing created


@pytest.mark.parametrize("method, body", [("GET", None), ("PATCH", {"year": 1990}), ("DELETE", None)])
def test_unknown_id_is_404(http, base_url, auth, method, body):
    r = http.request(method, f"{base_url}/books/999999999", json=body, headers=auth, timeout=5)
    assert r.status_code == 404 and r.json() == {"detail": "no book with id 999999999"}


def test_duplicate_isbn_on_create_is_409_and_creates_nothing(http, base_url, auth, create_book, book_data):
    book = create_book()
    data = book_data(isbn=book["isbn"])
    r = http.post(f"{base_url}/books", json=data, headers=auth, timeout=5)
    assert r.status_code == 409 and book["isbn"] in r.json()["detail"]
    assert _count(http, base_url, data["author"]) == 0


def test_patch_to_another_books_isbn_is_409(http, base_url, auth, create_book):
    a, b = create_book(), create_book()
    r = http.patch(f"{base_url}/books/{b['id']}", json={"isbn": a["isbn"]}, headers=auth, timeout=5)
    assert r.status_code == 409
    assert http.get(f"{base_url}/books/{b['id']}", timeout=5).json() == b


@pytest.mark.parametrize("change", [
    {"isbn": "9799000000001"},                  # wrong check digit (the valid one is computed in the tests below)
    {"isbn": "979900000000X"},                  # not all digits
    {"isbn": "979900000000"},                   # 12 digits
    {"year": "nineteen ninety"},                # wrong type
    {"title": "   "},                           # blank
    {"tags": "fiction"},                        # not a list
    {"publisher": "Nobody"},                    # unknown field
], ids=["isbn-check-digit", "isbn-letters", "isbn-12-digits", "year-type", "blank-title", "tags-type", "unknown-field"])
def test_invalid_create_is_422_and_creates_nothing(http, base_url, auth, book_data, change):
    data = book_data(**change)
    r = http.post(f"{base_url}/books", json=data, headers=auth, timeout=5)
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)
    assert _count(http, base_url, data["author"]) == 0


@pytest.mark.parametrize("field", ["title", "author", "year", "isbn"])
def test_missing_required_field_is_422(http, base_url, auth, book_data, field):
    data = book_data()
    del data[field]
    r = http.post(f"{base_url}/books", json=data, headers=auth, timeout=5)
    assert r.status_code == 422
    assert any(e["loc"][-1] == field for e in r.json()["detail"])


@pytest.mark.parametrize("field", ["title", "author", "year", "isbn", "tags"])
def test_patch_to_null_is_422_and_changes_nothing(http, base_url, auth, create_book, field):
    book = create_book()
    r = http.patch(f"{base_url}/books/{book['id']}", json={field: None}, headers=auth, timeout=5)
    assert r.status_code == 422
    assert http.get(f"{base_url}/books/{book['id']}", timeout=5).json() == book


def test_malformed_json_is_422(http, base_url, auth):
    r = http.post(f"{base_url}/books", data=b'{"title": "unterminated',
                  headers={**auth, "Content-Type": "application/json"}, timeout=5)
    assert r.status_code == 422


@pytest.mark.parametrize("method, path", [("PUT", "/books/1"), ("DELETE", "/books"), ("POST", "/health")])
def test_wrong_method_is_405(http, base_url, auth, method, path):
    assert http.request(method, base_url + path, headers=auth, timeout=5).status_code == 405


def test_non_integer_id_is_422(http, base_url):
    assert http.get(f"{base_url}/books/abc", timeout=5).status_code == 422


def test_unknown_path_is_404(http, base_url):
    assert http.get(f"{base_url}/shelves", timeout=5).status_code == 404
