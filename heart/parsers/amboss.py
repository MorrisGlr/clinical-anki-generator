from bs4 import BeautifulSoup

from heart.core import ParsedQuestion

SYSTEM_PROMPT = (
    "You are a medical education expert specializing in preparing students for NBME shelf"
    " exams. The level of detail should be proportionate to their relevance to the vignette."
    " Below is a practice question along with its answer.\n\n"
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

# All four known CSS class variants for the correct-answer div, tried in order.
_CORRECT_ANSWER_CLASS_VARIANTS = [
    "container--CKAXW correctAnswer--xNrke",
    "container--CKAXW pointer--eMKos correctAnswer--xNrke",
    "container--CKAXW pointer--eMKos correctAnswer--xNrke",
    "-f8b48b6542a07-container -f8b48b6542a07-pointer -f8b48b6542a07-correctAnswer",
]
_EXPLANATION_DIV_CLASS = "-f8b48b6542a07-explanationContainer"


def _question_id_from_path(file_path: str) -> str:
    import os

    filename = os.path.basename(file_path)
    for length in (3, 2, 1):
        if len(filename) > length and filename[:length].isdigit():
            return f"FLaJnh0OIM_{filename[:length]}"
    return "FLaJnh0OIM_1"


def parse(content: str, file_path: str) -> list[ParsedQuestion]:
    """Extract question fields from AMBOSS HTML content."""
    soup = BeautifulSoup(content, "html.parser")
    question_id = _question_id_from_path(file_path)

    question_div = soup.find("div", id=question_id)
    question_str = question_div.get_text(separator=" ", strip=True) if question_div else ""
    question_str = question_str.replace("\n", " ")
    try:
        if question_str and question_str[0].isdigit():
            question_str = question_str.split(" ", 1)[1]
    except IndexError:
        print(f"Warning: Did not find a number at start of question for {question_id}")

    correct_answer_str = ""
    for css_class in _CORRECT_ANSWER_CLASS_VARIANTS:
        div = soup.find("div", class_=css_class)
        if div:
            correct_answer_str = div.get_text(separator=" ", strip=True)
            break
    if not correct_answer_str:
        print(f"Warning: Correct answer not found for question {question_id}")
    correct_answer_str = correct_answer_str.replace("\n", " ")
    correct_answer_str = correct_answer_str.replace("Give feedback", "")
    correct_answer_str += "</br>"
    correct_answer_str = "Correct Answer: " + correct_answer_str

    explanation_divs = soup.find_all("div", class_=_EXPLANATION_DIV_CLASS)
    if not explanation_divs:
        print(f"Warning: Explanation not found for question {question_id}")
    explanation_str = "</br></br>".join(
        div.get_text(separator=" ", strip=True) for div in explanation_divs
    )
    explanation_str = explanation_str.replace("\n", " ")
    explanation_str = explanation_str.replace("Give feedback", "")
    explanation_str = "</br>" + explanation_str

    return [
        ParsedQuestion(
            question=question_str,
            correct_answer=correct_answer_str,
            answer_list="",
            explanation=explanation_str,
            image_paths=[],
        )
    ]
