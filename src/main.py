# src/main.py

import sys
import os
import argparse

# Adjust the Python path to include the src directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Only import the script generator
from src.script_generator import generate_podcast_script

# Default input directory (useful for help text)
DEFAULT_INPUT_DIR = "input/"

def main(args):
    print("Starting script generation process...")

    # --- Define and Check Input PDF Path --- 
    base_dir = parent_dir
    pdf_input_path = os.path.abspath(os.path.join(base_dir, args.pdf_file))

    if not os.path.exists(pdf_input_path):
        print(f"Error: Input PDF not found at {pdf_input_path}")
        sys.exit(1)

    print(f"Input PDF: {pdf_input_path}")

    # --- Generate Script --- 
    print("\nGenerating podcast script using Gemini...")
    structured_script = generate_podcast_script(pdf_input_path)

    if not structured_script:
        print("Error: Failed to generate script. Exiting.")
        sys.exit(1)

    # --- Print Generated Script --- 
    print("\n--- Generated Script ---")
    for i, line in enumerate(structured_script):
        # Ensure consistent formatting
        speaker = line.get('speaker', 'Unknown')
        text = line.get('text', '')
        print(f"Speaker {speaker}: {text}")
    print("------------------------\n")
    print("Script generation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a podcast script from a PDF using Gemini and print it.")

    # Only argument needed is the input PDF
    parser.add_argument("pdf_file", 
                        help=f"Path to the input PDF file (relative to project root, e.g., {os.path.join(DEFAULT_INPUT_DIR, 'pdf/philip_paskov_cv.pdf')})")

    parsed_args = parser.parse_args()
    main(parsed_args) 