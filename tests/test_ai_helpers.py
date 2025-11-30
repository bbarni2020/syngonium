from app.ai_helpers import local_validate


def test_local_validate_ok():
    source = "Some FAQ text"
    candidate = "Hi, This is an answer. Information above is taken from the FAQ. If this helped, please close the ticket."
    ok, why = local_validate(candidate, source)
    assert ok


def test_local_validate_missing_greeting():
    source = ""
    candidate = "This is an answer without greeting. If this helped, please close the ticket."
    ok, why = local_validate(candidate, source)
    assert not ok
