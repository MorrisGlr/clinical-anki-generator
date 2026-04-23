from bs4 import BeautifulSoup

from cast.core import ParsedQuestion, try_selectors

SYSTEM_PROMPT = (
    "You are a savvy expert with medical knowledge that trains medical students for NMBE"
    " shelf exams. I need help learning concepts from this NBME self-exam-style question."
    " Pasted below is a practice question with its corresponding answer."
    " 1. Provide a vignette analysis (what words should I be paying attention to in the"
    " vignette and why. How does it relate to what a student wants to rule in and rule out?)"
    " 2a. Explain the correct answer and the train of thought a student needs to consider to"
    " learn the content effectively. Also briefly explain the related pathophysiology as well."
    " 2b. If applicable mention and explain relevant anatomy."
    " 3. Explain other diseases that should be considered on the differential diagnosis"
    " (3 other diseases but are ultimately incorrect for this vignette) and describe key"
    " differentiating indicators (pertinent positives and negatives)."
    " 4. Discuss the distractors in the vignette (and how they could lead a student astray"
    " from the right answer)."
    " 5. Provide related test-taking strategies."
    " 6. Provide pertinent mnemonics to the clinical correlations.\n\n"
    "Your response must be a JSON object with these fields:\n\n"
    "- enrichment_markdown (string): the full back-of-card explanation in Markdown, covering"
    " all sections above.\n"
    "- tags (array of exactly 6 strings): a mix of USMLE controlled-vocabulary organ-system"
    " terms (e.g. obstetrics_gynecology, endocrine, cardiovascular, renal, hematology,"
    " infectious_disease, gastrointestinal, neurology, pediatrics, pharmacology) and free-text"
    " subject or mechanism terms specific to this question (e.g. preeclampsia, cervical_ripening,"
    " postpartum_hemorrhage). Normalize all tags to lowercase with underscores. Provide exactly 6.\n"
    "- confidence (float 0.0–1.0): your self-reported confidence in the accuracy and"
    " completeness of enrichment_markdown. 1.0 = fully confident, 0.0 = highly uncertain."
)

_QUESTION_SELECTORS = [
    {"id": "questionText"},
    {"id": "question-text"},
    {"attrs": {"data-testid": "question-text"}},
]
_CORRECT_ANSWER_SELECTORS = [
    {"class_": "omitted-answer content d-flex align-items-start flex-column ng-star-inserted"},
    {"class_": "omitted-answer content d-flex align-items-start flex-column"},
    {"class_": "omitted-answer"},
    {"attrs": {"aria-checked": "true"}},
]
_ANSWER_LIST_SELECTORS = [
    {"id": "answerContainer"},
    {"id": "answer-container"},
    {"class_": "answerContainer"},
]
_EXPLANATION_SELECTORS = [
    {"id": "explanation-container"},
    {"class_": "explanation-container"},
    {"id": "explanation"},
]


def parse(content: str, file_path: str) -> list[ParsedQuestion]:
    """Extract question fields from APGO HTML content."""
    soup = BeautifulSoup(content, "html.parser")

    question_div = try_selectors(soup, _QUESTION_SELECTORS, context="apgo:question")
    question_str = question_div.get_text(separator=" ", strip=True) if question_div else ""
    question_str = question_str.replace("\n", " ")
    try:
        question_str = question_str.split(" ", 1)[1]
    except IndexError:
        pass

    correct_answer_div = try_selectors(
        soup, _CORRECT_ANSWER_SELECTORS, context="apgo:correct_answer"
    )
    correct_answer_str = (
        correct_answer_div.get_text(separator=" ", strip=True) if correct_answer_div else ""
    )
    correct_answer_str = correct_answer_str.replace("\n", " ")
    correct_answer_str = correct_answer_str.replace("Omitted ", " ")
    correct_answer_str += "</br>"

    answer_list_divs = try_selectors(
        soup, _ANSWER_LIST_SELECTORS, find_all=True, context="apgo:answer_list"
    )
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

    explanation_divs = try_selectors(
        soup, _EXPLANATION_SELECTORS, find_all=True, context="apgo:explanation"
    )
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

    return [
        ParsedQuestion(
            question=question_str,
            correct_answer=correct_answer_str,
            answer_list=answer_list_str,
            explanation=explanation_str,
            image_paths=[],
        )
    ]
