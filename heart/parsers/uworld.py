import os

from bs4 import BeautifulSoup

from heart.core import ParsedQuestion

SYSTEM_PROMPT = (
    "You are a biomedical and medical education expert specializing in preparing students"
    " for NBME shelf exams. The level of detail should be proportionate to their relevance"
    " to the vignette. Below is a practice question along with its answer.\n\n"
    " Vignette Analysis: Identify and explain key words or phrases in the vignette that are"
    " critical for diagnosing the condition. Describe how these details help narrow down the"
    " differential diagnosis, focusing on what to rule in and rule out.\n\n"
    "Correct Answer Explanation: Clearly explain the reasoning behind the correct answer."
    " Discuss the thought process a student should follow, focusing on learning the core"
    " concept.\n\n"
    "Pathophysiology Review: Provide a brief overview of the disease's pathophysiology,"
    " including etiology, risk factors, mechanisms, clinical manifestations, and treatment.\n\n"
    "Incorrect Answer Review: Instead of simply stating that the incorrect choice doesn't"
    " match the vignette, explain what clinical findings, history details, diagnostic test"
    " results, and treatment approaches would be expected if this option were correct."
    " Highlight the key differences between these expected findings and those presented in"
    " the vignette.\n\n"
    "Your response must be a JSON object with these fields:\n\n"
    "- enrichment_markdown (string): the full back-of-card explanation in Markdown, covering"
    " all sections above.\n"
    "- tags (array of exactly 6 strings): a mix of USMLE controlled-vocabulary organ-system"
    " terms (e.g. cardiovascular, respiratory, gastrointestinal, renal, endocrine,"
    " hematology, infectious_disease, neurology, musculoskeletal, dermatology, psychiatry,"
    " obstetrics_gynecology, pediatrics, surgery, pharmacology) and free-text subject or"
    " mechanism terms specific to this question (e.g. beta_blocker, heart_failure,"
    " sodium_balance). Normalize all tags to lowercase with underscores. Provide exactly 6.\n"
    "- confidence (float 0.0–1.0): your self-reported confidence in the accuracy and"
    " completeness of enrichment_markdown. 1.0 = fully confident, 0.0 = highly uncertain."
)

_QUESTION_DIV_ID = "questionText"
_CORRECT_ANSWER_DIV_CLASS = (
    "omitted-answer content d-flex align-items-start flex-column ng-star-inserted"
)
_ANSWER_LIST_DIV_ID = "answerContainer"
_EXPLANATION_DIV_ID = "explanation-container"


def parse(content: str, file_path: str) -> list[ParsedQuestion]:
    """Extract question fields from UWorld HTML content."""
    soup = BeautifulSoup(content, "html.parser")

    question_div = soup.find("div", id=_QUESTION_DIV_ID)
    question_str = question_div.get_text(separator=" ", strip=True) if question_div else ""
    question_str = question_str.replace("\n", " ")
    try:
        question_str = question_str.split(" ", 1)[1]
    except IndexError:
        print(
            "Warning: Could not remove leading number from question string."
            " Manual editing in Anki might be necessary. Continuing..."
        )

    correct_answer_div = soup.find("div", class_=_CORRECT_ANSWER_DIV_CLASS)
    correct_answer_str = (
        correct_answer_div.get_text(separator=" ", strip=True) if correct_answer_div else ""
    )
    if not correct_answer_str:
        print("Warning: Correct answer string is empty. Continuing...")
    correct_answer_str = correct_answer_str.replace("\n", " ")
    correct_answer_str = correct_answer_str.replace("Omitted ", " ")
    correct_answer_str += "</br>"

    answer_list_divs = soup.find_all("div", id=_ANSWER_LIST_DIV_ID)
    answer_list_str = "".join(
        f"{chr(65 + i)}. {div.get_text(separator=' ', strip=True)}"
        for i, div in enumerate(answer_list_divs)
    )
    for i in range(1, 10):
        answer_list_str = answer_list_str.replace(
            f") {chr(64 + i)}. ", f")</br>{chr(64 + i)}. "
        )
    answer_list_str = answer_list_str.replace("\n", " ")
    answer_list_str = answer_list_str.replace("A. A. ", "A. ")
    answer_list_str = "</br>" + answer_list_str

    explanation_divs = soup.find_all("div", id=_EXPLANATION_DIV_ID)
    explanation_str = "</br></br>".join(
        div.get_text(separator=" ", strip=True) for div in explanation_divs
    )
    explanation_str = explanation_str.replace("\n", " ")
    explanation_str = explanation_str.replace(" (Choice", "</br></br>(Choice")
    explanation_str = explanation_str.replace("Explanation ", "")
    explanation_str = explanation_str.replace(
        "Topic Copyright \u00a9 UWorld. All rights reserved.", " "
    )
    explanation_str = explanation_str.replace("</br></br></br>Explanation: ", "</br>Explanation: ")
    explanation_str = explanation_str.replace("User Id: 1514650 ", "")
    explanation_str = "</br></br>" + explanation_str

    # Collect image paths from companion *_files/ directory
    image_paths: list[str] = []
    if file_path.endswith(".html"):
        files_dir = file_path[:-5] + "_files"
        if os.path.isdir(files_dir):
            for fname in os.listdir(files_dir):
                if fname.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                    image_paths.append(os.path.join(files_dir, fname))

    return [
        ParsedQuestion(
            question=question_str,
            correct_answer=correct_answer_str,
            answer_list=answer_list_str,
            explanation=explanation_str,
            image_paths=image_paths,
        )
    ]
