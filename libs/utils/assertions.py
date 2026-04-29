"""
Custom assertion helpers to keep tests clean and readable.
"""


def assert_equal(actual, expected, message: str = ""):
    msg = message or f"Expected '{expected}', got '{actual}'"
    assert actual == expected, msg


def assert_true(condition, message: str = ""):
    msg = message or "Expected condition to be True"
    assert condition, msg


def assert_false(condition, message: str = ""):
    msg = message or "Expected condition to be False"
    assert not condition, msg

