import logging
import os
import shutil
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import markdown as _markdown
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

_MODEL = "gpt-5.4"


@dataclass
class ParsedQuestion:
    question: str
    correct_answer: str
    answer_list: str
    explanation: str
    image_paths: list[str] = field(default_factory=list)


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


def generate_enrichment(question: str, answer: str, system_prompt: str) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    stop_event = threading.Event()
    status_thread = threading.Thread(target=_status_spinner, args=(stop_event,))
    status_thread.start()
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question + "\n" + answer},
            ],
            temperature=0.75,
            max_tokens=4096,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
    finally:
        stop_event.set()
        status_thread.join()
    elapsed = time.time() - start_time
    gen_text = response.choices[0].message.content
    logger.info("Text generation completed in %.2f seconds.", elapsed)
    print(f"\nText generation completed in {elapsed:.2f} seconds.")
    return markdown_to_html(gen_text)


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


def format_for_anki(question: str, answer: str) -> str:
    return f"{question}\t{answer}"


def run_pipeline(
    parse_fn,
    system_prompt: str,
    input_path: Path,
    output_dir: Path,
    anki_media_path: str | None = None,
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
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        for content, file_path in file_pairs:
            parsed_questions = parse_fn(content, file_path)
            for pq in parsed_questions:
                card_num += 1
                print(f"Processing card {card_num}")

                if anki_media_path and pq.image_paths:
                    dest_names = copy_media(pq.image_paths, anki_media_path)
                    for name in dest_names:
                        pq.explanation += f'<img src="{name}">'

                gen_text = generate_enrichment(
                    pq.question,
                    pq.correct_answer + pq.answer_list,
                    system_prompt,
                )
                back_side = (
                    pq.correct_answer
                    + pq.answer_list
                    + pq.explanation
                    + "</br></br>"
                    + gen_text
                )
                output_file.write(format_for_anki(pq.question, back_side) + "\n")
                print(f"Processed: {file_path}")
                print(f"Front side: {pq.question[:70]}")
                print(f"Back side: {back_side[:70]}\n")

    print(f"Done. Anki flashcards have been saved to {output_file_path}")
