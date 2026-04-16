import argparse
import os
from pathlib import Path
import re
from bs4 import BeautifulSoup
from datetime import datetime
from openai import OpenAI
import time
import threading
import sys
import markdown
import shutil
import imgkit
from dotenv import load_dotenv
load_dotenv()

# Get the API key
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key, timeout=120)

# Function to extract question, multiple choice answers, and correct answer from a single docx file and return a dictionary.
def extract_questions_and_answers(file_path):
    """
    Extracts questions, multiple-choice options, and correct answers from a given text file.

    Parameters:
    - file_path (str): Path to the text file.

    Returns:
    - questions_dict (dict): Dictionary where each key is a question string, and the value is a list containing
                             the multiple-choice options (as a string) and the correct answer.
    """
    # Read the text from the file
    with open(file_path, 'r') as file:
        text = file.read()

    # Use regex to find all the questions and their choices
    question_pattern = r"(\d+)\.\s(.*?)\n([a-f]\..*?)(?=\n\d+\.\s|\nAnswer Key:)"
    matches = re.findall(question_pattern, text, re.DOTALL)

    # Use regex to find the answer key
    answer_key_pattern = r"Answer Key:\n([\s\S]+)"
    answer_key_match = re.search(answer_key_pattern, text)
    answer_key = re.findall(r"(\d+)\.\s([A-Z])", answer_key_match.group(1))

    # Create a dictionary to store the questions, options, and answers
    questions_dict = {}

    # Create a mapping of question numbers to answers for accurate linking
    answer_dict = {num: ans for num, ans in answer_key}

    for match in matches:
        question_num = match[0].strip()
        question_text = match[1].strip()
        # Replace new lines with HTML line breaks
        question_text = question_text.replace("\n", "</br>")
        try:
            # remove tabs from the question text
            question_text = question_text.replace("\t", " ")
        except:
            pass

        options_text = match[2].strip()
        # Remove the tabs from the options text
        options_text = options_text.replace("\t", " ")
        # Replace new lines with HTML line breaks
        options_text = options_text.replace("\n", "</br>")
        
        # Combine the question number with the question text
        question_key = f"{question_num}. {question_text}"
        
        # Look up the correct answer based on the question number
        correct_answer = answer_dict.get(question_num, "Answer not found")
        
        # Store in the dictionary
        questions_dict[question_key] = [options_text, f"Correct answer: {correct_answer}"]
    
    print(f"Extracted {len(questions_dict)} questions and {len(answer_dict)} answers from the file.")
    return questions_dict


# Function to format the extracted text into Anki flashcard format
def format_for_anki(question, answer):
    return f"{question}\t{answer}"

# Function to print the status message
def print_status(stop_event):
    while not stop_event.is_set():
        print("Generating text...", end="\r")
        sys.stdout.flush()  # Ensure the message is printed immediately
        time.sleep(2)  # Adjust this value to change the frequency

# Function to use GPT-4o to generate complementary explanations for the questions
def generate_explanations(question, answer):
    # Create a stop event to control the status printing thread
    stop_event = threading.Event()

    # Start the status printing thread
    status_thread = threading.Thread(target=print_status, args=(stop_event,))
    status_thread.start()

    # Record the start time
    start_time = time.time()

    try:
      response = client.responses.create(
            model="o3-2025-04-16",
            input=[
                {
                    "role": "system",
                    "content": prompt_markdown
                },
                {
                    "role": "user",
                    "content": question + '\n' + answer
                }
            ],
            #temperature=0.1,
            max_output_tokens= 6384,
            timeout=120
            )
    finally:
        # Stop the status printing thread
        stop_event.set()
        status_thread.join()

    # Calculate the elapsed time
    elapsed_time = time.time() - start_time
    gen_text = response.output_text
    #gen_text = gen_text.replace("\t", "&emsp;").replace("\n", "<br>")
    # Wrap the content in a <div> or other HTML tag for better formatting
    gen_text = markdown.markdown(gen_text)
    gen_text = gen_text.replace('\n', '</br>')
    gen_text = gen_text.replace('</p></br><h3>', '</p><h3>')
    gen_text = gen_text.replace('</li></br></ul></br><h3>', '</li></br></ul><h3>')
    gen_text = gen_text.replace('</h3></br><ul></br><li>', '</h3></br><ul><li>')
    #gen_text = gen_text.replace('</li></br><li><strong>', '</li><li><strong>')
    #gen_text = gen_text.replace('</h3></br><ul><li><strong>', '</h3><ul><li><strong>')
    gen_text = '</br>' + gen_text

    # Print the elapsed time
    print(f"\nText generation completed in {elapsed_time:.2f} seconds.")
    try:
        usage_data = response.usage
        print(f"Usage stats per flashcard: (input_tokens: {usage_data.input_tokens}, output_tokens: {usage_data.output_tokens}, total_tokens: {usage_data.total_tokens})")
    except Exception as e:
        print(f"Error extracting usage data: {e}")
    return gen_text

def main(argv=None):
    global prompt_markdown

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Convert NBME practice form text file to Anki flashcards.')
    parser.add_argument('--input', type=Path, required=True,
                        help='Path to the NBME practice form .txt file')
    parser.add_argument('--output', type=Path, default=Path('./gen_anki'),
                        help='Output directory for Anki flashcard files (default: ./gen_anki)')
    args = parser.parse_args(argv)

    file_path = args.input
    output_dir = args.output

    prompt_markdown = """# Role
- You are a helpful biomedical/bioclinical and medical education expert specializing in preparing students for NBME shelf exams and Step 2CK. 
- Teach students like an expert tutor and clinical attending physician that is supportive and encouraging.

# Objective
- Your goal is to provide concise, high-yield explanations for NBME style questions that enhance student understanding and focus on core concepts critical for exam success.

# Instructions
- **Follow the explanation rubric and instructions provided below.**
- Process each question and answer. I will submit the questions, their corresponding answer choices, and the correct answer to you one at a time.
- Your job is the explain the **correct answer of the question according to the answer key that is provided to you.**
- **DO NOT select the correct answer yourself. I will provide it to you.**
- Provide a detailed explanation for each question to help students understand the reasoning behind the correct answer (provided by user/student), why the incorrent answers are wrong, and the clinical concepts involved.

# Criteria
- **Prioritize accuracy and factuality in your responses.**
- Ground your explanations on established medical knowledge, clinical guidelines, reputatable sources, and high-yield concepts relevant to USMLE Step 2CK and NBME shelf exams.
- Give it your all and do not hold back.
- If you are unsure about something, please let me know.
- Be thorough in your explanations.
- Think deeply about the clinical concepts and testing strategies involved.
- Stay organized and structured in your explanations.
- Logically connect the details in the vignette, critical reasoning, pathophysiology, treatments, and diagnositic tests to the correct answer choice that is provided.
- If you use abreviations or acronyms, please define them the first time you use them.
## Explanation Rubric
### Correct Answer Selection
- [place the correct answer that is provided to you here]
### Vignette Analysis
- Identify and explain key words, phrases, and clues in the vignette critical for diagnosing the condition.
- Clearly describe how specific details in the vignette help narrow the differential diagnosis, highlighting what to rule in and out.
- Point out the pertinent positives and negatives in the vignette that lead to the correct answer.
- Note the patterns and algorithms that are essential for recognizing the condition being tested.
- Also provide a cognitve and metacognitive analysis of the vignette, including how to approach similar questions in the future with a framework.
### Clinical Critical Reasoning
- Emphasize pattern recognition, management algorithms, clinical reasoning steps, and common pitfalls to avoid.
- Correct Answer Explanation: Provide a focused explanation of the reasoning behind the correct answer **that is provided to you by the user**. 
- Outline the clinical thought process in a step-wise approach linking key vignette details to the correct choice.
- Highlight the core concept or "takeaway message" that the question is testing.
- Note what would need to be documented in the medical record if this were a real patient encounter.
### Pathophysiology Review
- Balance between a concise and detailed review of the disease’s pathophysiology, including etiology, risk factors, mechanisms, and clinical manifestations.
- The level of detail needs to be appropriate for the content covered on USLME STEP 2 exams and in UWorld STEP 2 exam practice questions.
### Treatments and Diagnostic Tests Review
- discuss management algorithms.
- Summarize the treatment approach, including first-line and second-line treatments, and name specific drugs if applicable (avoid saying a medication category only; give exact drug names in that category).
- If applicable, include imaging studies, lab tests, or other diagnostic tools that are relevant to the vignette.
- If labs or imaging are needed for the diagnosis, please justify their use in the context of the vignette and how it would affect the management of the patient.
- Connect these pieces of information logically, illustrating how they lead to the clinical presentation in the vignette.
- If antibiotics are mentioned, please explain why they are used. Provide a logical framework for their use in the context of the vignette and how to logically connect them to the clinical presentation so that it is easy to recall during exams.
### Memorization Tips
- Provide mnemonics, acronyms, or other memory aids to help students retain the key concepts.
- Suggest ways to remember the critical details, such as common associations or patterns that can help in recalling the information during exams.
- Perhaps provide a memory palace or visualization technique that can help students remember the key points.
### Incorrect Answer Analysis
- For each incorrect option, explain the clinical findings, history details, diagnostic test results, and treatment approaches (including medications, if applicable) that would be expected if the option were correct.
- Highlight the key differences between these expected findings and those in the vignette.
- Address common misconceptions or traps in reasoning that students might encounter."""

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get current date, hour, minute for the output file name
    current_date = datetime.now().strftime('%Y-%m-%d_%H-%M')

    output_file_path = os.path.join(output_dir, f'{current_date}.txt')

    # Iterate through
    questions_dict = extract_questions_and_answers(file_path)
    #for question, content in questions_dict.items():
    #    print(f"Question: {question[:10]}\nCorrect Answer:\n{content[1]}\n")

    # Write the questions and answers to the output file in Anki format
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        for question, content in questions_dict.items():
            correct_answer_str = content[1]
            answer_list_str = content[0]
            back_side = correct_answer_str+ '</br></br>' + answer_list_str
            #print(f"Question: {question}\nOptions:\n{content[0]}\n{content[1]}\n")
            gen_text = generate_explanations(question, correct_answer_str+ '</br></br>' + answer_list_str)
            back_side = back_side + '</br></br>' + gen_text
            anki_format_text = format_for_anki(question, back_side)
            output_file.write(anki_format_text + '\n')
            # Debugging output to verify correct processing
            print(f"Processed NMBE form question.")
            print(f"Front side of card preview: {question[:70]}")
            print(f"Back side of card preview: {back_side[:70]}"+"\n")

    print(f"Done. Anki flashcards have been saved to {output_file_path}")


if __name__ == '__main__':
    main()
