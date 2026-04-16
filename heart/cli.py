import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='heart',
        description='Convert question bank HTML/text files to Anki flashcards.',
    )
    parser.add_argument(
        '--platform',
        choices=['uworld', 'amboss', 'apgo', 'nbme'],
        required=True,
        help='Source platform',
    )
    parser.add_argument(
        '--input',
        type=Path,
        help=(
            'Input directory containing saved HTML files (UWorld/AMBOSS/APGO; '
            'default: ./html_dump) or path to a .txt file (NBME; required).'
        ),
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('./gen_anki'),
        help='Output directory for Anki flashcard files (default: ./gen_anki)',
    )
    parser.add_argument(
        '--anki-media',
        type=Path,
        default=Path.home() / 'Library/Application Support/Anki2/User 1/collection.media',
        help=(
            'Anki collection.media directory, UWorld only '
            '(default: ~/Library/Application Support/Anki2/User 1/collection.media)'
        ),
    )

    args = parser.parse_args(argv)

    # Build the argv list for the target parser script.
    script_argv = ['--output', str(args.output)]
    if args.input is not None:
        script_argv += ['--input', str(args.input)]

    if args.platform == 'uworld':
        script_argv += ['--anki-media', str(args.anki_media)]
        from src.app_uworld import main as _main
    elif args.platform == 'amboss':
        from src.app_amboss import main as _main
    elif args.platform == 'apgo':
        from src.app_apgo import main as _main
    elif args.platform == 'nbme':
        from src.app_NBME_form_textfile import main as _main

    _main(script_argv)


if __name__ == '__main__':
    main()
