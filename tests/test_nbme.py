"""Tests for the NBME text-file parser (heart/parsers/nbme.py)."""
from pathlib import Path

from heart.core import format_for_anki
from heart.parsers.nbme import parse

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "nbme_sample.txt"
TEXT_CONTENT = FIXTURE_PATH.read_text(encoding="utf-8")


def test_returns_nonempty_list():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    assert isinstance(results, list)
    assert len(results) > 0


def test_extracts_correct_number_of_questions():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    assert len(results) == 2


def test_question_is_nonempty():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    for pq in results:
        assert pq.question, f"Question is empty: {pq!r}"


def test_question_leading_number_stripped():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    for pq in results:
        assert not pq.question[0].isdigit(), (
            f"Question starts with digit: {pq.question[:20]!r}"
        )


def test_correct_answer_format():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    for pq in results:
        assert pq.correct_answer.startswith("Correct answer:"), (
            f"Unexpected format: {pq.correct_answer!r}"
        )


def test_correct_answer_has_html_linebreak():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    for pq in results:
        assert "</br>" in pq.correct_answer


def test_first_question_correct_answer_is_a():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    assert "A" in results[0].correct_answer


def test_second_question_correct_answer_is_c():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    assert "C" in results[1].correct_answer


def test_answer_list_is_nonempty():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    for pq in results:
        assert pq.answer_list, f"Answer list is empty: {pq!r}"


def test_explanation_is_empty_string():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    for pq in results:
        assert pq.explanation == ""


def test_image_paths_is_empty_list():
    results = parse(TEXT_CONTENT, str(FIXTURE_PATH))
    for pq in results:
        assert pq.image_paths == []


def test_format_for_anki_tab_separated():
    result = format_for_anki("Front text", "Back text")
    parts = result.split("\t")
    assert len(parts) == 2
    assert parts[0] == "Front text"
    assert parts[1] == "Back text"


def test_format_for_anki_no_trailing_newline():
    result = format_for_anki("Front", "Back")
    assert not result.endswith("\n")
