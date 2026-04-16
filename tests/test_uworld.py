"""Tests for the UWorld HTML parser (src/app_uworld.py).

All tests use a synthetic HTML fixture — no API calls are made.
"""
from pathlib import Path

from src.app_uworld import extract_text_from_html, format_for_anki

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "uworld_sample.html"
HTML_CONTENT = FIXTURE_PATH.read_text(encoding="utf-8")

QUESTION_DIV_ID = "questionText"
CORRECT_ANSWER_DIV_CLASS = (
    "omitted-answer content d-flex align-items-start flex-column ng-star-inserted"
)
ANSWER_LIST_DIV_ID = "answerContainer"
EXPLANATION_DIV_ID = "explanation-container"


def _parse():
    return extract_text_from_html(
        HTML_CONTENT,
        QUESTION_DIV_ID,
        CORRECT_ANSWER_DIV_CLASS,
        ANSWER_LIST_DIV_ID,
        EXPLANATION_DIV_ID,
        str(FIXTURE_PATH),
        anki_media_path=None,
    )


def test_question_is_nonempty():
    question, *_ = _parse()
    assert question


def test_question_leading_number_stripped():
    question, *_ = _parse()
    assert not question[0].isdigit(), f"Question starts with digit: {question[:20]!r}"


def test_correct_answer_contains_expected_text():
    _, _, correct_answer_str, _, _ = _parse()
    assert "Acute pericarditis" in correct_answer_str


def test_correct_answer_has_html_linebreak():
    _, _, correct_answer_str, _, _ = _parse()
    assert "</br>" in correct_answer_str


def test_answer_list_has_multiple_choices():
    _, _, _, answer_list_str, _ = _parse()
    assert "A." in answer_list_str
    assert "B." in answer_list_str


def test_answer_list_prefixed_with_linebreak():
    _, _, _, answer_list_str, _ = _parse()
    assert answer_list_str.startswith("</br>")


def test_explanation_is_nonempty():
    _, _, _, _, explanation_str = _parse()
    assert explanation_str


def test_back_side_is_concatenation_of_components():
    _, back_side, correct_answer_str, answer_list_str, explanation_str = _parse()
    assert back_side == correct_answer_str + answer_list_str + explanation_str


def test_format_for_anki_tab_separated():
    result = format_for_anki("Front text", "Back text")
    parts = result.split("\t")
    assert len(parts) == 2
    assert parts[0] == "Front text"
    assert parts[1] == "Back text"


def test_format_for_anki_no_trailing_newline():
    result = format_for_anki("Front", "Back")
    assert not result.endswith("\n")
