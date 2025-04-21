# src/main.py

import sys
import os
import argparse
import json

# Adjust the Python path to include the src directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import necessary modules
from src.script_generator import generate_podcast_script
from src.tts_processor import process_script_for_tts # Import the processor

# Default directories
DEFAULT_INPUT_DIR = "input/"
DEFAULT_OUTPUT_DIR = "output/"

def main(args):
    print("Starting script generation process...")

    # --- Define Paths --- 
    base_dir = parent_dir
    pdf_input_path = os.path.abspath(os.path.join(base_dir, args.pdf_file))
    script_output_path = os.path.abspath(os.path.join(base_dir, args.script_output_file))
    
    # --- Validate Inputs --- 
    # Only need to check PDF input now
    if not os.path.exists(pdf_input_path):
        print(f"Error: Input PDF not found at {pdf_input_path}")
        sys.exit(1)

    # --- Create Output Directory ---
    os.makedirs(os.path.dirname(script_output_path), exist_ok=True)
    # The processor will handle creation of its own output/temp dirs based on hardcoded paths

    print(f"Input PDF: {pdf_input_path}")
    print(f"Output Script File: {script_output_path}")

    # --- Step 1: Generate Script --- 
    print("\nGenerating podcast script using Gemini...")
    structured_script = generate_podcast_script(pdf_input_path)

    if not structured_script:
        print("Error: Failed to generate script. Exiting.")
        sys.exit(1)

    # --- Step 2: Save Generated Script to JSON --- 
    print(f"\nSaving generated script to: {script_output_path}")
    try:
        with open(script_output_path, 'w', encoding='utf-8') as f:
            json.dump(structured_script, f, indent=4, ensure_ascii=False)
        print("Script saved successfully.")
    except IOError as e:
        print(f"Error saving script to {script_output_path}: {e}")
        sys.exit(1)

    # --- Step 3: Process Script for TTS --- 
    print("\nCalling TTS Processor...")
    try:
        # Call processor with only the script path
        process_script_for_tts(script_path=script_output_path)
        print("\nTTS processing pipeline finished.")
    except SystemExit: # Allow sys.exit calls within the processor to terminate
        print("\nTerminating due to error in TTS processing.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during TTS processing: {e}")
        sys.exit(1)

    print("\n--- Full Process Complete (Placeholders in TTS Processor) ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a podcast script from PDF, save it, and process for TTS (using placeholders and hardcoded paths).")

    parser.add_argument("pdf_file", 
                        help=f"Path to the input PDF file (e.g., {os.path.join(DEFAULT_INPUT_DIR, 'mydoc.pdf')})")
    parser.add_argument("script_output_file", 
                        help=f"Path to save the generated script JSON file (e.g., {os.path.join(DEFAULT_OUTPUT_DIR, 'podcast_script.json')})")
    # Removed arguments for speaker refs and final audio output

    parsed_args = parser.parse_args()
    main(parsed_args) 