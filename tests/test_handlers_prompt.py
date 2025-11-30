from app.handlers import ANSWER_SYSTEM_PROMPT, CHECK_SYSTEM_PROMPT


def test_answer_prompt_includes_greeting_and_disclaimer_and_close():
    assert "greeting" in ANSWER_SYSTEM_PROMPT.lower()
    assert (
        "taken from the faq" in ANSWER_SYSTEM_PROMPT.lower()
        or "information above is taken from the faq" in ANSWER_SYSTEM_PROMPT.lower()
    )
    assert "please close the ticket" in ANSWER_SYSTEM_PROMPT.lower()


def test_answer_prompt_suggests_playful_but_factual():
    assert (
        "playful" in ANSWER_SYSTEM_PROMPT.lower()
        or "cheers" in ANSWER_SYSTEM_PROMPT.lower()
    )
    assert (
        "factual" in ANSWER_SYSTEM_PROMPT.lower()
        or "accurate" in ANSWER_SYSTEM_PROMPT.lower()
    )


def test_answer_prompt_forbids_follow_up_phrases():
    assert "do not" in ANSWER_SYSTEM_PROMPT.lower() or "do NOT" in ANSWER_SYSTEM_PROMPT
    assert "let me know" in ANSWER_SYSTEM_PROMPT.lower()


def test_check_prompt_requires_yes_no_and_justification():
    assert (
        "yes' or 'no'" in CHECK_SYSTEM_PROMPT.lower()
        or "reply only 'yes' or 'no'" in CHECK_SYSTEM_PROMPT.lower()
    )
    assert "justification" in CHECK_SYSTEM_PROMPT.lower()
