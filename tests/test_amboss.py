"""Tests for the AMBOSS HTML parser (src/app_amboss.py).

All tests use a synthetic HTML fixture — no API calls are made.
"""
from pathlib import Path

from src.app_amboss import extract_text_from_html, format_for_anki

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "amboss_sample.html"
HTML_CONTENT = FIXTURE_PATH.read_text(encoding="utf-8")

QUESTION_ID = "FLaJnh0OIM_1"
CORRECT_ANSWER_DIV_CLASS = "container--CKAXW correctAnswer--xNrke"
EXPLANATION_DIV_CLASS = "-f8b48b6542a07-explanationContainer"


def _parse():
    return extract_text_from_html(
        HTML_CONTENT, QUESTION_ID, CORRECT_ANSWER_DIV_CLASS, EXPLANATION_DIV_CLASS
    )


def test_question_is_nonempty():
    question, *_ = _parse()
    assert question


def test_question_leading_number_stripped():
    question, *_ = _parse()
    assert not question[0].isdigit(), f"Question starts with digit: {question[:20]!r}"


def test_correct_answer_contains_expected_text():
    _, _, correct_answer_str, _ = _parse()
    assert "Systemic lupus erythematosus" in correct_answer_str


def test_correct_answer_prefixed():
    _, _, correct_answer_str, _ = _parse()
    assert correct_answer_str.startswith("Correct Answer:")


def test_correct_answer_has_html_linebreak():
    _, _, correct_answer_str, _ = _parse()
    assert "</br>" in correct_answer_str


def test_explanation_is_nonempty():
    _, _, _, explanation_str = _parse()
    assert explanation_str


def test_explanation_prefixed_with_linebreak():
    _, _, _, explanation_str = _parse()
    assert explanation_str.startswith("</br>")


def test_back_side_is_concatenation_of_components():
    _, back_side, correct_answer_str, explanation_str = _parse()
    assert back_side == correct_answer_str + explanation_str


def test_format_for_anki_tab_separated():
    result = format_for_anki("Front text", "Back text")
    parts = result.split("\t")
    assert len(parts) == 2
    assert parts[0] == "Front text"
    assert parts[1] == "Back text"


def test_format_for_anki_no_trailing_newline():
    result = format_for_anki("Front", "Back")
    assert not result.endswith("\n")
