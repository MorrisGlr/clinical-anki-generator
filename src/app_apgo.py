import argparse
import os
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from openai import OpenAI
import time
import threading
import sys
import markdown
from dotenv import load_dotenv
load_dotenv()

# Get the API key
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)


# Note: The HTML files should be in the 'html_dump' directory and each html file should have a file name with the question number as the first two characters. Remember to change the directory paths to match your local setup.
# Function to extract text from a given HTML element and remove HTML tags
def extract_text_from_html(html_content, question_div_id, correct_answer_div_class, answer_list_div_id, explanation_div_id):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract question
    question_div = soup.find('div', id=question_div_id)
    question_str = question_div.get_text(separator=' ', strip=True) if question_div else ""
    # remove new line characters
    question_str = question_str.replace('\n', ' ')
    # if the first characters are numbers, remove them until the first space
    question_str = question_str.split(' ', 1)[1]

    # Extract correct answer
    correct_answer_div = soup.find('div', class_=correct_answer_div_class)
    correct_answer_str = correct_answer_div.get_text(separator=' ', strip=True) if correct_answer_div else ""
    # add new line after the correct answer
    correct_answer_str = correct_answer_str.replace('\n', ' ')
    correct_answer_str = correct_answer_str.replace('Omitted ', ' ')
    correct_answer_str += '</br>'
    #print(correct_answer_str)

    # Extract answer choices
    answer_list_div = soup.find_all('div', id=answer_list_div_id)
    # join the answer choices into a single string while adding the multiple choice letters and new line characters
    answer_list_str = ''.join(''.join([f'{chr(65 + i)}. ', div.get_text(separator=' ', strip=True)]) for i, div in enumerate(answer_list_div))
    # for a string that contains ") {any letter}. ", add a new line character '</br>' before the letter. Flexible to hanle any number of answer choices.
    for i in range(1, 10):
        try:
            answer_list_str = answer_list_str.replace(f') {chr(64 + i)}. ', f')</br>{chr(64 + i)}. ')
        except:
            break
    # remove new line characters
    answer_list_str = answer_list_str.replace('\n', ' ')
    answer_list_str = answer_list_str.replace('A. A. ', 'A. ')
    answer_list_str = '</br>' + answer_list_str

    # Extract explanation
    explanation_divs = soup.find_all('div', id=explanation_div_id)
    explanation_str = '</br></br>'.join(div.get_text(separator=' ', strip=True) for div in explanation_divs)
    # remove new line characters
    explanation_str = explanation_str.replace('\n', ' ')
    explanation_str = explanation_str.replace(' (Choice', '</br></br>(Choice')
    explanation_str = explanation_str.replace('Explanation ', '')
    explanation_str = explanation_str.replace('Topic Copyright © UWorld. All rights reserved.', ' ')
    explanation_str = explanation_str.replace('</br></br></br>Explanation: ', '</br>Explanation: ')
    explanation_str = explanation_str.replace('User Id: 1514650 ', '')

    explanation_str = '</br></br>' + explanation_str

    # combine correct answer and explanation
    back_side = correct_answer_str + answer_list_str + explanation_str


    return question_str, back_side, correct_answer_str, answer_list_str, explanation_str

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
      response = client.chat.completions.create(
          model='gpt-4o',
          messages=[
              {
                  "role": "system",
                  "content": "You are a savvy expert with medical knowledge that trains medical students for NMBE shelf exams. I need help learning concepts from this NBME self-exam-style question. Pasted below is a practice question with its corresponding answer. 1. Provide a vignette analysis (what words should I be paying attention to in the vignette and why. How does it relate to what a student wants to rule in and rule out?) 2a. Explain the correct answer and the train of thought a student needs to consider to learn the content effectively. Also briefly explain the related pathophysiology as well. 2b. If applicable mention and explain relevant anatomy. 3. Explain other diseases that should be considered on the differential diagnosis (3 other diseases but are ultimately incorrect for this vignette) and describe key differentiating indicators (pertinent positives and negatives). 4. Discuss the distractors in the vignette (and how they could lead a student astray from the right answer). 5. Provide related test-taking strategies. 6. Provide pertinent mnemonics to the clinical correlations."
              },
              {
                  "role": "user",
                  "content": question + '\n' + answer
              }
          ],
          temperature=0.75,
          max_tokens= 4096,
          top_p=1,
          frequency_penalty=0,
          presence_penalty=0
          )
    finally:
        # Stop the status printing thread
        stop_event.set()
        status_thread.join()

    # Calculate the elapsed time
    elapsed_time = time.time() - start_time
    gen_text = response.choices[0].message.content
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
    return gen_text

def main(argv=None):
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Convert APGO HTML files to Anki flashcards.')
    parser.add_argument('--input', type=Path, default=Path('./html_dump'),
                        help='Directory containing saved HTML files (default: ./html_dump)')
    parser.add_argument('--output', type=Path, default=Path('./gen_anki'),
                        help='Output directory for Anki flashcard files (default: ./gen_anki)')
    args = parser.parse_args(argv)

    html_dir = args.input
    output_dir = args.output

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get current date, hour, minute for the output file name
    current_date = datetime.now().strftime('%Y-%m-%d_%H-%M')

    output_file_path = os.path.join(output_dir, f'{current_date}.txt')

    # Classes to identify the HTML divs
    #question_div_class = 'questionListContainer--hbbIy containerMuted--arxU8'
    question_div_id = 'questionText'
    correct_answer_div_class = 'omitted-answer content d-flex align-items-start flex-column ng-star-inserted'
    answer_list_div_id = 'answerContainer'
    explanation_div_id = 'explanation-container'

    # print number of html files in the directory
    html_files = [f for f in os.listdir(html_dir) if f.endswith('.html')]
    print(f"Number of HTML files in the directory: {len(html_files)}")

    # Process each HTML file in the directory
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        for filename in os.listdir(html_dir):
            if filename.endswith('.html'):
                html_file_path = os.path.join(html_dir, filename)
                # check if the first character in the file name is a number followed by a character, also check if the first two characters are numbers followed by a character, also check if the first three characters are numbers followed by a character. Then use the first one, two, or three characters as the question id suffix.
                if filename[0].isdigit() and filename[1].isalpha():
                    question_id_suffix = filename[0]
                elif filename[0].isdigit() and filename[1].isdigit() and filename[2].isalpha():
                    question_id_suffix = filename[:2]
                elif filename[0].isdigit() and filename[1].isdigit() and filename[2].isdigit() and filename[3].isalpha():
                    question_id_suffix = filename[:3]
                with open(html_file_path, 'r', encoding='utf-8') as html_file:
                    html_content = html_file.read()
                    question, back_side, correct_answer_str, answer_list_str, explanation_str = extract_text_from_html(
                        html_content, question_div_id, correct_answer_div_class, answer_list_div_id, explanation_div_id
                    )
                    #print("correct_answer_str: ", correct_answer_str)
                    #print("answer_list_str: ", answer_list_str)
                    #print("explanation_str: ", explanation_str)
                    # print file processing number, e.g., file 1 of 100
                    print(f"File {html_files.index(filename)+1} of {len(html_files)}")
                    gen_text = generate_explanations(question, correct_answer_str + answer_list_str)
                    back_side = back_side + '</br></br>' + gen_text
                    anki_format_text = format_for_anki(question, back_side)
                    output_file.write(anki_format_text + '\n')
                    # Debugging output to verify correct processing
                    print(f"Processed file: {filename}")
                    print(f"Front side: {question[:70]}")
                    print(f"Back side: {back_side[:70]}"+"\n")

    print(f"Done. Anki flashcards have been saved to {output_file_path}")


if __name__ == '__main__':
    main()