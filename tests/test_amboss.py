"""Tests for the AMBOSS HTML parser (heart/parsers/amboss.py)."""
from pathlib import Path

from heart.core import format_for_anki
from heart.parsers.amboss import parse

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "amboss_sample.html"
HTML_CONTENT = FIXTURE_PATH.read_text(encoding="utf-8")


def _parse():
    results = parse(HTML_CONTENT, str(FIXTURE_PATH))
    assert len(results) == 1
    return results[0]


def test_returns_one_parsed_question():
    results = parse(HTML_CONTENT, str(FIXTURE_PATH))
    assert len(results) == 1


def test_question_is_nonempty():
    pq = _parse()
    assert pq.question


def test_question_leading_number_stripped():
    pq = _parse()
    assert not pq.question[0].isdigit(), f"Question starts with digit: {pq.question[:20]!r}"


def test_correct_answer_contains_expected_text():
    pq = _parse()
    assert "Systemic lupus erythematosus" in pq.correct_answer


def test_correct_answer_prefixed():
    pq = _parse()
    assert pq.correct_answer.startswith("Correct Answer:")


def test_correct_answer_has_html_linebreak():
    pq = _parse()
    assert "</br>" in pq.correct_answer


def test_explanation_is_nonempty():
    pq = _parse()
    assert pq.explanation


def test_explanation_prefixed_with_linebreak():
    pq = _parse()
    assert pq.explanation.startswith("</br>")


def test_answer_list_is_empty_string():
    pq = _parse()
    assert pq.answer_list == ""


def test_format_for_anki_tab_separated():
    result = format_for_anki("Front text", "Back text")
    parts = result.split("\t")
    assert len(parts) == 2
    assert parts[0] == "Front text"
    assert parts[1] == "Back text"


def test_format_for_anki_no_trailing_newline():
    result = format_for_anki("Front", "Back")
    assert not result.endswith("\n")
