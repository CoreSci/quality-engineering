"""Write the service's OpenAPI document to ``openapi/openapi.json`` (the contract snapshot).

Run from ``api-testing/`` after an intended API change, then review and commit the diff:

    python tools/export_openapi.py

The contract tests compare the live document with this file and fail on any difference.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "service"))

from app import app  # noqa: E402

OUT = ROOT / "openapi" / "openapi.json"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    OUT.write_bytes(text.encode("utf-8"))
    print(f"wrote {OUT.relative_to(ROOT)} ({len(text):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
