# src/generate_intro.py

import os
import sys
import shutil

# Adjust path to import from src
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.tts_engine import TTSEngine
from src.audio_combiner import combine_audio_segments

# --- Configuration ---
# Paths relative to the project root
PROJECT_ROOT = parent_dir
SPEAKER_A_REF_PATH = os.path.join(PROJECT_ROOT, "reference/philip.wav") 
SPEAKER_B_REF_PATH = os.path.join(PROJECT_ROOT, "reference/oskar.wav") 
TTS_MODEL_PATH = os.path.join(PROJECT_ROOT, "model/XTTS-v2")
FINAL_INTRO_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/podcast_intro.wav")
TEMP_INTRO_AUDIO_DIR = os.path.join(PROJECT_ROOT, "output/temp_intro_audio/")

# --- Introduction Script ---
# Speaker A: Philip, Speaker B: Oskar
INTRO_SCRIPT = [
    {"speaker": "A", "text": "Hello and welcome! My name is Philip."},
    {"speaker": "B", "text": "And I'm Oskar. Welcome to our automated podcast project, created for the Tartu University student competition."},
    {"speaker": "A", "text": "That's right, Oskar. In this project, we take documents, like PDFs..."},
    {"speaker": "B", "text": "...and use AI, including large language models and voice cloning, to automatically generate a podcast discussion about the document's content."},
    {"speaker": "A", "text": "Exactly. So sit back, and let's hear what the AI came up with for today's topic."}
]

def main():
    print("--- Starting Podcast Introduction Generation ---")

    # --- Validate Inputs ---
    if not os.path.exists(SPEAKER_A_REF_PATH):
        print(f"Error: Speaker A (Philip) reference file not found: {SPEAKER_A_REF_PATH}")
        sys.exit(1)
    if not os.path.exists(SPEAKER_B_REF_PATH):
        print(f"Error: Speaker B (Oskar) reference file not found: {SPEAKER_B_REF_PATH}")
        sys.exit(1)
    if not os.path.exists(TTS_MODEL_PATH):
         print(f"Error: TTS Model not found at: {TTS_MODEL_PATH}")
         sys.exit(1)

    # --- Setup Directories ---
    os.makedirs(os.path.dirname(FINAL_INTRO_OUTPUT_PATH), exist_ok=True)
    # Clear and create temp directory for this specific run
    if os.path.exists(TEMP_INTRO_AUDIO_DIR):
        shutil.rmtree(TEMP_INTRO_AUDIO_DIR)
        print(f"Cleaned existing temp directory: {TEMP_INTRO_AUDIO_DIR}")
    os.makedirs(TEMP_INTRO_AUDIO_DIR)
    print(f"Created temporary directory: {TEMP_INTRO_AUDIO_DIR}")

    # --- Initialize TTS Engine ---
    print("\nInitializing TTS Engine...")
    try:
        tts_engine = TTSEngine(model_path=TTS_MODEL_PATH)
        if not tts_engine.model:
            print("Error: TTSEngine initialization failed. Exiting.")
            sys.exit(1)
    except Exception as e:
        print(f"Fatal error initializing TTSEngine: {e}")
        sys.exit(1)

    # --- Synthesize Intro Segments ---
    print("\nSynthesizing introduction segments...")
    intro_segment_paths = []
    for i, segment in enumerate(INTRO_SCRIPT):
        speaker = segment.get('speaker')
        text = segment.get('text')

        if not speaker or not text:
            print(f"Warning: Skipping intro segment {i+1} due to missing speaker or text.")
            continue
        
        speaker_name = "Philip" if speaker == 'A' else "Oskar"
        print(f"\nSegment {i+1}: Speaker {speaker} ({speaker_name})")
        speaker_ref = SPEAKER_A_REF_PATH if speaker == 'A' else SPEAKER_B_REF_PATH
        
        # No need for chunking as intro lines are short
        chunk_filename = f"intro_segment_{i:02d}_spk{speaker}.wav"
        chunk_output_path = os.path.join(TEMP_INTRO_AUDIO_DIR, chunk_filename)

        print(f"  Synthesizing: '{text[:60]}...' -> {chunk_output_path}")
        try:
            tts_engine.synthesize_segment(
                text=text, 
                speaker_wav=speaker_ref, 
                output_path=chunk_output_path
            )
            intro_segment_paths.append(chunk_output_path)
        except Exception as e:
            print(f"    Error synthesizing intro segment {i+1}: {e}")
            # Stop if any intro segment fails
            print("Exiting due to synthesis error.")
            sys.exit(1) 

    # --- Combine Intro Segments ---
    if not intro_segment_paths:
        print("\nError: No intro audio segments were generated. Cannot combine.")
        sys.exit(1)

    print(f"\nCombining {len(intro_segment_paths)} intro audio segments into final output... -> {FINAL_INTRO_OUTPUT_PATH}")
    try:
        combine_audio_segments(intro_segment_paths, FINAL_INTRO_OUTPUT_PATH)
    except Exception as e:
        print(f"Fatal error combining intro audio segments: {e}") 
        sys.exit(1)

    # --- Cleanup --- 
    print(f"\nCleaning up temporary directory: {TEMP_INTRO_AUDIO_DIR}")
    try:
        shutil.rmtree(TEMP_INTRO_AUDIO_DIR)
        print("Temporary directory removed.")
    except OSError as e:
        print(f"Warning: Could not remove temporary directory {TEMP_INTRO_AUDIO_DIR}: {e}")

    print(f"\n--- Podcast Introduction Generation Complete --- ")
    print(f"Output saved to: {FINAL_INTRO_OUTPUT_PATH}")

if __name__ == "__main__":
    main() 