"""Tests for heart/core.py helpers (excluding LLM calls)."""
import logging
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from heart.core import EnrichmentResult, format_for_anki, markdown_to_html, try_patterns, try_selectors


def test_enrichment_result_fields():
    result = EnrichmentResult(
        enrichment_markdown="## Header\nSome explanation.",
        tags=["cardiology", "cardiovascular", "heart_failure", "diuretics", "renal", "uworld"],
        confidence=0.95,
    )
    assert result.enrichment_markdown == "## Header\nSome explanation."
    assert len(result.tags) == 6
    assert result.confidence == 0.95


def test_enrichment_result_tags_are_list():
    result = EnrichmentResult(
        enrichment_markdown="Text",
        tags=["a", "b", "c", "d", "e", "f"],
        confidence=0.8,
    )
    assert isinstance(result.tags, list)
    assert all(isinstance(t, str) for t in result.tags)


def test_enrichment_result_confidence_bounds():
    low = EnrichmentResult(enrichment_markdown="", tags=["a"] * 6, confidence=0.0)
    high = EnrichmentResult(enrichment_markdown="", tags=["a"] * 6, confidence=1.0)
    assert low.confidence == 0.0
    assert high.confidence == 1.0


def test_enrichment_result_markdown_rendered_to_html():
    result = EnrichmentResult(
        enrichment_markdown="**bold** text",
        tags=["cardiology"] * 6,
        confidence=0.9,
    )
    html = markdown_to_html(result.enrichment_markdown)
    assert "<strong>bold</strong>" in html


@patch("heart.core.OpenAI")
def test_generate_enrichment_returns_enrichment_result(mock_openai_cls):
    from heart.core import generate_enrichment

    mock_parsed = EnrichmentResult(
        enrichment_markdown="Explanation here.",
        tags=["cardiology", "cardiovascular", "heart_failure", "beta_blocker", "renal", "uworld"],
        confidence=0.88,
    )
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed = mock_parsed
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.return_value = mock_response
    mock_openai_cls.return_value = mock_client

    result = generate_enrichment("Q text", "A text", "system prompt")

    assert isinstance(result, EnrichmentResult)
    assert result.enrichment_markdown == "Explanation here."
    assert len(result.tags) == 6
    assert result.confidence == 0.88
    mock_client.beta.chat.completions.parse.assert_called_once()


def test_try_selectors_primary_match():
    soup = BeautifulSoup('<div id="questionText">Q</div>', "html.parser")
    result = try_selectors(soup, [{"id": "questionText"}, {"id": "fallback"}], context="test")
    assert result is not None
    assert result.get_text() == "Q"


def test_try_selectors_fallback_match_logs_warning(caplog):
    soup = BeautifulSoup('<div id="fallback">Q</div>', "html.parser")
    with caplog.at_level(logging.WARNING, logger="heart.core"):
        result = try_selectors(
            soup,
            [{"id": "primary"}, {"id": "fallback"}],
            context="test:question",
        )
    assert result is not None
    assert "Fallback selector matched" in caplog.text
    assert "test:question" in caplog.text


def test_try_selectors_all_fail_logs_warning(caplog):
    soup = BeautifulSoup("<div>nothing</div>", "html.parser")
    with caplog.at_level(logging.WARNING, logger="heart.core"):
        result = try_selectors(soup, [{"id": "missing"}], context="test:field")
    assert result is None
    assert "All selectors failed" in caplog.text


def test_try_selectors_find_all_returns_list():
    soup = BeautifulSoup(
        '<div id="answerContainer">A</div><div id="answerContainer">B</div>', "html.parser"
    )
    result = try_selectors(
        soup, [{"id": "answerContainer"}], find_all=True, context="test:answers"
    )
    assert isinstance(result, list)
    assert len(result) == 2


def test_try_selectors_find_all_all_fail_returns_empty_list(caplog):
    soup = BeautifulSoup("<div>nothing</div>", "html.parser")
    with caplog.at_level(logging.WARNING, logger="heart.core"):
        result = try_selectors(soup, [{"id": "missing"}], find_all=True, context="test:answers")
    assert result == []


def test_try_patterns_primary_match():
    result = try_patterns("Answer Key:\n1. A", [r"Answer Key:\n([\s\S]+)"], context="test")
    assert result is not None


def test_try_patterns_fallback_match_logs_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="heart.core"):
        result = try_patterns(
            "Answers:\n1. A",
            [r"Answer Key:\n([\s\S]+)", r"Answers:\n([\s\S]+)"],
            context="test:answer_key",
        )
    assert result is not None
    assert "Fallback pattern matched" in caplog.text


def test_try_patterns_all_fail_logs_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="heart.core"):
        result = try_patterns("no match here", [r"Answer Key:\n([\s\S]+)"], context="test:key")
    assert result is None
    assert "All patterns failed" in caplog.text


def test_try_patterns_find_all_returns_list():
    import re
    content = "1. Q1\na. opt\nAnswer Key:\n1. A"
    result = try_patterns(
        content,
        [r"(\d+)\.\s(.*?)\n([a-f]\..*?)(?=\n\d+\.\s|\nAnswer Key:)"],
        flags=re.DOTALL,
        find_all=True,
        context="test:questions",
    )
    assert isinstance(result, list)
    assert len(result) == 1


def test_format_for_anki_with_enrichment_result_tags():
    result = EnrichmentResult(
        enrichment_markdown="",
        tags=["cardiology", "cardiovascular", "heart_failure", "diuretics", "renal", "uworld"],
        confidence=0.9,
    )
    anki_line = format_for_anki("Front", "Back", tags=result.tags)
    parts = anki_line.split("\t")
    assert len(parts) == 3
    assert "cardiology" in parts[2]
    assert "cardiovascular" in parts[2]
