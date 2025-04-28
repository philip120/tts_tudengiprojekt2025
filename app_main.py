import uvicorn
import os
import shutil
import sys
import io # Added for Pydub
from pathlib import Path # Added for easier path handling
from fastapi import FastAPI, File, UploadFile, HTTPException

# --- Pydub Import (Requires ffmpeg installed system-wide) ---
try:
    from pydub import AudioSegment
except ImportError:
    print("Error: Pydub not found. Audio combination will fail.")
    print("Install it: pip install pydub")
    print("Ensure ffmpeg is also installed (e.g., sudo apt install ffmpeg or conda install ffmpeg).")
    AudioSegment = None # Placeholder

# --- Add src directory to Python path ---
# This allows importing modules from the src folder
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# --- Import from src ---
try:
    from script_generator import generate_podcast_script
    # Import Runpod orchestrator functions
    from runpod_orchestrator import submit_tts_job, get_tts_job_result, RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID
except ImportError as e:
    print(f"Error importing from src: {e}")
    print(f"Ensure src directory and runpod_orchestrator.py exist.")
    generate_podcast_script = None
    submit_tts_job = None
    get_tts_job_result = None
    RUNPOD_API_KEY = None
    RUNPOD_ENDPOINT_ID = None

# --- Constants ---
TEMP_UPLOAD_DIR = "temp_uploads"
FINAL_AUDIO_DIR = "final_audio"
INTRO_AUDIO_PATH = "output/podcast_intro.wav" # Added path for intro audio

# --- Configuration ---
# Check if necessary Runpod config is loaded
if not RUNPOD_API_KEY:
    print("Warning: RUNPOD_API_KEY environment variable not set. Runpod calls will fail.")
if not RUNPOD_ENDPOINT_ID:
    print("Warning: RUNPOD_ENDPOINT_ID environment variable not set or defaulted. Using default.")

# === SPEAKER MAPPING (IMPORTANT: ADJUST FILENAMES) ===
# Map speaker codes from Gemini script ('A', 'B') to the actual
# speaker reference .wav filenames inside your Runpod worker's samples/ directory.
SPEAKER_MAP = {
    "A": "philip.wav",  # REMOVED prefix - Replace if needed
    "B": "oskar.wav",   # REMOVED prefix - Replace if needed
    # Add more mappings if your script uses other speakers (e.g., "K": "katriin.wav")
}
# =====================================================

# Create the FastAPI app instance
app = FastAPI()

# --- Ensure directories exist ---
if not os.path.exists(TEMP_UPLOAD_DIR):
    os.makedirs(TEMP_UPLOAD_DIR)
if not os.path.exists(FINAL_AUDIO_DIR):
    os.makedirs(FINAL_AUDIO_DIR)

# --- Helper Function: Combine Audio --- (Modified for Intro)
def combine_audio_segments(
    audio_bytes_list: list[bytes | None],
    output_path: str,
    intro_audio_path: str | None = None # Added intro path parameter
) -> bool:
    """Combines a list of WAV audio bytes into a single WAV file, optionally prepending an intro."""
    if not AudioSegment:
        print("Error: Cannot combine audio, Pydub not available.")
        return False

    combined = AudioSegment.empty()

    # --- Load Intro Audio --- 
    if intro_audio_path:
        if os.path.exists(intro_audio_path):
            try:
                intro = AudioSegment.from_file(intro_audio_path)
                combined += intro
                print(f"Successfully loaded and added intro: {intro_audio_path}")
            except Exception as e:
                print(f"Warning: Failed to load intro audio from {intro_audio_path}: {e}. Proceeding without intro.")
        else:
            print(f"Warning: Intro audio file not found at {intro_audio_path}. Proceeding without intro.")
    # ---------------------------

    loaded_segment_count = 0
    for i, audio_bytes in enumerate(audio_bytes_list):
        if audio_bytes:
            try:
                segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
                combined += segment
                loaded_segment_count += 1
                print(f"Combined segment {i+1}")
            except Exception as e:
                print(f"Error loading audio segment {i+1} with pydub: {e}. Skipping.")
        else:
            print(f"Skipping segment {i+1} as it has no audio data.")

    # Only export if we have *something* (either intro or segments)
    if len(combined) > 0:
        try:
            combined.export(output_path, format="wav")
            print(f"Final combined audio saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error exporting combined audio to {output_path}: {e}")
            return False
    else:
        print("Error: No intro or valid audio segments were loaded to combine.")
        return False

# Simple root endpoint for testing
@app.get("/")
def read_root():
    return {"message": "XTTS Backend is running!"}

# --- Modified Endpoint: Upload -> Script -> TTS -> Combine (Sync) ---
@app.post("/generate-podcast-sync/")
async def upload_script_tts_combine_sync(file: UploadFile = File(..., description="The PDF file to process")):
    """Accepts PDF, saves it, generates script, generates audio via Runpod, combines audio, and returns final path."""
    if not generate_podcast_script or not submit_tts_job or not get_tts_job_result:
         raise HTTPException(status_code=500, detail="Required processing modules not loaded correctly.")
    if not AudioSegment:
        raise HTTPException(status_code=500, detail="Audio processing library (Pydub/ffmpeg) not available.")
    if not RUNPOD_API_KEY:
         raise HTTPException(status_code=500, detail="RUNPOD_API_KEY is not configured.")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are accepted.")

    temp_file_path = os.path.join(TEMP_UPLOAD_DIR, file.filename)
    script_result = []
    job_ids = []
    audio_results = []
    success_count = 0
    failure_count = 0
    final_audio_path = None # Initialize final path

    try:
        # 1. Save Uploaded File
        print(f"Saving uploaded file to: {temp_file_path}")
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File saved successfully.")

        # 2. Call Script Generator
        print(f"Calling script generator for: {temp_file_path}")
        script_result = generate_podcast_script(temp_file_path)
        print(f"Script generation finished. Got {len(script_result)} segments.")

        if not script_result:
             raise HTTPException(status_code=500, detail="Script generation failed or returned empty script.")

        # 3. Submit TTS Jobs to Runpod
        print("\n--- Submitting TTS Jobs ---")
        for i, segment in enumerate(script_result):
            text = segment.get("text")
            speaker_code = segment.get("speaker")
            speaker_filename = SPEAKER_MAP.get(speaker_code)

            if text and speaker_filename:
                print(f"Submitting segment {i+1}/{len(script_result)} (Speaker: {speaker_code} -> {speaker_filename})...")
                job_id = submit_tts_job(text=text, speaker_filename=speaker_filename)
                job_ids.append(job_id) # Store job_id or None if submission failed
            else:
                print(f"Warning: Skipping segment {i+1} due to missing text or unknown speaker code '{speaker_code}'.")
                job_ids.append(None)

        # 4. Poll for TTS Results (Synchronously for now)
        print("\n--- Retrieving TTS Results ---")
        for i, job_id in enumerate(job_ids):
            if job_id:
                print(f"Polling result for segment {i+1}/{len(job_ids)} (Job ID: {job_id})...")
                result_bytes = get_tts_job_result(job_id)
                audio_results.append(result_bytes) # Appends bytes or None
                if result_bytes:
                    success_count += 1
                else:
                    failure_count += 1
            else:
                print(f"Skipping result retrieval for segment {i+1} (submission failed or skipped).")
                audio_results.append(None)
                failure_count += 1 # Count skipped as failure for this step

        print(f"\n--- TTS Processing Summary ---")
        print(f"Successfully synthesized: {success_count} segments")
        print(f"Failed/Skipped:         {failure_count} segments")

        if success_count == 0:
            raise HTTPException(status_code=500, detail="TTS generation failed for all segments.")

        # 5. Combine Audio Segments (Now passing intro path)
        print("\n--- Combining Audio Segments ---")
        input_filename_stem = Path(file.filename).stem
        output_filename = f"{input_filename_stem}_podcast.wav"
        final_audio_path = os.path.join(FINAL_AUDIO_DIR, output_filename)

        # Pass the INTRO_AUDIO_PATH constant here
        if not combine_audio_segments(audio_results, final_audio_path, intro_audio_path=INTRO_AUDIO_PATH):
            raise HTTPException(status_code=500, detail=f"Audio combination failed. See server logs. Segments synthesized: {success_count}")

    except HTTPException: # Re-raise HTTP exceptions
        # Clean up PDF if needed
        if os.path.exists(temp_file_path):
             try: os.remove(temp_file_path) 
             except: pass # Ignore cleanup errors
        # Don't delete partially combined audio if combination failed before this point
        raise
    except Exception as e:
        # Clean up on general failure
        print(f"Error during processing: {e}")
        if os.path.exists(temp_file_path):
            try: os.remove(temp_file_path)
            except: pass
        # Attempt to clean up potentially incomplete final audio
        if final_audio_path and os.path.exists(final_audio_path):
            try: os.remove(final_audio_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
    finally:
        # Clean up the temporary uploaded PDF file on success or handled failure
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                print(f"Cleaned up temporary PDF: {temp_file_path}")
            except OSError as rm_err:
                 print(f"Error cleaning up temp PDF {temp_file_path}: {rm_err}")
        await file.close()

    # Return success with the path to the final audio file
    return {
        "message": f"Podcast generated successfully! Combined {success_count} audio segments (intro added).",
        "final_audio_path": final_audio_path,
        "succeeded_segments": success_count,
        "failed_or_skipped_segments": failure_count
    }

# --- Main block to run the server (for development) ---
# if __name__ == "__main__":
#     print(f"Starting server on http://127.0.0.1:8000")
#     uvicorn.run("app_main:app", host="127.0.0.1", port=8000, reload=True) 