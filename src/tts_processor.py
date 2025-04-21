# src/tts_processor.py

import json
import os
import sys
import re # For sentence splitting

# Import the TTS Engine
from src.tts_engine import TTSEngine 
# Import the Audio Combiner
from src.audio_combiner import combine_audio_segments

# --- Configuration ---
# Estimate max characters based on the TTS library warning.
# Needs testing with the actual TTS model, but 250 seems to be the hard limit.
MAX_CHARS_PER_TTS_CHUNK = 240 # Reduced from 750 to be below the library's 250 limit
DEFAULT_TEMP_AUDIO_DIR = "temp_audio/"
# Define model path for TTS Engine initialization
# This path should be relative to the project root where main.py is typically run
DEFAULT_TTS_MODEL_PATH = "model/XTTS-v2" # Changed back from ../model/XTTS-v2

# --- Hardcoded Paths ---
# Define paths relative to the project root (parent of src)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEAKER_A_REF_PATH = os.path.join(PROJECT_ROOT, "reference/recording.wav") # Adjust if your default name is different
SPEAKER_B_REF_PATH = os.path.join(PROJECT_ROOT, "reference/0022.wav") # Adjust if your default name is different
FINAL_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/final_podcast.wav") # Adjust if your default name is different

# --- Helper: Sentence Splitter ---
# Basic sentence splitting based on common punctuation.
# More sophisticated libraries like nltk or spacy could be used for better accuracy.
def split_into_sentences(text):
    # Use regex to split by '.', '!', '?' followed by space or end of string
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Filter out any empty strings that might result from splitting
    return [s.strip() for s in sentences if s.strip()]

# --- Helper: Chunk Text ---
def chunk_text(text, max_chars):
    """Splits text into chunks under max_chars, trying to respect sentence boundaries."""
    chunks = []
    current_chunk = ""
    sentences = split_into_sentences(text)

    if not sentences:
        # Handle case where the input text has no sentences or splitting failed
        if len(text) <= max_chars:
             if text.strip(): # Avoid adding empty chunks
                return [text.strip()]
        else:
            # Force split if it's too long and has no sentences
            # This might cut words, which is bad for TTS, but it's a fallback.
            print(f"Warning: Force-splitting long text without sentence breaks: '{text[:50]}...'")
            for i in range(0, len(text), max_chars):
                chunks.append(text[i:i+max_chars].strip())
            return chunks

    for sentence in sentences:
        # Check if adding the next sentence exceeds the limit
        if current_chunk and len(current_chunk) + len(sentence) + 1 > max_chars: # +1 for space
            # Finish the current chunk
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        elif len(sentence) > max_chars:
             # If a single sentence is already too long, handle it.
             # First, add the previous chunk if it exists
             if current_chunk:
                 chunks.append(current_chunk.strip())
                 current_chunk = ""
             # Split the long sentence itself (this is suboptimal, might cut mid-word)
             print(f"Warning: Splitting a single sentence longer than {max_chars} chars: '{sentence[:50]}...'")
             for i in range(0, len(sentence), max_chars):
                 chunks.append(sentence[i:i+max_chars].strip())
        else:
            # Add sentence to the current chunk
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    # Add the last remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    # Filter out any potential empty chunks again after processing
    return [c for c in chunks if c]


# --- Main Processing Function ---
def process_script_for_tts(script_path: str):
    """
    Loads a JSON script, processes it segment by segment for TTS (handling chunking),
    using hardcoded paths for speaker references and final output.
    Initializes TTSEngine and calls synthesize_segment.
    Calls placeholder combiner function.

    Args:
        script_path: Path to the generated JSON script file.
    """
    print(f"\n--- Starting TTS Processing --- ")
    print(f"Loading script from: {script_path}")
    print(f"Using Speaker A Ref: {SPEAKER_A_REF_PATH}")
    print(f"Using Speaker B Ref: {SPEAKER_B_REF_PATH}")
    print(f"Using Final Output Path: {FINAL_OUTPUT_PATH}")

    # --- Validate Hardcoded Input Files ---
    if not os.path.exists(SPEAKER_A_REF_PATH):
        print(f"Error: Speaker A reference file not found at hardcoded path: {SPEAKER_A_REF_PATH}")
        sys.exit(1)
    if not os.path.exists(SPEAKER_B_REF_PATH):
        print(f"Error: Speaker B reference file not found at hardcoded path: {SPEAKER_B_REF_PATH}")
        sys.exit(1)

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            structured_script = json.load(f)
    except FileNotFoundError:
        print(f"Error: Script file not found at {script_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON script file {script_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred loading the script: {e}")
        sys.exit(1)

    if not isinstance(structured_script, list):
        print(f"Error: Script file {script_path} does not contain a valid list structure.")
        sys.exit(1)

    # --- Prepare for TTS --- 
    # Get base directory for placing temp files relative to the final output
    base_output_dir = os.path.dirname(FINAL_OUTPUT_PATH)
    temp_audio_dir = os.path.join(base_output_dir, os.path.basename(DEFAULT_TEMP_AUDIO_DIR))
    os.makedirs(temp_audio_dir, exist_ok=True)
    print(f"Temporary audio will be stored in: {temp_audio_dir}")

    all_segment_paths = [] # List to hold paths of ALL generated audio chunks
    segment_counter = 0

    # --- Initialize TTS Engine --- 
    print("\nInitializing TTS Engine...")
    try:
        # Consider making use_cuda configurable if needed
        tts_engine = TTSEngine(model_path=DEFAULT_TTS_MODEL_PATH)
        if not tts_engine.model: # Check if initialization failed within the class
            print("Error: TTSEngine initialization failed. Exiting.")
            sys.exit(1)
    except Exception as e:
        print(f"Fatal error initializing TTSEngine: {e}")
        sys.exit(1)

    # --- Initialize Audio Combiner (Placeholder) ---
    # combiner_function = combine_audio_segments # From audio_combiner.py
    combiner_function = None # Replace later

    # --- Process Each Segment --- 
    print("\nProcessing script segments for TTS...")
    for i, segment in enumerate(structured_script):
        speaker = segment.get('speaker')
        text = segment.get('text')

        if not speaker or not text:
            print(f"Warning: Skipping segment {i+1} due to missing speaker or text.")
            continue

        print(f"\nSegment {i+1}: Speaker {speaker}")
        # Use hardcoded paths
        speaker_ref = SPEAKER_A_REF_PATH if speaker == 'A' else SPEAKER_B_REF_PATH

        # --- Chunk the text for TTS --- 
        text_chunks = chunk_text(text, MAX_CHARS_PER_TTS_CHUNK)
        print(f"  Split into {len(text_chunks)} chunk(s) for TTS:")
        for j, chunk in enumerate(text_chunks):
            print(f"    Chunk {j+1}: '{chunk[:60]}...' ({len(chunk)} chars)")

            # Define unique output path for this chunk
            chunk_filename = f"segment_{segment_counter:04d}_spk{speaker}_chunk{j+1}.wav"
            chunk_output_path = os.path.join(temp_audio_dir, chunk_filename)

            # --- Synthesize Audio Chunk --- 
            print(f"    Synthesizing audio for chunk {j+1}... -> {chunk_output_path}")
            try:
                # Use the actual TTS engine
                tts_engine.synthesize_segment(
                    text=chunk, 
                    speaker_wav=speaker_ref, 
                    output_path=chunk_output_path
                )
                # Only add path if synthesis was successful
                all_segment_paths.append(chunk_output_path)
            except Exception as e:
                print(f"    Error synthesizing chunk {j+1} for segment {i+1}: {e}")
                # Decide how to handle errors: skip chunk, stop process? 
                # For now, just print and continue to next chunk/segment
                pass
            
            segment_counter += 1 # Increment global counter

    # --- Combine Audio Segments --- 
    if not all_segment_paths:
        print("\nError: No audio segments were generated successfully. Cannot combine.")
        sys.exit(1)

    print(f"\nCombining {len(all_segment_paths)} audio chunks into final output... -> {FINAL_OUTPUT_PATH}")
    try:
        # Use the actual combiner function
        combine_audio_segments(all_segment_paths, FINAL_OUTPUT_PATH)
        # The function prints success/failure messages internally
    except Exception as e:
        # combine_audio_segments might raise an exception on export failure
        print(f"Fatal error combining audio segments: {e}"); 
        sys.exit(1) # Exit if combination fails

    # --- Cleanup (Optional - Placeholder) ---
    # print("\nTemporary audio cleanup (Placeholder)...")
    # Consider uncommenting cleanup logic if desired
    print(f"Attempting cleanup in: {temp_audio_dir}")
    cleanup_count = 0
    error_count = 0
    for path in all_segment_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                # print(f"  Removed: {os.path.basename(path)}") # Optional: uncomment for verbose cleanup
                cleanup_count += 1
        except OSError as e:
            print(f"  Warning: Error removing {os.path.basename(path)}: {e}")
            error_count += 1
    print(f"Cleanup attempted: {cleanup_count} files removed, {error_count} errors.")
    # Optionally remove the temp directory if it's now empty
    try:
        if os.path.exists(temp_audio_dir) and not os.listdir(temp_audio_dir):
            os.rmdir(temp_audio_dir)
            print(f"Removed empty temporary directory: {temp_audio_dir}")
    except OSError as e:
        print(f"Warning: Could not remove temporary directory {temp_audio_dir}: {e}")

    print("\n--- TTS Processing and Combination Finished --- ")

# --- Simple Test --- 
# (Keep the test block as is, it will now use the hardcoded paths and the real TTSEngine)
# Removing the test block as requested
# if __name__ == "__main__":
#     print("Running tts_processor.py standalone test...")
# 
#     # Create a dummy JSON script for testing
#     test_script_path = "test_script.json"
#     dummy_script = [
#         {"speaker": "A", "text": "Hello, this is the first sentence. This is the second sentence which is a bit longer to test basic splitting maybe perhaps even more text here."},
#         {"speaker": "B", "text": "Indeed. This is a very very long sentence designed specifically to exceed the character limit of our TTS chunker and see how it handles the forced splitting because sometimes sentences can be quite verbose and lengthy indeed going on and on. This part should definitely be in a second chunk or maybe even a third one depending on the exact limit set within the configuration constants at the top of the file just imagine more words here. And a final short sentence."},
#         {"speaker": "A", "text": "Okay, that was long. This is short."},
#         {"speaker": "B", "text": ""}, # Empty text test
#         {"speaker": "A", "text": "Final line."}
#     ]
#     try:
#         with open(test_script_path, 'w') as f:
#             json.dump(dummy_script, f, indent=4)
#         print(f"Created dummy script: {test_script_path}")
# 
#         # Ensure dummy ref/output dirs exist for the hardcoded paths
#         os.makedirs(os.path.dirname(SPEAKER_A_REF_PATH), exist_ok=True)
#         os.makedirs(os.path.dirname(SPEAKER_B_REF_PATH), exist_ok=True)
#         os.makedirs(os.path.dirname(FINAL_OUTPUT_PATH), exist_ok=True)
#         # Create dummy ref files if they don't exist
#         if not os.path.exists(SPEAKER_A_REF_PATH): open(SPEAKER_A_REF_PATH, 'a').close(); print(f"Warning: Created dummy file for {SPEAKER_A_REF_PATH}")
#         if not os.path.exists(SPEAKER_B_REF_PATH): open(SPEAKER_B_REF_PATH, 'a').close(); print(f"Warning: Created dummy file for {SPEAKER_B_REF_PATH}")
# 
#         # Call the main processing function (only needs script path)
#         process_script_for_tts(test_script_path)
# 
#         # Calculate expected temp dir based on FINAL_OUTPUT_PATH
#         expected_temp_dir = os.path.join(os.path.dirname(FINAL_OUTPUT_PATH), os.path.basename(DEFAULT_TEMP_AUDIO_DIR))
#         print(f"\nTest finished. Check '{expected_temp_dir}' for actual generated chunk files.")
#         print(f"(Note: Dummy script '{test_script_path}' was not deleted for inspection.)")
# 
#     except Exception as e:
#         print(f"An error occurred during the standalone test: {e}")
#         import traceback
#         traceback.print_exc() 