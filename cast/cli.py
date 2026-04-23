import argparse
import os
import sys
import traceback
import webbrowser
from pathlib import Path

# ANSI color codes (stdlib only; safe on macOS Terminal and iTerm2)
_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"


def _check_command() -> int:
    """Run environment checks and report pass/fail for each item."""
    all_ok = True

    def _ok(msg: str) -> None:
        print(f"  {_GREEN}✓{_RESET}  {msg}")

    def _fail(msg: str, advice: str = "") -> None:
        nonlocal all_ok
        all_ok = False
        print(f"  {_RED}✗{_RESET}  {msg}")
        if advice:
            print(f"       {advice}")

    # Python version
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 10:
        _ok(f"Python {major}.{minor}.{sys.version_info[2]}")
    else:
        _fail(
            f"Python {major}.{minor} — version 3.10 or later required",
            "Install from https://www.python.org/downloads/ and re-run ./setup.sh",
        )

    # API key
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        _ok("OPENAI_API_KEY is set")
    else:
        _fail(
            "OPENAI_API_KEY is not set",
            "Run ./setup.sh to add your key, or see SETUP.md → 'Get your OpenAI API key'",
        )

    # Input directory
    input_dir = Path("./html_dump")
    if input_dir.exists():
        _ok(f"Input directory {input_dir} exists")
    else:
        _fail(
            f"Input directory {input_dir} not found",
            f"Create it with: mkdir {input_dir}",
        )

    # Output directory
    output_dir = Path("./gen_anki")
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True)
            _ok(f"Output directory {output_dir} created")
        except OSError as exc:
            _fail(
                f"Output directory {output_dir} could not be created: {exc}",
                "Check that you have write permissions in this folder",
            )
    else:
        test_file = output_dir / ".castcheck"
        try:
            test_file.touch()
            test_file.unlink()
            _ok(f"Output directory {output_dir} exists and is writable")
        except OSError:
            _fail(
                f"Output directory {output_dir} exists but is not writable",
                "Check folder permissions",
            )

    return 0 if all_ok else 1


def _serve_command(argv: list[str]) -> None:
    """Launch the CAST local web UI."""
    parser = argparse.ArgumentParser(prog="cast serve", description="Launch the CAST web UI.")
    parser.add_argument(
        "--port",
        type=int,
        default=7070,
        help="Port to listen on (default: 7070)",
    )
    args = parser.parse_args(argv)

    from cast.server.app import create_app

    app = create_app()
    url = f"http://localhost:{args.port}"
    print(f"Starting CAST web UI at {url}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(url)
    app.run(port=args.port, debug=False, use_reloader=False)


def main(argv=None):
    # Dispatch subcommands before the main argparse so --platform is not required.
    argv = list(argv) if argv is not None else sys.argv[1:]
    if argv and argv[0] == "check":
        sys.exit(_check_command())
    if argv and argv[0] == "serve":
        _serve_command(argv[1:])

    parser = argparse.ArgumentParser(
        prog="cast",
        description="Convert question bank HTML/text files to Anki flashcards.",
    )
    parser.add_argument(
        "--platform",
        choices=["uworld", "amboss", "apgo", "nbme"],
        required=True,
        help="Source platform",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help=(
            "Input directory containing saved HTML files (UWorld/AMBOSS/APGO; "
            "default: ./html_dump) or path to a .txt file (NBME; required)."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./gen_anki"),
        help="Output directory for Anki flashcard files (default: ./gen_anki)",
    )
    from cast.core import _default_anki_media_path

    parser.add_argument(
        "--anki-media",
        type=Path,
        default=_default_anki_media_path(),
        help=(
            "Anki collection.media directory, UWorld only "
            "(default: platform-specific Anki2/User 1/collection.media)"
        ),
    )
    parser.add_argument(
        "--tags",
        action="store_true",
        default=False,
        help=(
            "Append LLM-extracted tags as a third tab-separated column in the output. "
            "Requires a matching Anki note type with a Tags field."
        ),
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=False,
        help=(
            "Run a second lightweight LLM pass to flag cards whose explanations may "
            "contain claims that contradict standard medical knowledge. Flagged cards "
            "receive a visible warning banner on the back side."
        ),
    )
    parser.add_argument(
        "--format",
        choices=["basic", "cloze", "choices-front"],
        default="basic",
        help=(
            "Output card format. 'basic': standard front/back (default). "
            "'cloze': LLM-generated cloze-deletion stem (requires Anki Cloze note type). "
            "'choices-front': answer choices on the front, correct answer + explanation on back."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress tracebacks; print only a short friendly error message on failure.",
    )

    args = parser.parse_args(argv)

    # API key guard — check before importing openai or calling the pipeline.
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "\nError: OPENAI_API_KEY is not set.\n"
            "\nTo fix this:\n"
            "  1. Follow the API key setup guide in SETUP.md\n"
            "  2. Re-run: ./setup.sh\n"
            "  3. Verify with: cast check\n",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = args.input or Path("./html_dump")

    from cast.core import HeartError, run_pipeline
    from cast.parsers import get_parser

    try:
        parse_fn, system_prompt = get_parser(args.platform)
        run_pipeline(
            parse_fn=parse_fn,
            system_prompt=system_prompt,
            input_path=input_path,
            output_dir=args.output,
            anki_media_path=str(args.anki_media) if args.platform == "uworld" else None,
            tags=args.tags,
            validate=args.validate,
            format=args.format,
        )
    except HeartError as exc:
        if not args.quiet:
            traceback.print_exc()
        print(f"\nError: {exc.user_message}", file=sys.stderr)
        if exc.advice:
            print(f"  → {exc.advice}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        if not args.quiet:
            traceback.print_exc()
        print(f"\nUnexpected error: {exc}", file=sys.stderr)
        print(
            "  → If this keeps happening, please open an issue at "
            "https://github.com/MorrisGlr/clinical-anki-generator/issues",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
