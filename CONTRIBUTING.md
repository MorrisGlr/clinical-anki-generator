# Contributing to HEART

Thank you for your interest in contributing. This document covers how to set up a development environment, run tests, follow code style, and submit a pull request.

---

## Development setup

```bash
git clone https://github.com/MorrisGlr/clinical-anki-generator.git
cd clinical-anki-generator
pip install -e ".[dev]"
```

This installs the `heart` CLI in editable mode along with `pytest` and `pytest-cov`.

You will need an OpenAI API key for any live runs:

```bash
cp .env.example .env  # then add your key
```

---

## Running tests

```bash
pytest                                        # run all tests
pytest --cov=heart --cov-report=term          # with coverage
```

All 84 tests should pass before you open a pull request. Live API calls are not tested -- mock the OpenAI client in any new tests that touch `generate_enrichment()`, `validate_enrichment()`, or `generate_cloze()`.

---

## Code style

- **Formatter:** `black` with default line length (88 characters)
- **Linter:** `ruff` with the default ruleset
- **Type hints:** required on all public functions
- **Docstrings:** Google style

```bash
black heart/
ruff check heart/
```

---

## Test fixtures policy

HEART parsers operate on saved HTML from UWorld, AMBOSS, APGO, and NBME -- all copyrighted platforms. **Test fixtures must be synthetic.** Do not commit real question content, screenshots, or output files containing real question-bank material. See `tests/fixtures/` for examples of synthetic HTML that mimics platform structure without reproducing actual questions.

---

## Submitting a pull request

1. Branch from `main` with a descriptive name (e.g., `fix/amboss-selector`, `feat/pdf-export`).
2. Keep pull requests focused on one concern. A fix and an unrelated refactor belong in separate PRs.
3. Update `CLAUDE.md` if you change the directory structure, add dependencies, or modify CLI flags.
4. Run `pytest` and `ruff check heart/` before pushing. CI will also run these checks.
5. In the PR description, explain **what** changed and **why**. Reference any related issues.

---

## Adding a new parser

Each parser lives in `heart/parsers/<platform>.py` and must expose:

- `parse(content: str, file_path: str) -> list[ParsedQuestion]`
- `SYSTEM_PROMPT: str`

Use `try_selectors()` and `try_patterns()` from `heart/core.py` for all CSS and regex lookups -- do not call `soup.find()` or `re.search()` directly. Add a synthetic HTML fixture to `tests/fixtures/` and corresponding tests to `tests/test_<platform>.py`.

---

## Questions

Open a [GitHub Discussion](https://github.com/MorrisGlr/clinical-anki-generator/discussions) or file an issue using the [bug report or feature request templates](https://github.com/MorrisGlr/clinical-anki-generator/issues/new/choose).
