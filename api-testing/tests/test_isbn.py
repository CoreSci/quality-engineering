"""Unit tests for the ISBN-13 check digit used by the service and by the test data."""
import pytest

from isbn import is_valid_isbn13, isbn13_check_digit


@pytest.mark.parametrize("first12, digit", [
    ("979900000000", "4"),     # 9+21+9+27 = 66 -> (10 - 6) % 10
    ("000000000000", "0"),
    ("111111111111", "6"),     # 6*1 + 6*3 = 24 -> 6
])
def test_check_digit_by_hand(first12, digit):
    assert isbn13_check_digit(first12) == digit


def test_exactly_one_check_digit_is_valid():
    first12 = "979912345678"
    valid = [d for d in "0123456789" if is_valid_isbn13(first12 + d)]
    assert valid == [isbn13_check_digit(first12)]


@pytest.mark.parametrize("value", ["", "979900000000", "97990000000044", "979900000000X", "9799-0000-0004"])
def test_malformed_values_are_invalid(value):
    assert not is_valid_isbn13(value)


@pytest.mark.parametrize("value", ["12345678901", "1234567890123", "abcdefghijkl"])
def test_check_digit_needs_twelve_digits(value):
    with pytest.raises(ValueError):
        isbn13_check_digit(value)
