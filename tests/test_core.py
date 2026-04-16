"""Tests for heart/core.py helpers (excluding LLM calls)."""
from heart.core import _extract_tags


def test_extract_tags_returns_tags_and_strips_footer():
    raw = "Some explanation text.\n\nMore content.\nTAGS: cardiology, heart, uworld"
    content, tags = _extract_tags(raw)
    assert "TAGS:" not in content
    assert tags == ["cardiology", "heart", "uworld"]


def test_extract_tags_normalizes_to_lowercase():
    raw = "Content.\nTAGS: Cardiology, Heart Failure"
    _, tags = _extract_tags(raw)
    assert tags == ["cardiology", "heart_failure"]


def test_extract_tags_replaces_spaces_with_underscores():
    raw = "Content.\nTAGS: organ system, infectious disease"
    _, tags = _extract_tags(raw)
    assert tags == ["organ_system", "infectious_disease"]


def test_extract_tags_case_insensitive_header():
    raw = "Content.\ntags: nephrology, kidney"
    _, tags = _extract_tags(raw)
    assert tags == ["nephrology", "kidney"]


def test_extract_tags_missing_returns_empty_list():
    raw = "Content with no tags line at the end."
    content, tags = _extract_tags(raw)
    assert tags == []
    assert content == raw


def test_extract_tags_preserves_content_above_footer():
    raw = "Line one.\nLine two.\nTAGS: cardiology, heart"
    content, _ = _extract_tags(raw)
    assert "Line one." in content
    assert "Line two." in content


def test_extract_tags_strips_whitespace_from_individual_tags():
    raw = "Content.\nTAGS:  cardiology ,  heart , uworld "
    _, tags = _extract_tags(raw)
    assert tags == ["cardiology", "heart", "uworld"]


def test_extract_tags_ignores_empty_segments():
    raw = "Content.\nTAGS: cardiology, , heart"
    _, tags = _extract_tags(raw)
    assert tags == ["cardiology", "heart"]
