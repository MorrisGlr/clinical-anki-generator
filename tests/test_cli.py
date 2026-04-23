"""Tests for cast CLI: cast check subcommand and API key guard."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cast.cli import _check_command, _serve_command, main


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


# ── cast check: remaining branches ───────────────────────────────────────────


def test_check_python_version_too_old(tmp_path, capsys):
    """_check_command() reports failure when Python < 3.10."""
    html_dump = tmp_path / "html_dump"
    html_dump.mkdir()

    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
        patch("cast.cli.Path") as mock_path_cls,
        patch("cast.cli.sys") as mock_sys,
    ):
        mock_sys.version_info = (3, 9, 0)

        def path_side_effect(arg=""):
            if arg == "./html_dump":
                return html_dump
            if arg == "./gen_anki":
                gen = tmp_path / "gen_anki"
                gen.mkdir(exist_ok=True)
                return gen
            return Path(arg)

        mock_path_cls.side_effect = path_side_effect
        result = _check_command()

    assert result == 1
    captured = capsys.readouterr()
    assert "version 3.10 or later required" in captured.out


def test_check_output_dir_creation_fails(tmp_path, capsys):
    """_check_command() reports failure when output dir cannot be created."""
    html_dump = tmp_path / "html_dump"
    html_dump.mkdir()

    mock_gen_anki = MagicMock()
    mock_gen_anki.exists.return_value = False
    mock_gen_anki.mkdir.side_effect = OSError("Permission denied")

    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
        patch("cast.cli.Path") as mock_path_cls,
    ):
        def path_side_effect(arg=""):
            if arg == "./html_dump":
                return html_dump
            if arg == "./gen_anki":
                return mock_gen_anki
            return Path(arg)

        mock_path_cls.side_effect = path_side_effect
        result = _check_command()

    assert result == 1
    captured = capsys.readouterr()
    assert "could not be created" in captured.out


def test_check_output_dir_not_writable(tmp_path, capsys):
    """_check_command() reports failure when output dir exists but is not writable."""
    html_dump = tmp_path / "html_dump"
    html_dump.mkdir()

    mock_castcheck = MagicMock()
    mock_castcheck.touch.side_effect = OSError("Read-only filesystem")

    mock_gen_anki = MagicMock()
    mock_gen_anki.exists.return_value = True
    mock_gen_anki.__truediv__ = MagicMock(return_value=mock_castcheck)

    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
        patch("cast.cli.Path") as mock_path_cls,
    ):
        def path_side_effect(arg=""):
            if arg == "./html_dump":
                return html_dump
            if arg == "./gen_anki":
                return mock_gen_anki
            return Path(arg)

        mock_path_cls.side_effect = path_side_effect
        result = _check_command()

    assert result == 1
    captured = capsys.readouterr()
    assert "not writable" in captured.out


# ── cast serve ────────────────────────────────────────────────────────────────


def test_serve_command_default_port(capsys):
    """_serve_command() opens browser at localhost:7070 and starts Flask."""
    mock_app = MagicMock()
    with patch("cast.server.app.create_app", return_value=mock_app), \
         patch("cast.cli.webbrowser.open") as mock_browser:
        _serve_command([])

    mock_browser.assert_called_once_with("http://localhost:7070")
    mock_app.run.assert_called_once_with(port=7070, debug=False, use_reloader=False)
    captured = capsys.readouterr()
    assert "http://localhost:7070" in captured.out


def test_serve_subcommand_dispatched_from_main():
    """main(['serve', ...]) dispatches to _serve_command with remaining argv."""
    with patch("cast.cli._serve_command") as mock_serve:
        main(["serve", "--port", "9090"])
    mock_serve.assert_called_once_with(["--port", "9090"])


# ── generic Exception handler ─────────────────────────────────────────────────


def test_generic_exception_handler(capsys):
    """Non-HeartError exceptions print 'Unexpected error' and exit 1."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("cast.parsers.get_parser", return_value=(MagicMock(), "prompt")), \
         patch("cast.core.run_pipeline", side_effect=RuntimeError("unexpected boom")):
        with pytest.raises(SystemExit) as exc_info:
            main(["--platform", "uworld"])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Unexpected error" in captured.err
    assert "unexpected boom" in captured.err
    assert "Traceback" in captured.err


# ── get_parser factory ────────────────────────────────────────────────────────


def test_get_parser_uworld():
    from cast.parsers import get_parser
    parse_fn, prompt = get_parser("uworld")
    assert callable(parse_fn)
    assert isinstance(prompt, str)


def test_get_parser_amboss():
    from cast.parsers import get_parser
    parse_fn, prompt = get_parser("amboss")
    assert callable(parse_fn)
    assert isinstance(prompt, str)


def test_get_parser_apgo():
    from cast.parsers import get_parser
    parse_fn, prompt = get_parser("apgo")
    assert callable(parse_fn)
    assert isinstance(prompt, str)


def test_get_parser_nbme():
    from cast.parsers import get_parser
    parse_fn, prompt = get_parser("nbme")
    assert callable(parse_fn)
    assert isinstance(prompt, str)


def test_get_parser_unknown_platform():
    from cast.parsers import get_parser
    with pytest.raises(ValueError, match="Unknown platform"):
        get_parser("unknown")
