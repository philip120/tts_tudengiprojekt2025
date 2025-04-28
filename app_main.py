import uvicorn
import os
import shutil
import sys
import io # Added for Pydub
import uuid # Added for Job IDs
from pathlib import Path # Added for easier path handling
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks # Added BackgroundTasks
from fastapi.responses import FileResponse # Added for sending files
from fastapi.middleware.cors import CORSMiddleware # <-- Import CORS Middleware

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

# --- Job Status Store (In-Memory - Simple Example) ---
# NOTE: This will be lost if the server restarts. For production, use a database or persistent store.
job_status_db = {}
# Example entry: job_id: {"status": "PROCESSING", "message": "Generating script...", "result_path": None, "error": None}

# Create the FastAPI app instance
app = FastAPI()

# --- Add CORS Middleware --- 
origins = [
    # Allow ONLY the deployed Vercel frontend
    "https://tts-tudengiprojekt2025.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, 
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
# -------------------------

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

# --- Background Task Function --- 
def process_podcast_job(job_id: str, temp_pdf_path: str, original_filename: str):
    """The actual processing logic that runs in the background."""
    print(f"[Job {job_id}] process_podcast_job function started.") 
    global job_status_db

    final_audio_path = None
    status_message = ""

    try:
        # Update status: Processing Script
        job_status_db[job_id] = {"status": "PROCESSING", "message": "Generating script...", "result_path": None, "error": None}
        print(f"[Job {job_id}] Calling script generator for: {temp_pdf_path}")
        script_result = generate_podcast_script(temp_pdf_path)
        print(f"[Job {job_id}] Script generation finished. Got {len(script_result)} segments.")

        if not script_result:
            raise ValueError("Script generation failed or returned empty script.") # Use ValueError for internal logic errors

        total_segments = len(script_result)

        # Update status: Submitting TTS
        job_status_db[job_id]["message"] = f"Submitting {total_segments} TTS jobs..."
        print(f"\n[Job {job_id}] --- Submitting TTS Jobs ---")
        job_ids_tts = []
        for i, segment in enumerate(script_result):
            text = segment.get("text")
            speaker_code = segment.get("speaker")
            speaker_filename = SPEAKER_MAP.get(speaker_code)

            if text and speaker_filename:
                print(f"[Job {job_id}] Submitting segment {i+1}/{total_segments} (Speaker: {speaker_code} -> {speaker_filename})...")
                tts_job_id = submit_tts_job(text=text, speaker_filename=speaker_filename)
                job_ids_tts.append(tts_job_id)
            else:
                print(f"[Job {job_id}] Warning: Skipping segment {i+1} due to missing text or unknown speaker code '{speaker_code}'.")
                job_ids_tts.append(None)

        # Update status: Retrieving TTS
        print(f"\n[Job {job_id}] --- Retrieving TTS Results ---")
        audio_results = []
        success_count = 0
        failure_count = 0
        for i, tts_job_id in enumerate(job_ids_tts):
            # Update progress message
            job_status_db[job_id]["message"] = f"Generating audio segment {i+1}/{total_segments}..."
            if tts_job_id:
                print(f"[Job {job_id}] Polling result for segment {i+1}/{total_segments} (Job ID: {tts_job_id})...")
                result_bytes = get_tts_job_result(tts_job_id)
                audio_results.append(result_bytes)
                if result_bytes:
                    success_count += 1
                else:
                    failure_count += 1
            else:
                print(f"[Job {job_id}] Skipping result retrieval for segment {i+1} (submission failed or skipped).")
                audio_results.append(None)
                failure_count += 1

        status_message = f"Synthesized: {success_count} segments, Failed/Skipped: {failure_count} segments."
        print(f"\n[Job {job_id}] --- TTS Processing Summary ---")
        print(status_message)

        if success_count == 0:
            raise ValueError("TTS generation failed for all segments.")

        # Update status: Combining Audio
        job_status_db[job_id]["message"] = "Combining audio segments..."
        print(f"\n[Job {job_id}] --- Combining Audio Segments ---")
        input_filename_stem = Path(original_filename).stem
        output_filename = f"{input_filename_stem}_podcast.wav"
        final_audio_path = os.path.join(FINAL_AUDIO_DIR, output_filename)

        if not combine_audio_segments(audio_results, final_audio_path, intro_audio_path=INTRO_AUDIO_PATH):
            raise ValueError(f"Audio combination failed. Segments synthesized: {success_count}")

        # Update status: Completed
        job_status_db[job_id]["status"] = "COMPLETED"
        job_status_db[job_id]["message"] = f"Podcast generated successfully! Combined {success_count} segments (intro added)."
        job_status_db[job_id]["result_path"] = final_audio_path
        print(f"[Job {job_id}] Processing COMPLETED. Result: {final_audio_path}")

    except Exception as e:
        # Update status: Failed
        error_message = f"Processing failed: {e}"
        print(f"[Job {job_id}] Error during background processing: {error_message}")
        job_status_db[job_id]["status"] = "FAILED"
        job_status_db[job_id]["message"] = status_message # Keep last known status message
        job_status_db[job_id]["error"] = error_message
        # Attempt to clean up potentially incomplete final audio
        if final_audio_path and os.path.exists(final_audio_path):
            try: os.remove(final_audio_path)
            except: pass

    finally:
        # Clean up the temporary uploaded PDF file when done
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                print(f"[Job {job_id}] Cleaned up temporary PDF: {temp_pdf_path}")
            except OSError as rm_err:
                 print(f"[Job {job_id}] Error cleaning up temp PDF {temp_pdf_path}: {rm_err}")

# Simple root endpoint for testing
@app.get("/")
def read_root():
    return {"message": "XTTS Backend is running!"}

# --- NEW: Async Endpoint to Start Job ---
@app.post("/generate-podcast-async/", status_code=202) # Return 202 Accepted
async def start_podcast_generation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="The PDF file to process")
):
    """Accepts PDF, starts background processing, returns job ID."""
    # Basic validation (can add more checks)
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are accepted.")
    if not generate_podcast_script or not submit_tts_job or not get_tts_job_result or not AudioSegment:
         raise HTTPException(status_code=500, detail="Required processing modules not loaded correctly.")
    if not RUNPOD_API_KEY:
         raise HTTPException(status_code=500, detail="RUNPOD_API_KEY is not configured.")

    job_id = str(uuid.uuid4())
    print(f"Received new job request: {job_id}")

    # --- Save temporary file with unique name --- 
    # Include job_id in temp filename to prevent clashes
    # Use original filename stem for the final output later
    temp_filename = f"{job_id}_{Path(file.filename).name}"
    temp_file_path = os.path.join(TEMP_UPLOAD_DIR, temp_filename)
    
    try:
        print(f"[Job {job_id}] Saving uploaded file to: {temp_file_path}")
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[Job {job_id}] File saved successfully.")
    except Exception as e:
        print(f"[Job {job_id}] Failed to save temporary file: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
    finally:
        await file.close()
    # -----------------------------------------------

    # Initialize job status
    job_status_db[job_id] = {"status": "PENDING", "message": "Job accepted, waiting to start...", "result_path": None, "error": None}

    # Add the long-running task to the background
    background_tasks.add_task(process_podcast_job, job_id, temp_file_path, file.filename) # Pass original filename too
    print(f"[Job {job_id}] Task added to background queue.")

    # Return the job ID immediately
    return {"message": "Podcast generation started.", "job_id": job_id}

# --- NEW: Endpoint to Check Job Status ---
@app.get("/job-status/{job_id}")
def get_job_status(job_id: str):
    """Returns the current status of a background job."""
    status_info = job_status_db.get(job_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    return status_info

# --- NEW: Endpoint to Download Result ---
@app.get("/download-result/{job_id}")
def download_result(job_id: str):
    """Downloads the final audio file if the job is complete."""
    status_info = job_status_db.get(job_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Job ID not found.")

    if status_info["status"] == "COMPLETED" and status_info.get("result_path"):
        result_path = status_info["result_path"]
        if os.path.exists(result_path):
            # Use FileResponse to send the file
            return FileResponse(path=result_path, filename=Path(result_path).name, media_type='audio/wav')
        else:
            raise HTTPException(status_code=404, detail="Result file not found on server.")
    elif status_info["status"] == "FAILED":
        raise HTTPException(status_code=400, detail=f"Job failed: {status_info.get('error', 'Unknown error')}")
    else:
        raise HTTPException(status_code=400, detail=f"Job is still processing (status: {status_info['status']}).")

# --- Main block to run the server (for development) ---
# if __name__ == "__main__":
#     print(f"Starting server on http://127.0.0.1:8000")
#     uvicorn.run("app_main:app", host="127.0.0.1", port=8000, reload=True) 