"""Shared fixtures: the local site, a network guard, and fixed browser settings.

* The demo page in ``site/`` is served for the test session by a small server in
  this process, bound to 127.0.0.1 on a free port.
* Every browser request goes through a guard: anything not addressed to 127.0.0.1
  or localhost is aborted and recorded, and the test fails. The tests never reach
  a third-party site.
* Locale, time zone, viewport and colour scheme are fixed, so results don't depend
  on the machine.
"""
from __future__ import annotations

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
LOCAL_HOSTS = {"127.0.0.1", "localhost"}


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):          # keep test output clean
        pass


@pytest.fixture(scope="session")
def site_url():
    """Base URL of the demo page, served on 127.0.0.1 for this session."""
    handler = functools.partial(_QuietHandler, directory=str(SITE))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    assert urlparse(url).hostname in LOCAL_HOSTS
    yield url
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """pytest-playwright hook: the same settings on every machine."""
    return {
        **browser_context_args,
        "locale": "en-US",
        "timezone_id": "UTC",
        "viewport": {"width": 1280, "height": 800},
        "color_scheme": "light",
        "reduced_motion": "reduce",
    }


@pytest.fixture
def blocked_requests(context):
    """Abort every request that isn't for 127.0.0.1/localhost; the list must stay empty."""
    blocked = []

    def guard(route):
        url = route.request.url
        if urlparse(url).hostname in LOCAL_HOSTS:
            route.continue_()
        else:
            blocked.append(url)
            route.abort()

    context.route("**/*", guard)
    yield blocked
    assert not blocked, f"requests to non-local hosts were blocked: {blocked}"


@pytest.fixture
def app(page, site_url, blocked_requests):
    """The demo page, freshly loaded with an empty list."""
    if urlparse(site_url).hostname not in LOCAL_HOSTS:
        pytest.exit(f"refusing to test a non-local address: {site_url}", returncode=2)
    page.goto(site_url)
    page.evaluate("localStorage.clear()")
    page.reload()
    return page
