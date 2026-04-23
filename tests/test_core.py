"""Tests for cast/core.py helpers (excluding LLM calls)."""
import logging
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from cast.core import (
    CardUsage,
    ClozeResult,
    EnrichmentResult,
    HeartAPIError,
    HeartError,
    HeartParseError,
    HeartUserError,
    ParsedQuestion,
    ValidationResult,
    _INPUT_COST_PER_1K_TOKENS,
    _OUTPUT_COST_PER_1K_TOKENS,
    _default_anki_media_path,
    format_for_anki,
    markdown_to_html,
    try_patterns,
    try_selectors,
)


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


@patch("cast.core.OpenAI")
def test_generate_enrichment_returns_enrichment_result(mock_openai_cls):
    from cast.core import generate_enrichment

    mock_parsed = EnrichmentResult(
        enrichment_markdown="Explanation here.",
        tags=["cardiology", "cardiovascular", "heart_failure", "beta_blocker", "renal", "uworld"],
        confidence=0.88,
    )
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed = mock_parsed
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.prompt_tokens_details.cached_tokens = 20
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.return_value = mock_response
    mock_openai_cls.return_value = mock_client

    result, usage = generate_enrichment("Q text", "A text", "system prompt")

    assert isinstance(result, EnrichmentResult)
    assert result.enrichment_markdown == "Explanation here."
    assert len(result.tags) == 6
    assert result.confidence == 0.88
    assert isinstance(usage, CardUsage)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.cached_tokens == 20
    mock_client.beta.chat.completions.parse.assert_called_once()


def test_card_usage_cost_usd():
    usage = CardUsage(input_tokens=1000, output_tokens=500, cached_tokens=200)
    expected = (1000 * _INPUT_COST_PER_1K_TOKENS + 500 * _OUTPUT_COST_PER_1K_TOKENS) / 1000
    assert abs(usage.cost_usd - expected) < 1e-10


def test_card_usage_cost_zero_tokens():
    usage = CardUsage(input_tokens=0, output_tokens=0, cached_tokens=0)
    assert usage.cost_usd == 0.0


@patch("cast.core.generate_enrichment")
def test_run_pipeline_logs_per_card_debug(mock_gen, tmp_path, caplog):
    from cast.core import run_pipeline

    mock_result = EnrichmentResult(
        enrichment_markdown="text",
        tags=["a", "b", "c", "d", "e", "f"],
        confidence=0.9,
    )
    mock_usage = CardUsage(input_tokens=100, output_tokens=50, cached_tokens=10)
    mock_gen.return_value = (mock_result, mock_usage)

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")
    output_dir = tmp_path / "output"

    def fake_parse(content, file_path):
        return [ParsedQuestion(question="Q?", correct_answer="A", answer_list="", explanation="E")]

    with caplog.at_level(logging.DEBUG, logger="cast.core"):
        run_pipeline(fake_parse, "system prompt", input_file, output_dir)

    assert any(
        "Card 1" in r.message and "100 in" in r.message and "50 out" in r.message
        for r in caplog.records
        if r.levelno == logging.DEBUG
    )


@patch("cast.core.generate_enrichment")
def test_run_pipeline_logs_run_total_info(mock_gen, tmp_path, caplog):
    from cast.core import run_pipeline

    mock_result = EnrichmentResult(
        enrichment_markdown="text",
        tags=["a", "b", "c", "d", "e", "f"],
        confidence=0.9,
    )
    mock_gen.return_value = (
        mock_result,
        CardUsage(input_tokens=100, output_tokens=50, cached_tokens=10),
    )

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")
    output_dir = tmp_path / "output"

    def fake_parse(content, file_path):
        return [
            ParsedQuestion(question="Q1?", correct_answer="A", answer_list="", explanation="E"),
            ParsedQuestion(question="Q2?", correct_answer="B", answer_list="", explanation="E"),
        ]

    with caplog.at_level(logging.INFO, logger="cast.core"):
        run_pipeline(fake_parse, "system prompt", input_file, output_dir)

    total_records = [r for r in caplog.records if "Run total" in r.message]
    assert len(total_records) == 1
    msg = total_records[0].message
    assert "200 in" in msg
    assert "100 out" in msg
    assert "20 cached" in msg


def test_try_selectors_primary_match():
    soup = BeautifulSoup('<div id="questionText">Q</div>', "html.parser")
    result = try_selectors(soup, [{"id": "questionText"}, {"id": "fallback"}], context="test")
    assert result is not None
    assert result.get_text() == "Q"


def test_try_selectors_fallback_match_logs_warning(caplog):
    soup = BeautifulSoup('<div id="fallback">Q</div>', "html.parser")
    with caplog.at_level(logging.WARNING, logger="cast.core"):
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
    with caplog.at_level(logging.WARNING, logger="cast.core"):
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
    with caplog.at_level(logging.WARNING, logger="cast.core"):
        result = try_selectors(soup, [{"id": "missing"}], find_all=True, context="test:answers")
    assert result == []


def test_try_patterns_primary_match():
    result = try_patterns("Answer Key:\n1. A", [r"Answer Key:\n([\s\S]+)"], context="test")
    assert result is not None


def test_try_patterns_fallback_match_logs_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="cast.core"):
        result = try_patterns(
            "Answers:\n1. A",
            [r"Answer Key:\n([\s\S]+)", r"Answers:\n([\s\S]+)"],
            context="test:answer_key",
        )
    assert result is not None
    assert "Fallback pattern matched" in caplog.text


def test_try_patterns_all_fail_logs_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="cast.core"):
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


# --- validate_enrichment tests ---

@patch("cast.core.OpenAI")
def test_validate_enrichment_returns_result_and_usage_not_flagged(mock_openai_cls):
    from cast.core import validate_enrichment

    mock_val = ValidationResult(flagged=False, justification="No contradictions found.")
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed = mock_val
    mock_response.usage.prompt_tokens = 80
    mock_response.usage.completion_tokens = 20
    mock_response.usage.prompt_tokens_details.cached_tokens = 0
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.return_value = mock_response
    mock_openai_cls.return_value = mock_client

    val_result, usage = validate_enrichment("Some enrichment text.")

    assert isinstance(val_result, ValidationResult)
    assert val_result.flagged is False
    assert val_result.justification == "No contradictions found."
    assert isinstance(usage, CardUsage)
    assert usage.input_tokens == 80
    assert usage.output_tokens == 20


@patch("cast.core.OpenAI")
def test_validate_enrichment_returns_flagged_true(mock_openai_cls):
    from cast.core import validate_enrichment

    mock_val = ValidationResult(
        flagged=True, justification="Beta-blockers are stated to increase heart rate."
    )
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed = mock_val
    mock_response.usage.prompt_tokens = 80
    mock_response.usage.completion_tokens = 30
    mock_response.usage.prompt_tokens_details.cached_tokens = 0
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.return_value = mock_response
    mock_openai_cls.return_value = mock_client

    val_result, _ = validate_enrichment("Incorrect explanation.")

    assert val_result.flagged is True
    assert "Beta-blockers" in val_result.justification


@patch("cast.core.validate_enrichment")
@patch("cast.core.generate_enrichment")
def test_run_pipeline_validate_off_skips_validation(mock_gen, mock_val, tmp_path):
    from cast.core import run_pipeline

    mock_result = EnrichmentResult(
        enrichment_markdown="text", tags=["a", "b", "c", "d", "e", "f"], confidence=0.9
    )
    mock_gen.return_value = (mock_result, CardUsage(100, 50, 0))

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")

    def fake_parse(content, file_path):
        return [ParsedQuestion(question="Q?", correct_answer="A", answer_list="", explanation="E")]

    run_pipeline(fake_parse, "prompt", input_file, tmp_path / "out", validate=False)

    mock_val.assert_not_called()


@patch("cast.core.validate_enrichment")
@patch("cast.core.generate_enrichment")
def test_run_pipeline_validate_on_calls_validation(mock_gen, mock_val, tmp_path):
    from cast.core import run_pipeline

    mock_result = EnrichmentResult(
        enrichment_markdown="text", tags=["a", "b", "c", "d", "e", "f"], confidence=0.9
    )
    mock_gen.return_value = (mock_result, CardUsage(100, 50, 0))
    mock_val.return_value = (ValidationResult(flagged=False, justification="OK"), CardUsage(80, 20, 0))

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")

    def fake_parse(content, file_path):
        return [ParsedQuestion(question="Q?", correct_answer="A", answer_list="", explanation="E")]

    run_pipeline(fake_parse, "prompt", input_file, tmp_path / "out", validate=True)

    mock_val.assert_called_once_with("text")


@patch("cast.core.validate_enrichment")
@patch("cast.core.generate_enrichment")
def test_run_pipeline_validate_flagged_appends_banner(mock_gen, mock_val, tmp_path):
    from cast.core import run_pipeline

    mock_result = EnrichmentResult(
        enrichment_markdown="text", tags=["a", "b", "c", "d", "e", "f"], confidence=0.9
    )
    mock_gen.return_value = (mock_result, CardUsage(100, 50, 0))
    mock_val.return_value = (
        ValidationResult(flagged=True, justification="Wrong mechanism stated."),
        CardUsage(80, 20, 0),
    )

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")
    output_dir = tmp_path / "out"

    def fake_parse(content, file_path):
        return [ParsedQuestion(question="Q?", correct_answer="A", answer_list="", explanation="E")]

    run_pipeline(fake_parse, "prompt", input_file, output_dir, validate=True)

    output_files = list(output_dir.glob("*.txt"))
    assert len(output_files) == 1
    content = output_files[0].read_text(encoding="utf-8")
    assert "Validation flag" in content
    assert "Wrong mechanism stated." in content


@patch("cast.core.validate_enrichment")
@patch("cast.core.generate_enrichment")
def test_run_pipeline_validate_flagged_logs_warning(mock_gen, mock_val, tmp_path, caplog):
    from cast.core import run_pipeline

    mock_result = EnrichmentResult(
        enrichment_markdown="text", tags=["a", "b", "c", "d", "e", "f"], confidence=0.9
    )
    mock_gen.return_value = (mock_result, CardUsage(100, 50, 0))
    mock_val.return_value = (
        ValidationResult(flagged=True, justification="Incorrect first-line treatment."),
        CardUsage(80, 20, 0),
    )

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")

    def fake_parse(content, file_path):
        return [ParsedQuestion(question="Q?", correct_answer="A", answer_list="", explanation="E")]

    with caplog.at_level(logging.WARNING, logger="cast.core"):
        run_pipeline(fake_parse, "prompt", input_file, tmp_path / "out", validate=True)

    warning_records = [r for r in caplog.records if "flagged by validator" in r.message]
    assert len(warning_records) == 1
    assert "Incorrect first-line treatment." in warning_records[0].message


# --- generate_cloze / format=cloze / format=choices-front tests ---

@patch("cast.core.OpenAI")
def test_generate_cloze_returns_result_and_usage(mock_openai_cls):
    from cast.core import generate_cloze

    mock_cloze = ClozeResult(cloze_stem="Patient presents with {{c1::hypertension}}.")
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed = mock_cloze
    mock_response.usage.prompt_tokens = 60
    mock_response.usage.completion_tokens = 15
    mock_response.usage.prompt_tokens_details.cached_tokens = 0
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.return_value = mock_response
    mock_openai_cls.return_value = mock_client

    cloze_result, usage = generate_cloze("Patient presents with hypertension.", "Hypertension")

    assert isinstance(cloze_result, ClozeResult)
    assert "{{c1::" in cloze_result.cloze_stem
    assert isinstance(usage, CardUsage)
    assert usage.input_tokens == 60
    assert usage.output_tokens == 15


@patch("cast.core.generate_cloze")
@patch("cast.core.generate_enrichment")
def test_run_pipeline_format_cloze_calls_generate_cloze(mock_gen, mock_cloze_gen, tmp_path):
    from cast.core import run_pipeline

    mock_result = EnrichmentResult(
        enrichment_markdown="text", tags=["a", "b", "c", "d", "e", "f"], confidence=0.9
    )
    mock_gen.return_value = (mock_result, CardUsage(100, 50, 0))
    mock_cloze_gen.return_value = (ClozeResult(cloze_stem="{{c1::Q}}?"), CardUsage(60, 15, 0))

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")

    def fake_parse(content, file_path):
        return [ParsedQuestion(question="Q?", correct_answer="A", answer_list="", explanation="E")]

    run_pipeline(fake_parse, "prompt", input_file, tmp_path / "out", format="cloze")

    mock_cloze_gen.assert_called_once_with("Q?", "A")


@patch("cast.core.generate_cloze")
@patch("cast.core.generate_enrichment")
def test_run_pipeline_format_cloze_output_uses_cloze_stem(mock_gen, mock_cloze_gen, tmp_path):
    from cast.core import run_pipeline

    mock_result = EnrichmentResult(
        enrichment_markdown="text", tags=["a", "b", "c", "d", "e", "f"], confidence=0.9
    )
    mock_gen.return_value = (mock_result, CardUsage(100, 50, 0))
    mock_cloze_gen.return_value = (
        ClozeResult(cloze_stem="Patient has {{c1::hypertension}}."),
        CardUsage(60, 15, 0),
    )

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")
    output_dir = tmp_path / "out"

    def fake_parse(content, file_path):
        return [ParsedQuestion(question="Q?", correct_answer="A", answer_list="", explanation="E")]

    run_pipeline(fake_parse, "prompt", input_file, output_dir, format="cloze")

    content = list(output_dir.glob("*.txt"))[0].read_text(encoding="utf-8")
    front = content.split("\t")[0]
    assert "{{c1::hypertension}}" in front


@patch("cast.core.generate_enrichment")
def test_run_pipeline_format_choices_front_puts_answer_list_on_front(mock_gen, tmp_path):
    from cast.core import run_pipeline

    mock_result = EnrichmentResult(
        enrichment_markdown="text", tags=["a", "b", "c", "d", "e", "f"], confidence=0.9
    )
    mock_gen.return_value = (mock_result, CardUsage(100, 50, 0))

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")
    output_dir = tmp_path / "out"

    def fake_parse(content, file_path):
        return [ParsedQuestion(question="Q?", correct_answer="A", answer_list="CHOICES", explanation="E")]

    run_pipeline(fake_parse, "prompt", input_file, output_dir, format="choices-front")

    content = list(output_dir.glob("*.txt"))[0].read_text(encoding="utf-8")
    front = content.split("\t")[0]
    assert "CHOICES" in front


@patch("cast.core.generate_enrichment")
def test_run_pipeline_format_choices_front_drops_answer_list_from_back(mock_gen, tmp_path):
    from cast.core import run_pipeline

    mock_result = EnrichmentResult(
        enrichment_markdown="text", tags=["a", "b", "c", "d", "e", "f"], confidence=0.9
    )
    mock_gen.return_value = (mock_result, CardUsage(100, 50, 0))

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")
    output_dir = tmp_path / "out"

    def fake_parse(content, file_path):
        return [ParsedQuestion(question="Q?", correct_answer="A", answer_list="CHOICES", explanation="E")]

    run_pipeline(fake_parse, "prompt", input_file, output_dir, format="choices-front")

    content = list(output_dir.glob("*.txt"))[0].read_text(encoding="utf-8")
    back = content.split("\t")[1]
    assert "CHOICES" not in back


# ── HeartError hierarchy ──────────────────────────────────────────────────────


def test_heart_error_is_base():
    err = HeartError("Something broke", "Try this fix")
    assert isinstance(err, Exception)
    assert err.user_message == "Something broke"
    assert err.advice == "Try this fix"
    assert str(err) == "Something broke"


def test_heart_user_error_is_heart_error():
    err = HeartUserError("Bad input", "Check your files")
    assert isinstance(err, HeartError)
    assert err.user_message == "Bad input"


def test_heart_api_error_is_heart_error():
    err = HeartAPIError("API unreachable", "Check your connection")
    assert isinstance(err, HeartError)


def test_heart_parse_error_is_heart_error():
    err = HeartParseError("Parsing failed", "Check the HTML format")
    assert isinstance(err, HeartError)


# ── run_pipeline pre-run validation ──────────────────────────────────────────


def test_run_pipeline_raises_on_missing_api_key(tmp_path):
    from cast.core import run_pipeline

    input_file = tmp_path / "input.html"
    input_file.write_text("<html></html>", encoding="utf-8")

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(HeartUserError, match="OPENAI_API_KEY"):
            run_pipeline(lambda c, f: [], "prompt", input_file, tmp_path / "out")


def test_run_pipeline_raises_on_missing_input_path(tmp_path):
    from cast.core import run_pipeline

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with pytest.raises(HeartUserError, match="not found"):
            run_pipeline(
                lambda c, f: [],
                "prompt",
                tmp_path / "nonexistent",
                tmp_path / "out",
            )


def test_run_pipeline_raises_on_empty_html_directory(tmp_path):
    from cast.core import run_pipeline

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with pytest.raises(HeartUserError, match="No HTML files"):
            run_pipeline(lambda c, f: [], "prompt", empty_dir, tmp_path / "out")


# ── _default_anki_media_path ──────────────────────────────────────────────────


def test_default_anki_media_path_macos():
    with patch("cast.core.sys") as mock_sys:
        mock_sys.platform = "darwin"
        path = _default_anki_media_path()
    assert "Library" in str(path)
    assert "Application Support" in str(path)
    assert "Anki2" in str(path)


def test_default_anki_media_path_windows():
    with patch("cast.core.sys") as mock_sys, \
         patch.dict("os.environ", {"APPDATA": "C:\\Users\\test\\AppData\\Roaming"}):
        mock_sys.platform = "win32"
        path = _default_anki_media_path()
    assert "Anki2" in str(path)
    assert "AppData" in str(path) or "Roaming" in str(path)


def test_default_anki_media_path_linux():
    with patch("cast.core.sys") as mock_sys:
        mock_sys.platform = "linux"
        path = _default_anki_media_path()
    assert ".local" in str(path)
    assert "share" in str(path)
    assert "Anki2" in str(path)


def test_default_anki_media_path_no_home():
    """Returns None when Path.home() raises RuntimeError (e.g. stripped CI env)."""
    with patch("cast.core.Path.home", side_effect=RuntimeError("Could not determine home directory.")), \
         patch.dict("os.environ", {}, clear=True):
        path = _default_anki_media_path()
    assert path is None
