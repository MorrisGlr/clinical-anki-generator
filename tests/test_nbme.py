"""Tests for the NBME text-file parser (src/app_NBME_form_textfile.py).

All tests use a synthetic .txt fixture — no API calls are made.
"""
from pathlib import Path

from src.app_NBME_form_textfile import extract_questions_and_answers, format_for_anki

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "nbme_sample.txt"


def test_returns_nonempty_dict():
    result = extract_questions_and_answers(str(FIXTURE_PATH))
    assert isinstance(result, dict)
    assert len(result) > 0


def test_extracts_correct_number_of_questions():
    result = extract_questions_and_answers(str(FIXTURE_PATH))
    assert len(result) == 2


def test_question_keys_start_with_number():
    result = extract_questions_and_answers(str(FIXTURE_PATH))
    keys = list(result.keys())
    assert keys[0].startswith("1.")
    assert keys[1].startswith("2.")


def test_each_value_has_options_and_correct_answer():
    result = extract_questions_and_answers(str(FIXTURE_PATH))
    for question_key, content in result.items():
        assert len(content) == 2, f"Expected [options, answer] for {question_key!r}"
        options, correct_answer = content
        assert options, f"Options are empty for {question_key!r}"
        assert correct_answer, f"Correct answer is empty for {question_key!r}"


def test_correct_answer_format():
    result = extract_questions_and_answers(str(FIXTURE_PATH))
    for question_key, content in result.items():
        _, correct_answer = content
        assert correct_answer.startswith(
            "Correct answer:"
        ), f"Unexpected format for {question_key!r}: {correct_answer!r}"


def test_first_question_correct_answer_is_a():
    result = extract_questions_and_answers(str(FIXTURE_PATH))
    keys = list(result.keys())
    _, correct_answer = result[keys[0]]
    assert "A" in correct_answer


def test_second_question_correct_answer_is_c():
    result = extract_questions_and_answers(str(FIXTURE_PATH))
    keys = list(result.keys())
    _, correct_answer = result[keys[1]]
    assert "C" in correct_answer


def test_format_for_anki_tab_separated():
    result = format_for_anki("Front text", "Back text")
    parts = result.split("\t")
    assert len(parts) == 2
    assert parts[0] == "Front text"
    assert parts[1] == "Back text"


def test_format_for_anki_no_trailing_newline():
    result = format_for_anki("Front", "Back")
    assert not result.endswith("\n")
