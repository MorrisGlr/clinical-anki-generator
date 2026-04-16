from bs4 import BeautifulSoup

from heart.core import ParsedQuestion

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
    "At the very end of your response, on its own line, write exactly:\n"
    "TAGS: tag1, tag2, tag3\n"
    "Provide 2–3 comma-separated lowercase tags: the primary medical subject (e.g. obstetrics),"
    " the organ system (e.g. reproductive), and optionally a third relevant tag."
    " Do not write anything after this line."
)

_QUESTION_DIV_ID = "questionText"
_CORRECT_ANSWER_DIV_CLASS = (
    "omitted-answer content d-flex align-items-start flex-column ng-star-inserted"
)
_ANSWER_LIST_DIV_ID = "answerContainer"
_EXPLANATION_DIV_ID = "explanation-container"


def parse(content: str, file_path: str) -> list[ParsedQuestion]:
    """Extract question fields from APGO HTML content."""
    soup = BeautifulSoup(content, "html.parser")

    question_div = soup.find("div", id=_QUESTION_DIV_ID)
    question_str = question_div.get_text(separator=" ", strip=True) if question_div else ""
    question_str = question_str.replace("\n", " ")
    try:
        question_str = question_str.split(" ", 1)[1]
    except IndexError:
        pass

    correct_answer_div = soup.find("div", class_=_CORRECT_ANSWER_DIV_CLASS)
    correct_answer_str = (
        correct_answer_div.get_text(separator=" ", strip=True) if correct_answer_div else ""
    )
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

    return [
        ParsedQuestion(
            question=question_str,
            correct_answer=correct_answer_str,
            answer_list=answer_list_str,
            explanation=explanation_str,
            image_paths=[],
        )
    ]
