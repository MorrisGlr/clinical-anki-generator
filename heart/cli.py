import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="heart",
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
    parser.add_argument(
        "--anki-media",
        type=Path,
        default=Path.home() / "Library/Application Support/Anki2/User 1/collection.media",
        help=(
            "Anki collection.media directory, UWorld only "
            "(default: ~/Library/Application Support/Anki2/User 1/collection.media)"
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

    args = parser.parse_args(argv)

    input_path = args.input or Path("./html_dump")

    from heart.core import run_pipeline
    from heart.parsers import get_parser

    parse_fn, system_prompt = get_parser(args.platform)
    run_pipeline(
        parse_fn=parse_fn,
        system_prompt=system_prompt,
        input_path=input_path,
        output_dir=args.output,
        anki_media_path=str(args.anki_media) if args.platform == "uworld" else None,
        tags=args.tags,
    )


if __name__ == "__main__":
    main()
