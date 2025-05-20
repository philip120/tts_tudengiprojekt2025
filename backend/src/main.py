# src/main.py

import sys
import os
import argparse
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.script_generator import generate_podcast_script
from src.tts_processor import process_script_for_tts 
from src.audio_combiner import combine_audio_segments 

DEFAULT_INPUT_DIR = "input/"
DEFAULT_OUTPUT_DIR = "backend/output/"

INTRO_AUDIO_PATH = os.path.join(parent_dir, "backend/reference/podcast_intro.wav")
MAIN_CONTENT_AUDIO_PATH = os.path.join(parent_dir, "backend/output/final_podcast_content.wav")

def main(args):
    print("Starting full podcast generation process...")

    base_dir = parent_dir
    pdf_input_path = os.path.abspath(os.path.join(base_dir, args.pdf_file))
    script_output_path = os.path.abspath(os.path.join(base_dir, args.script_output_file))
    final_output_path = os.path.abspath(os.path.join(base_dir, args.final_output_with_intro))
    
    if not os.path.exists(pdf_input_path):
        print(f"Error: Input PDF not found at {pdf_input_path}")
        sys.exit(1)
    if not os.path.exists(INTRO_AUDIO_PATH):
        print(f"Error: Pre-generated intro not found at {INTRO_AUDIO_PATH}")
        print("Please run src/generate_intro.py first.")
        sys.exit(1)

    os.makedirs(os.path.dirname(script_output_path), exist_ok=True)
    os.makedirs(os.path.dirname(final_output_path), exist_ok=True)

    print(f"Input PDF: {pdf_input_path}")
    print(f"Output Script File: {script_output_path}")
    print(f"Using Intro Audio: {INTRO_AUDIO_PATH}")
    print(f"Final Output (with Intro): {final_output_path}")

    print("\nGenerating podcast script using Gemini...")
    structured_script = generate_podcast_script(pdf_input_path)
    if not structured_script: print("Error: Failed to generate script. Exiting."); sys.exit(1)

    print(f"\nSaving generated script to: {script_output_path}")
    try:
        with open(script_output_path, 'w', encoding='utf-8') as f:
            json.dump(structured_script, f, indent=4, ensure_ascii=False)
        print("Script saved successfully.")
    except IOError as e: print(f"Error saving script to {script_output_path}: {e}"); sys.exit(1)

    print("\nCalling TTS Processor to generate main content...")
    main_content_output_file = None 
    try:
        main_content_output_file = process_script_for_tts(script_path=script_output_path)
        if main_content_output_file:
             print(f"\nTTS processing for main content finished successfully.")
             print(f"Main content audio saved to: {main_content_output_file}")
        else:
             print("\nError: TTS processing failed to return a valid output path. Exiting.")
             sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during TTS processing: {e}")
        sys.exit(1)

    print(f"\nCombining intro and main content into final output: {final_output_path}")
    segments_to_combine = [INTRO_AUDIO_PATH, main_content_output_file]
    try:
        combine_audio_segments(segments_to_combine, final_output_path)
        print(f"Final combined podcast saved successfully to: {final_output_path}")
    except Exception as e:
        print(f"Fatal error during final audio combination: {e}")
        sys.exit(1)

    print("\n--- Full Process Complete --- ")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a podcast with intro from PDF, save script, process TTS, and combine audio.")

    parser.add_argument("pdf_file", 
                        help=f"Path to the input PDF file (e.g., {os.path.join(DEFAULT_INPUT_DIR, 'mydoc.pdf')})")
    parser.add_argument("script_output_file", 
                        help=f"Path to save the generated script JSON file (e.g., {os.path.join(DEFAULT_OUTPUT_DIR, 'podcast_script.json')})")
    parser.add_argument("final_output_with_intro", 
                        help=f"Path for the final combined audio file including the intro (e.g., {os.path.join(DEFAULT_OUTPUT_DIR, 'podcast_with_intro.wav')})")

    parsed_args = parser.parse_args()
    main(parsed_args)