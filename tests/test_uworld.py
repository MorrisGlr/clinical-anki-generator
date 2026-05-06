"""Tests for the UWorld HTML parser (cast/parsers/uworld.py)."""
import logging
from pathlib import Path

from cast.core import format_for_anki
from cast.parsers.uworld import parse

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "uworld_sample.html"
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
    assert "Acute pericarditis" in pq.correct_answer


def test_correct_answer_has_html_linebreak():
    pq = _parse()
    assert "</br>" in pq.correct_answer


def test_answer_list_has_multiple_choices():
    pq = _parse()
    assert "A." in pq.answer_list
    assert "B." in pq.answer_list


def test_answer_list_prefixed_with_linebreak():
    pq = _parse()
    assert pq.answer_list.startswith("</br>")


def test_explanation_is_nonempty():
    pq = _parse()
    assert pq.explanation


def test_image_paths_is_list():
    pq = _parse()
    assert isinstance(pq.image_paths, list)


def test_format_for_anki_tab_separated():
    result = format_for_anki("Front text", "Back text")
    parts = result.split("\t")
    assert len(parts) == 2
    assert parts[0] == "Front text"
    assert parts[1] == "Back text"


def test_format_for_anki_no_trailing_newline():
    result = format_for_anki("Front", "Back")
    assert not result.endswith("\n")


def test_format_for_anki_with_tags_adds_third_column():
    result = format_for_anki("Front", "Back", tags=["cardiology", "heart"])
    parts = result.split("\t")
    assert len(parts) == 3
    assert parts[2] == "cardiology heart"


def test_format_for_anki_empty_tags_omits_third_column():
    result = format_for_anki("Front", "Back", tags=[])
    assert len(result.split("\t")) == 2


def test_format_for_anki_none_tags_omits_third_column():
    result = format_for_anki("Front", "Back", tags=None)
    assert len(result.split("\t")) == 2


FALLBACK_FIXTURE = Path(__file__).parent / "fixtures" / "uworld_sample_fallback.html"
FALLBACK_HTML = FALLBACK_FIXTURE.read_text(encoding="utf-8")


def test_fallback_fixture_correct_answer_extracted(caplog):
    with caplog.at_level(logging.WARNING, logger="cast.core"):
        results = parse(FALLBACK_HTML, str(FALLBACK_FIXTURE))
    assert len(results) == 1
    pq = results[0]
    assert "Subarachnoid hemorrhage" in pq.correct_answer
    assert "Fallback selector matched" in caplog.text
    assert "uworld:correct_answer" in caplog.text


def test_parse_single_word_question_no_leading_number(capsys):
    """IndexError branch: question text has no space so split(" ", 1) fails."""
    html = '<div id="questionText">SingleWord</div>'
    results = parse(html, "test.html")
    assert len(results) == 1
    # The warning is printed (not logged); capsys captures it
    captured = capsys.readouterr()
    assert "Warning" in captured.out
    assert results[0].question == "SingleWord"


def test_parse_collects_images_from_files_dir(tmp_path):
    """image_paths is populated when a *_files/ companion dir contains images."""
    html_file = tmp_path / "question.html"
    files_dir = tmp_path / "question_files"
    files_dir.mkdir()
    (files_dir / "diagram.png").write_bytes(b"\x89PNG")
    (files_dir / "notes.txt").write_text("ignore me", encoding="utf-8")

    html_file.write_text(
        '<div class="question-zn9y2">1 What is shown?</div>', encoding="utf-8"
    )
    results = parse(html_file.read_text(encoding="utf-8"), str(html_file))

    assert len(results) == 1
    assert any("diagram.png" in p for p in results[0].image_paths)
