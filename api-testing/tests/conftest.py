"""Shared fixtures: where the service runs, the API key, and synthetic test data.

Two ways to run:

* **Default:** the session starts the service itself (``uvicorn`` on 127.0.0.1, a
  free port), with an API key generated for this run, and stops it at the end.
* **Against a running service:** set ``BOOKSHELF_BASE_URL`` (e.g.
  ``http://127.0.0.1:8000``) and ``BOOKSHELF_API_KEY`` (the same key the service
  was started with). This is how CI and the Docker smoke test run.

Either way, tests only ever talk to 127.0.0.1 or localhost.
"""
from __future__ import annotations

import itertools
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import pytest
import requests

HERE = Path(__file__).resolve().parent
SERVICE = HERE.parent / "service"
sys.path.insert(0, str(SERVICE))

from isbn import isbn13_check_digit  # noqa: E402

LOCAL_HOSTS = {"127.0.0.1", "localhost"}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_healthy(base_url: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            if requests.get(f"{base_url}/health", timeout=1).status_code == 200:
                return
        except requests.ConnectionError:
            pass
        if time.monotonic() > deadline:
            raise RuntimeError(f"service at {base_url} did not become healthy within {timeout:.0f} s")
        time.sleep(0.2)


@pytest.fixture(scope="session")
def service():
    """(base_url, api_key) of a running service on the local machine."""
    base_url = os.environ.get("BOOKSHELF_BASE_URL")
    if base_url:
        key = os.environ.get("BOOKSHELF_API_KEY")
        if not key:
            pytest.exit("BOOKSHELF_BASE_URL is set but BOOKSHELF_API_KEY is not", returncode=2)
        if urlparse(base_url).hostname not in LOCAL_HOSTS:
            pytest.exit(f"refusing to test a non-local address: {base_url}", returncode=2)
        base_url = base_url.rstrip("/")
        _wait_healthy(base_url)
        yield base_url, key
        return
    key = secrets.token_hex(16)
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(SERVICE), env={**os.environ, "BOOKSHELF_API_KEY": key},
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_healthy(base_url)
        yield base_url, key
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def base_url(service) -> str:
    return service[0]


@pytest.fixture(scope="session")
def api_key(service) -> str:
    return service[1]


@pytest.fixture
def http():
    """A requests session that ignores proxy settings from the environment."""
    with requests.Session() as s:
        s.trust_env = False
        yield s


@pytest.fixture
def auth(api_key) -> dict:
    return {"X-API-Key": api_key}


# ------------------------------------------------------------------ synthetic data
# Each run gets its own block of ISBNs and author names, so tests don't depend on
# each other or on earlier runs against the same service. Outcomes don't depend on
# the block chosen. All ISBNs use the 979-9 prefix and carry a valid check digit.
_RUN = secrets.randbelow(10 ** 5)
_counter = itertools.count(1)


def new_isbn() -> str:
    n = next(_counter)
    assert n < 1000, "synthetic ISBN block exhausted for this run"
    first12 = f"9799{_RUN:05d}{n:03d}"
    return first12 + isbn13_check_digit(first12)


def new_author() -> str:
    return f"Test Author {_RUN:05d}-{next(_counter):03d}"


@pytest.fixture
def book_data():
    """Factory for a valid, unique create payload; keyword arguments override fields."""
    def make(**overrides):
        data = {"title": "An Invented Title", "author": new_author(), "year": 2001,
                "isbn": new_isbn(), "tags": ["fiction"]}
        data.update(overrides)
        return data
    return make


@pytest.fixture
def create_book(http, base_url, auth, book_data):
    """Create a book through the API and return its JSON."""
    def create(**overrides):
        r = http.post(f"{base_url}/books", json=book_data(**overrides), headers=auth, timeout=5)
        assert r.status_code == 201, r.text
        return r.json()
    return create
