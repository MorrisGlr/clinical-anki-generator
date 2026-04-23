"""Tests for cast CLI: cast check subcommand and API key guard."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from cast.cli import _check_command, main


# ── cast check ───────────────────────────────────────────────────────────────


def test_check_all_pass(tmp_path, capsys):
    html_dump = tmp_path / "html_dump"
    html_dump.mkdir()
    gen_anki = tmp_path / "gen_anki"
    gen_anki.mkdir()

    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
        patch("cast.cli.Path") as mock_path_cls,
    ):
        # Map Path("./html_dump") and Path("./gen_anki") to tmp_path subdirs
        def path_side_effect(arg=""):
            if arg == "./html_dump":
                return html_dump
            if arg == "./gen_anki":
                return gen_anki
            return Path(arg)

        mock_path_cls.side_effect = path_side_effect

        result = _check_command()

    assert result == 0
    captured = capsys.readouterr()
    assert "✓" in captured.out
    assert "✗" not in captured.out


def test_check_missing_api_key(tmp_path, capsys):
    html_dump = tmp_path / "html_dump"
    html_dump.mkdir()

    with (
        patch.dict("os.environ", {}, clear=True),
        patch("cast.cli.Path") as mock_path_cls,
    ):
        def path_side_effect(arg=""):
            if arg == "./html_dump":
                return html_dump
            if arg == "./gen_anki":
                return tmp_path / "gen_anki"
            return Path(arg)

        mock_path_cls.side_effect = path_side_effect

        result = _check_command()

    assert result == 1
    captured = capsys.readouterr()
    assert "OPENAI_API_KEY" in captured.out
    assert "✗" in captured.out


def test_check_missing_input_dir(tmp_path, capsys):
    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
        patch("cast.cli.Path") as mock_path_cls,
    ):
        def path_side_effect(arg=""):
            if arg == "./html_dump":
                return tmp_path / "html_dump"  # does not exist
            if arg == "./gen_anki":
                gen = tmp_path / "gen_anki"
                gen.mkdir()
                return gen
            return Path(arg)

        mock_path_cls.side_effect = path_side_effect

        result = _check_command()

    assert result == 1
    captured = capsys.readouterr()
    assert "html_dump" in captured.out
    assert "✗" in captured.out


def test_check_creates_missing_output_dir(tmp_path, capsys):
    html_dump = tmp_path / "html_dump"
    html_dump.mkdir()
    gen_anki = tmp_path / "gen_anki"  # does not exist yet

    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
        patch("cast.cli.Path") as mock_path_cls,
    ):
        def path_side_effect(arg=""):
            if arg == "./html_dump":
                return html_dump
            if arg == "./gen_anki":
                return gen_anki
            return Path(arg)

        mock_path_cls.side_effect = path_side_effect

        result = _check_command()

    assert result == 0
    assert gen_anki.exists()
    captured = capsys.readouterr()
    assert "created" in captured.out


# ── API key guard in main() ───────────────────────────────────────────────────


def test_api_key_guard_exits_cleanly(capsys):
    """main() exits with code 1 and prints a friendly message when key is missing."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            main(["--platform", "uworld"])
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "OPENAI_API_KEY" in captured.err
    assert "SETUP.md" in captured.err
    # No traceback text in stderr
    assert "Traceback" not in captured.err


# ── --quiet flag ─────────────────────────────────────────────────────────────


def test_quiet_suppresses_traceback_on_heart_error(capsys, tmp_path):
    """--quiet prints the friendly message but not a traceback."""
    from cast.core import HeartUserError

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("cast.parsers.get_parser", return_value=(lambda c, f: [], "prompt")), \
         patch("cast.core.run_pipeline", side_effect=HeartUserError("Bad input", "Fix it")):
        with pytest.raises(SystemExit) as exc_info:
            main(["--platform", "uworld", "--quiet"])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Bad input" in captured.err
    assert "Fix it" in captured.err
    assert "Traceback" not in captured.err


def test_no_quiet_shows_traceback_on_heart_error(capsys, tmp_path):
    """Without --quiet, a traceback is printed before the friendly message."""
    from cast.core import HeartUserError

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("cast.parsers.get_parser", return_value=(lambda c, f: [], "prompt")), \
         patch("cast.core.run_pipeline", side_effect=HeartUserError("Bad input", "Fix it")):
        with pytest.raises(SystemExit) as exc_info:
            main(["--platform", "uworld"])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Bad input" in captured.err
    assert "Traceback" in captured.err


def test_check_subcommand_dispatched(capsys, tmp_path):
    """cast check exits with 0/1, not argparse error about --platform."""
    html_dump = tmp_path / "html_dump"
    html_dump.mkdir()

    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
        patch("cast.cli.Path") as mock_path_cls,
    ):
        def path_side_effect(arg=""):
            if arg == "./html_dump":
                return html_dump
            if arg == "./gen_anki":
                gen = tmp_path / "gen_anki"
                gen.mkdir(exist_ok=True)
                return gen
            return Path(arg)

        mock_path_cls.side_effect = path_side_effect

        with pytest.raises(SystemExit) as exc_info:
            main(["check"])

    # Should exit with 0 (all pass) not 2 (argparse error)
    assert exc_info.value.code == 0
