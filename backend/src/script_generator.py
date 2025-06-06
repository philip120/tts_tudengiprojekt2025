import google.generativeai as genai
import os
import re
import time 

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    API_KEY = "" 

if not API_KEY:
    raise ValueError("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")

genai.configure(api_key=API_KEY)

MODEL_NAME = "gemini-2.0-flash"


def generate_podcast_script(pdf_path: str) -> list[dict[str, str]]:
    """
    Generates a two-speaker podcast script from an input PDF file using the Gemini API.

    Args:
        pdf_path: The file path to the PDF document.

    Returns:
        A list of dictionaries, where each dictionary represents a line of dialogue:
        [{'speaker': 'A', 'text': '...'}, {'speaker': 'B', 'text': '...'}]
        Returns an empty list if generation fails.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return []

    print(f"Uploading file: {pdf_path}...")
    try:
        
        pdf_file = genai.upload_file(path=pdf_path, display_name=os.path.basename(pdf_path))
        print(f"Uploaded file '{pdf_file.display_name}' as: {pdf_file.name}")

    

    except Exception as e:
        print(f"Failed to upload file {pdf_path}: {e}")
        return []

    model = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""
    You are a podcast script writer. Attached is a PDF document (file name: {pdf_file.display_name}). Your task is to read this document and convert its content into a conversational podcast script between two distinct speakers: "Speaker A" and "Speaker B".

    Instructions:
    1.  Analyze the content of the provided PDF document ({pdf_file.name}).
    2.  Create a natural-sounding conversation where Speaker A and Speaker B discuss the main points and key information from the document.
    3.  **Generally alternate** between Speaker A and Speaker B, but feel free to allow a speaker to have **two consecutive turns occasionally** if it improves the conversational flow (e.g., asking and immediately answering a rhetorical question, or elaborating on a point). Ensure a reasonable balance overall.
    4.  Keep the tone informative yet engaging, suitable for a podcast format. You can be funny and engaging, sometimes using mild colloquialisms or even a word like "shit" if it genuinely fits the context and tone, but use such language sparingly and appropriately.
    5.  Aim for individual speaking turns to be **around 150-200 characters** as a guideline, but **allow for occasional longer contributions (up to 400-500 characters)** if a speaker is explaining a complex point. Prioritize natural conversation over strict length adherence.
    6.  The script should cover the core information from the document but doesn't need to include every single detail. Focus on clarity and conversational flow.
    7.  The total script should be suitable for a podcast duration of roughly 3-5 minutes.
    8.  **Crucially, format the output ONLY as follows:** Each line must start with either "Speaker A:" or "Speaker B:", followed by the dialogue for that speaker. Do not include any introductory text, concluding remarks, titles, or any other text outside of this strict format.

    Example Output Format:
    Speaker A: Welcome to our podcast episode today!
    Speaker B: Thanks! Today we're diving into the document titled '{pdf_file.display_name}'.
    Speaker A: Indeed. The first key point seems to be...
    Speaker B: Right, and that connects to...
    Speaker B: ...which is quite interesting when you consider the implications.
    Speaker A: Absolutely. Moving on, another important aspect is...

    Please generate the podcast script based *only* on the attached PDF document.
    """

    print(f"Generating script from PDF: {pdf_path}...")
    try:
        response = model.generate_content([prompt, pdf_file])

        
        if response.text:
            script_text = response.text.strip()
            parsed_script = []
            lines = script_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("Speaker A:"):
                    parsed_script.append({"speaker": "A", "text": line.replace("Speaker A:", "").strip()})
                elif line.startswith("Speaker B:"):
                    parsed_script.append({"speaker": "B", "text": line.replace("Speaker B:", "").strip()})
            return parsed_script
        else:
            print("Error: Gemini API returned an empty response.")
            
            return []

    except Exception as e:
        print(f"An error occurred during Gemini API call: {e}")
        
        return []
