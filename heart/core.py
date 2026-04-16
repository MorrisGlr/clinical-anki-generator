import logging
import os
import re
import shutil
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import markdown as _markdown
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)

_MODEL = "gpt-5.4"


class EnrichmentResult(BaseModel):
    enrichment_markdown: str
    tags: list[str]
    confidence: float


@dataclass
class ParsedQuestion:
    question: str
    correct_answer: str
    answer_list: str
    explanation: str
    image_paths: list[str] = field(default_factory=list)


def try_selectors(
    soup: BeautifulSoup,
    candidates: list[dict],
    tag: str = "div",
    find_all: bool = False,
    context: str = "",
) -> Any:
    """Try BeautifulSoup selector dicts in order; log WARNING when a fallback fires.

    Each candidate is a dict of keyword args passed to soup.find() or soup.find_all().
    Primary (index 0) match is silent. Fallback matches and total failure both emit WARNING.
    Returns None (find) or [] (find_all) when all candidates fail.
    """
    for i, selector_kwargs in enumerate(candidates):
        if find_all:
            result = soup.find_all(tag, **selector_kwargs)
            if result:
                if i > 0:
                    logger.warning(
                        "Fallback selector matched for %s: %s", context, selector_kwargs
                    )
                else:
                    logger.debug("Primary selector matched for %s", context)
                return result
        else:
            result = soup.find(tag, **selector_kwargs)
            if result:
                if i > 0:
                    logger.warning(
                        "Fallback selector matched for %s: %s", context, selector_kwargs
                    )
                else:
                    logger.debug("Primary selector matched for %s", context)
                return result
    logger.warning("All selectors failed for %s. Field will be empty.", context)
    return [] if find_all else None


def try_patterns(
    content: str,
    candidates: list[str],
    flags: int = 0,
    find_all: bool = False,
    context: str = "",
) -> Any:
    """Try regex pattern strings in order; log WARNING when a fallback fires.

    Primary (index 0) match is silent. Fallback matches and total failure both emit WARNING.
    Returns None (search) or [] (findall) when all candidates fail.
    """
    for i, pattern in enumerate(candidates):
        if find_all:
            result = re.findall(pattern, content, flags)
            if result:
                if i > 0:
                    logger.warning(
                        "Fallback pattern matched for %s: %r", context, pattern
                    )
                else:
                    logger.debug("Primary pattern matched for %s", context)
                return result
        else:
            result = re.search(pattern, content, flags)
            if result:
                if i > 0:
                    logger.warning(
                        "Fallback pattern matched for %s: %r", context, pattern
                    )
                else:
                    logger.debug("Primary pattern matched for %s", context)
                return result
    logger.warning("All patterns failed for %s. Field will be empty.", context)
    return [] if find_all else None


def _status_spinner(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        print("Generating text...", end="\r")
        sys.stdout.flush()
        time.sleep(2)


def markdown_to_html(raw: str) -> str:
    text = _markdown.markdown(raw)
    text = text.replace("\n", "</br>")
    text = text.replace("</p></br><h3>", "</p><h3>")
    text = text.replace("</li></br></ul></br><h3>", "</li></br></ul><h3>")
    text = text.replace("</h3></br><ul></br><li>", "</h3></br><ul><li>")
    return "</br>" + text


def generate_enrichment(
    question: str, answer: str, system_prompt: str
) -> EnrichmentResult:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    stop_event = threading.Event()
    status_thread = threading.Thread(target=_status_spinner, args=(stop_event,))
    status_thread.start()
    start_time = time.time()
    try:
        response = client.beta.chat.completions.parse(
            model=_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question + "\n" + answer},
            ],
            temperature=0.75,
            max_tokens=4096,
            response_format=EnrichmentResult,
        )
    finally:
        stop_event.set()
        status_thread.join()
    elapsed = time.time() - start_time
    logger.info("Text generation completed in %.2f seconds.", elapsed)
    print(f"\nText generation completed in {elapsed:.2f} seconds.")
    return response.choices[0].message.parsed


def copy_media(image_paths: list[str], anki_media_path: str) -> list[str]:
    """Copy image files to Anki media dir. Returns list of destination filenames."""
    dest_names: list[str] = []
    for src_path in image_paths:
        filename = os.path.basename(src_path)
        dest_path = os.path.join(anki_media_path, filename)
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            filename = base + "1" + ext
            dest_path = os.path.join(anki_media_path, filename)
        shutil.copy(src_path, dest_path)
        dest_names.append(filename)
    return dest_names


def format_for_anki(question: str, answer: str, tags: list[str] | None = None) -> str:
    if tags:
        return f"{question}\t{answer}\t{' '.join(tags)}"
    return f"{question}\t{answer}"


def run_pipeline(
    parse_fn,
    system_prompt: str,
    input_path: Path,
    output_dir: Path,
    anki_media_path: str | None = None,
    tags: bool = False,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file_path = output_dir / f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}.txt"

    input_path = Path(input_path)

    if input_path.is_file():
        file_pairs = [(input_path.read_text(encoding="utf-8"), str(input_path))]
    else:
        html_files = sorted(f for f in input_path.iterdir() if f.suffix == ".html")
        print(f"Number of HTML files in the directory: {len(html_files)}")
        file_pairs = [(f.read_text(encoding="utf-8"), str(f)) for f in html_files]

    card_num = 0
    skipped = 0
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        for content, file_path in file_pairs:
            parsed_questions = parse_fn(content, file_path)
            for pq in parsed_questions:
                card_num += 1
                if not pq.question or not pq.correct_answer:
                    logger.warning(
                        "Skipping card %d from %s: question=%s correct_answer=%s",
                        card_num,
                        file_path,
                        bool(pq.question),
                        bool(pq.correct_answer),
                    )
                    skipped += 1
                    continue
                print(f"Processing card {card_num}")

                if anki_media_path and pq.image_paths:
                    dest_names = copy_media(pq.image_paths, anki_media_path)
                    for name in dest_names:
                        pq.explanation += f'<img src="{name}">'

                result = generate_enrichment(
                    pq.question,
                    pq.correct_answer + pq.answer_list,
                    system_prompt,
                )
                gen_html = markdown_to_html(result.enrichment_markdown)
                logger.info(
                    "Enrichment confidence: %.2f | tags: %s",
                    result.confidence,
                    result.tags,
                )
                back_side = (
                    pq.correct_answer
                    + pq.answer_list
                    + pq.explanation
                    + "</br></br>"
                    + gen_html
                )
                output_file.write(
                    format_for_anki(
                        pq.question,
                        back_side,
                        tags=result.tags if tags else None,
                    )
                    + "\n"
                )
                print(f"Processed: {file_path}")
                print(f"Front side: {pq.question[:70]}")
                print(f"Back side: {back_side[:70]}\n")

    processed = card_num - skipped
    print(f"Done. Processed {processed} cards, skipped {skipped}.")
    print(f"Anki flashcards have been saved to {output_file_path}")
