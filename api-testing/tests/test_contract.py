"""Contract tests derived from the service's own OpenAPI document.

* The live document must equal the committed snapshot (``openapi/openapi.json``), so
  any change to the API surface fails the build until the snapshot is updated on
  purpose: ``python tools/export_openapi.py``.
* Every documented (operation, status) pair has a scenario below, and every scenario's
  response is checked against the JSON Schema the document declares for that status,
  strictly: properties the document doesn't declare count as a failure.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import requests
from jsonschema import Draft202012Validator

SNAPSHOT = Path(__file__).resolve().parent.parent / "openapi" / "openapi.json"


@pytest.fixture(scope="module")
def live_doc(base_url):
    with requests.Session() as s:
        s.trust_env = False
        r = s.get(f"{base_url}/openapi.json", timeout=5)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def snapshot():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def _strict(node):
    """Copy of a schema where every object with declared properties forbids undeclared ones."""
    node = copy.deepcopy(node)

    def walk(n):
        if isinstance(n, dict):
            if "properties" in n and "additionalProperties" not in n:
                n["additionalProperties"] = False
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(node)
    return node


def _documented_pairs(doc):
    return {(method.upper(), path, int(code))
            for path, ops in doc["paths"].items() for method, op in ops.items()
            for code in op["responses"]}


def check_response(doc, method, path, response):
    """Assert that the response matches what the document declares for it."""
    op = doc["paths"][path][method.lower()]
    declared = op["responses"].get(str(response.status_code))
    assert declared is not None, f"{method} {path} returned undocumented status {response.status_code}"
    content = declared.get("content", {})
    if not content:
        assert response.content == b"", "a response documented without a body has one"
        return
    assert response.headers["Content-Type"].startswith("application/json")
    schema = {**_strict(content["application/json"]["schema"]), "components": _strict(doc["components"])}
    errors = sorted(Draft202012Validator(schema).iter_errors(response.json()), key=str)
    assert not errors, "; ".join(e.message for e in errors[:5])


# ------------------------------------------------------------------ the snapshot
def test_live_document_matches_the_snapshot(live_doc, snapshot):
    assert live_doc == snapshot, ("the API's OpenAPI document changed; if intended, run "
                                  "`python tools/export_openapi.py` and commit the new snapshot")


def test_document_basics(snapshot):
    assert snapshot["openapi"].startswith("3.1.")
    assert snapshot["info"]["title"] == "Bookshelf"
    assert snapshot["components"]["securitySchemes"]["APIKeyHeader"]["name"] == "X-API-Key"


# ------------------------------------------------------------------ scenarios
# (method, documented path, expected status, how to produce it)
def _book(c):
    return c.create_book()


SCENARIOS = [
    ("GET", "/health", 200, lambda c: c.get("/health")),
    ("GET", "/books", 200, lambda c: c.get("/books", params={"limit": 5})),
    ("GET", "/books", 422, lambda c: c.get("/books", params={"limit": 0})),
    ("POST", "/books", 201, lambda c: c.post("/books", json=c.book_data())),
    ("POST", "/books", 401, lambda c: c.post("/books", json=c.book_data(), key=False)),
    ("POST", "/books", 409, lambda c: c.post("/books", json=c.book_data(isbn=_book(c)["isbn"]))),
    ("POST", "/books", 422, lambda c: c.post("/books", json=c.book_data(year=1000))),
    ("GET", "/books/{book_id}", 200, lambda c: c.get(f"/books/{_book(c)['id']}")),
    ("GET", "/books/{book_id}", 404, lambda c: c.get("/books/999999999")),
    ("GET", "/books/{book_id}", 422, lambda c: c.get("/books/abc")),
    ("PATCH", "/books/{book_id}", 200, lambda c: c.patch(f"/books/{_book(c)['id']}", json={"year": 1980})),
    ("PATCH", "/books/{book_id}", 401, lambda c: c.patch(f"/books/{_book(c)['id']}", json={"year": 1980}, key=False)),
    ("PATCH", "/books/{book_id}", 404, lambda c: c.patch("/books/999999999", json={"year": 1980})),
    ("PATCH", "/books/{book_id}", 409, lambda c: c.patch(f"/books/{_book(c)['id']}", json={"isbn": _book(c)["isbn"]})),
    ("PATCH", "/books/{book_id}", 422, lambda c: c.patch(f"/books/{_book(c)['id']}", json={"title": ""})),
    ("DELETE", "/books/{book_id}", 204, lambda c: c.delete(f"/books/{_book(c)['id']}")),
    ("DELETE", "/books/{book_id}", 401, lambda c: c.delete(f"/books/{_book(c)['id']}", key=False)),
    ("DELETE", "/books/{book_id}", 404, lambda c: c.delete("/books/999999999")),
    ("DELETE", "/books/{book_id}", 422, lambda c: c.delete("/books/abc")),
]


class Client:
    def __init__(self, http, base_url, api_key, book_data, create_book):
        self.http, self.base_url, self.key = http, base_url, api_key
        self.book_data, self.create_book = book_data, create_book

    def _call(self, method, path, key=True, **kw):
        headers = {"X-API-Key": self.key} if key else {}
        return self.http.request(method, self.base_url + path, headers=headers, timeout=5, **kw)

    def get(self, path, **kw):
        return self._call("GET", path, **kw)

    def post(self, path, **kw):
        return self._call("POST", path, **kw)

    def patch(self, path, **kw):
        return self._call("PATCH", path, **kw)

    def delete(self, path, **kw):
        return self._call("DELETE", path, **kw)


@pytest.mark.parametrize("method, path, status, produce", SCENARIOS,
                         ids=[f"{m} {p} {s}" for m, p, s, _ in SCENARIOS])
def test_response_matches_the_documented_schema(live_doc, http, base_url, api_key, book_data, create_book,
                                                method, path, status, produce):
    response = produce(Client(http, base_url, api_key, book_data, create_book))
    assert response.status_code == status, response.text
    check_response(live_doc, method, path, response)


def test_every_documented_response_has_a_scenario(snapshot):
    scenarios = {(m, p, s) for m, p, s, _ in SCENARIOS}
    documented = _documented_pairs(snapshot)
    assert scenarios == documented, {"documented, no scenario": sorted(documented - scenarios),
                                     "scenario, not documented": sorted(scenarios - documented)}


def test_strict_check_catches_an_undeclared_field(live_doc, http, base_url):
    """The contract check itself: a body with an extra property must fail it."""
    response = http.get(f"{base_url}/health", timeout=5)

    class Tampered:
        status_code, headers, content = response.status_code, response.headers, response.content

        @staticmethod
        def json():
            return {**response.json(), "unexpected": True}

    with pytest.raises(AssertionError, match="unexpected"):
        check_response(live_doc, "GET", "/health", Tampered)
