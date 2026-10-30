"""Functional tests: the main flows behave as documented."""


def test_health(http, base_url):
    r = http.get(f"{base_url}/health", timeout=5)
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_create_returns_the_stored_book(http, base_url, auth, book_data):
    data = book_data(tags=["fiction", "short"])
    r = http.post(f"{base_url}/books", json=data, headers=auth, timeout=5)
    assert r.status_code == 201
    book = r.json()
    assert isinstance(book["id"], int) and book["id"] >= 1
    assert {k: book[k] for k in data} == data
    assert r.headers["Location"] == f"/books/{book['id']}"


def test_read_by_id_without_a_key(http, base_url, create_book):
    book = create_book()
    r = http.get(f"{base_url}/books/{book['id']}", timeout=5)
    assert r.status_code == 200 and r.json() == book


def test_list_filters_by_author_in_id_order(http, base_url, create_book):
    first = create_book()
    second = create_book(author=first["author"], title="A Second Invented Title")
    create_book()                                            # another author: not listed
    r = http.get(f"{base_url}/books", params={"author": first["author"]}, timeout=5)
    page = r.json()
    assert r.status_code == 200
    assert page["items"] == [first, second] and page["total"] == 2
    assert (page["limit"], page["offset"]) == (20, 0)


def test_list_filters_by_tag(http, base_url, create_book):
    tagged = create_book(tags=["rare-tag-for-this-test", "fiction"])
    untagged = create_book(author=tagged["author"], tags=["fiction"])
    r = http.get(f"{base_url}/books", params={"author": tagged["author"], "tag": "rare-tag-for-this-test"}, timeout=5)
    assert [b["id"] for b in r.json()["items"]] == [tagged["id"]]
    assert untagged["id"] not in [b["id"] for b in r.json()["items"]]


def test_pagination_walks_through_all_books(http, base_url, create_book):
    author = create_book()["author"]
    for _ in range(4):
        create_book(author=author)
    seen = []
    for offset in (0, 2, 4):
        page = http.get(f"{base_url}/books", params={"author": author, "limit": 2, "offset": offset}, timeout=5).json()
        assert page["total"] == 5 and page["limit"] == 2 and page["offset"] == offset
        seen += [b["id"] for b in page["items"]]
    assert len(seen) == 5 and seen == sorted(seen) and len(set(seen)) == 5


def test_patch_changes_only_the_given_fields(http, base_url, auth, create_book):
    book = create_book()
    r = http.patch(f"{base_url}/books/{book['id']}", json={"year": 1999, "tags": []}, headers=auth, timeout=5)
    assert r.status_code == 200
    assert r.json() == {**book, "year": 1999, "tags": []}
    assert http.get(f"{base_url}/books/{book['id']}", timeout=5).json() == r.json()


def test_patch_to_its_own_isbn_is_allowed(http, base_url, auth, create_book):
    book = create_book()
    r = http.patch(f"{base_url}/books/{book['id']}", json={"isbn": book["isbn"]}, headers=auth, timeout=5)
    assert r.status_code == 200 and r.json() == book


def test_delete_removes_the_book(http, base_url, auth, create_book):
    book = create_book()
    r = http.delete(f"{base_url}/books/{book['id']}", headers=auth, timeout=5)
    assert r.status_code == 204 and r.content == b""
    assert http.get(f"{base_url}/books/{book['id']}", timeout=5).status_code == 404
    listed = http.get(f"{base_url}/books", params={"author": book["author"]}, timeout=5).json()
    assert listed["total"] == 0


def test_ids_are_not_reused_after_delete(http, base_url, auth, create_book):
    old = create_book()
    assert http.delete(f"{base_url}/books/{old['id']}", headers=auth, timeout=5).status_code == 204
    new = create_book(isbn=old["isbn"])                      # the ISBN is free again, the id is not
    assert new["id"] > old["id"]


def test_list_needs_no_key(http, base_url):
    assert http.get(f"{base_url}/books", timeout=5).status_code == 200
