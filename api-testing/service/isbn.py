"""ISBN-13 check digit (standard library only)."""
from __future__ import annotations


def isbn13_check_digit(first12: str) -> str:
    """Check digit for 12 leading digits: weights 1, 3, 1, 3, ... ; (10 - sum mod 10) mod 10."""
    if len(first12) != 12 or not first12.isdigit():
        raise ValueError("need exactly 12 digits")
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(first12))
    return str((10 - total % 10) % 10)


def is_valid_isbn13(value: str) -> bool:
    return len(value) == 13 and value.isdigit() and isbn13_check_digit(value[:12]) == value[12]
