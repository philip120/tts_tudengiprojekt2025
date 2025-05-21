import uvicorn
import os
import shutil
import sys
import io 
import uuid 
from pathlib import Path 
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import redis 
import json 
import subprocess 
import tempfile 


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

try:
    from script_generator import generate_podcast_script
    from runpod_orchestrator import submit_tts_job, get_tts_job_result, RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID
except ImportError as e:
    print(f"Error importing from src: {e}")
    print(f"Ensure src directory and runpod_orchestrator.py exist.")
    generate_podcast_script = None
    submit_tts_job = None
    get_tts_job_result = None
    RUNPOD_API_KEY = None
    RUNPOD_ENDPOINT_ID = None

TEMP_UPLOAD_DIR = "temp_uploads"
FINAL_AUDIO_DIR = "final_audio"
INTRO_AUDIO_PATH = os.path.join(os.path.dirname(__file__), "reference", "podcast_intro.wav") 
SILENT_AUDIO_PATH = os.path.join(os.path.dirname(__file__), "reference", "silent_voice.wav")


if not RUNPOD_API_KEY:
    print("Warning: RUNPOD_API_KEY environment variable not set. Runpod calls will fail.")
if not RUNPOD_ENDPOINT_ID:
    print("Warning: RUNPOD_ENDPOINT_ID environment variable not set or defaulted. Using default.")


SPEAKER_MAP = {
    "A": "philip.wav", 
    "B": "oskar.wav",  
}

REDIS_URL = os.environ.get("REDIS_URL")
redis_client = None
if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True) 
        redis_client.ping()  
        print("Successfully connected to Redis.")
    except redis.exceptions.ConnectionError as e:
        print(f"Error connecting to Redis: {e}. Job status will not persist.")
        redis_client = None 
else:
    print("Warning: REDIS_URL environment variable not set. Job status will not persist across workers or restarts.")

JOB_STATUS_TTL = 86400 


app = FastAPI()

origins = [
    "https://www.tts-ut.ee",
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "https://tts-tudengiprojekt2025.vercel.app"  # Allow Vercel frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

if not os.path.exists(TEMP_UPLOAD_DIR):
    os.makedirs(TEMP_UPLOAD_DIR)
if not os.path.exists(FINAL_AUDIO_DIR):
    os.makedirs(FINAL_AUDIO_DIR)

def combine_audio_segments(
    audio_bytes_list: list[bytes | None],
    output_path: str,
    intro_audio_path: str | None = None
) -> bool:
    """Combines a list of WAV audio bytes using the ffmpeg concat filter for robustness."""
    
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

    temp_file_paths = []  
    input_files_for_ffmpeg = []  

   
    if intro_audio_path:
        abs_intro_path = os.path.abspath(intro_audio_path)
        if os.path.exists(abs_intro_path):
            input_files_for_ffmpeg.append(abs_intro_path)

    valid_segment_count = 0
    for i, audio_bytes in enumerate(audio_bytes_list):
        if audio_bytes:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
                    temp_wav.write(audio_bytes)
                    temp_file_path = temp_wav.name
                temp_file_paths.append(temp_file_path)  
                input_files_for_ffmpeg.append(temp_file_path)  
                valid_segment_count += 1
            except Exception:
                continue  

    if not input_files_for_ffmpeg:
        return False

    # Construct ffmpeg command using concat filter
    abs_output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output_path), exist_ok=True)

    ffmpeg_command = ["ffmpeg", "-y"]  

    for file_path in input_files_for_ffmpeg:
        ffmpeg_command.extend(["-i", file_path])

    filter_complex_str = ""
    for i in range(len(input_files_for_ffmpeg)):
        filter_complex_str += f"[{i}:a]" 
    filter_complex_str += f"concat=n={len(input_files_for_ffmpeg)}:v=0:a=1[outa]"  # Concatenate audio streams

    ffmpeg_command.extend(["-filter_complex", filter_complex_str])
    ffmpeg_command.extend(["-map", "[outa]"]) 

    ffmpeg_command.extend([
        "-ar", "48000",  
        "-ac", "2",      
        "-acodec", "pcm_s16le",  
        abs_output_path 
    ])

    result = subprocess.run(ffmpeg_command, capture_output=True, text=True, check=False)

    if result.returncode == 0:
        return True
    else:
        if os.path.exists(abs_output_path):
            try: os.remove(abs_output_path)
            except OSError: pass
        return False

    for temp_path in temp_file_paths:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

def set_job_status(job_id: str, status_data: dict):
    """Stores job status data in Redis as JSON."""
    if redis_client:
        try:
            status_json = json.dumps(status_data)
            redis_client.set(job_id, status_json, ex=JOB_STATUS_TTL)
            print(f"[Job {job_id}] Redis SET successful. Status: {status_data.get('status')}, Msg: {status_data.get('message')}") 
        except redis.exceptions.RedisError as e:
            print(f"[Job {job_id}] Redis Error - Failed to set status: {e}")
    else:
        print(f"[Job {job_id}] Warning: Redis client not available. Cannot save status.")

def get_job_status_from_redis(job_id: str) -> dict | None:
    """Retrieves and decodes job status data from Redis."""
    if redis_client:
        try:
            status_json = redis_client.get(job_id)
            if status_json:
                print(f"[Job {job_id}] Redis GET successful. Found status.") 
                return json.loads(status_json) 
            else:
                print(f"[Job {job_id}] Redis GET - Key not found.") 
                return None 
        except redis.exceptions.RedisError as e:
            print(f"[Job {job_id}] Redis Error - Failed to get status: {e}")
            return None 
        except json.JSONDecodeError as e:
             print(f"[Job {job_id}] Redis Error - Failed to decode status JSON: {e}. Data: {status_json}")
             return None 
    else:
        print(f"Warning: Redis client not available. Cannot get job status.")
        return None

def save_audio_segments(audio_bytes_list: list[bytes | None], debug_dir: str):
    """Saves each audio segment to a specified debug directory."""
    os.makedirs(debug_dir, exist_ok=True)  

    for i, audio_bytes in enumerate(audio_bytes_list):
        if audio_bytes:
            try:
                segment_path = os.path.join(debug_dir, f"segment_{i:02d}.wav")
                with open(segment_path, "wb") as segment_file:
                    segment_file.write(audio_bytes)
                print(f"Saved segment {i} to {segment_path}")
            except Exception as e:
                print(f"Failed to save segment {i}: {e}")

def process_podcast_job(job_id: str, temp_pdf_path: str, original_filename: str):
    """The actual processing logic that runs in the background, using Redis for status."""
    print(f"[Job {job_id}] process_podcast_job function started.")
    final_audio_path = None
    status_message = "" 
    current_status = {} 

    try:
        current_status = {"status": "PROCESSING", "message": "Generating script...", "result_path": None, "error": None}
        set_job_status(job_id, current_status)
        print(f"[Job {job_id}] Calling script generator for: {temp_pdf_path}")
        script_result = generate_podcast_script(temp_pdf_path)
        print(f"[Job {job_id}] Script generation finished. Got {len(script_result)} segments.")

        if not script_result:
            raise ValueError("Script generation failed or returned empty script.")

        total_segments = len(script_result)

        current_status["message"] = f"Submitting {total_segments} TTS jobs..."
        set_job_status(job_id, current_status)
        print(f"\n[Job {job_id}] --- Submitting TTS Jobs ---")
        job_ids_tts = []
        for i, segment in enumerate(script_result):
            text = segment.get("text")
            speaker_code = segment.get("speaker")
            speaker_filename = SPEAKER_MAP.get(speaker_code)

            if text and speaker_filename:
                print(f"[Job {job_id}] Submitting segment {i+1}/{total_segments} (Speaker: {speaker_code} -> {speaker_filename})..." )
                tts_job_id = submit_tts_job(text=text, speaker_filename=speaker_filename)
                job_ids_tts.append(tts_job_id)
            else:
                print(f"[Job {job_id}] Warning: Skipping segment {i+1} due to missing text or unknown speaker code '{speaker_code}'.")
                job_ids_tts.append(None)

        print(f"\n[Job {job_id}] --- Retrieving TTS Results ---")
        audio_results = []
        success_count = 0
        failure_count = 0
        for i, tts_job_id in enumerate(job_ids_tts):
            current_status["message"] = f"Generating audio segment {i+1}/{total_segments}..."
            set_job_status(job_id, current_status)
            if tts_job_id:
                print(f"[Job {job_id}] Polling result for segment {i+1}/{total_segments} (Job ID: {tts_job_id})..." )
                result_bytes = get_tts_job_result(tts_job_id)
                audio_results.append(result_bytes)
                if result_bytes:
                    success_count += 1
                else:
                    failure_count += 1
            else:
                print(f"[Job {job_id}] Skipping result retrieval for segment {i+1} (submission failed or skipped)." )
                audio_results.append(None)
                failure_count += 1

        status_message = f"Synthesized: {success_count} segments, Failed/Skipped: {failure_count} segments."
        print(f"\n[Job {job_id}] --- TTS Processing Summary ---")
        print(status_message)

        if success_count == 0:
            raise ValueError("TTS generation failed for all segments.")

        debug_dir = os.path.join(FINAL_AUDIO_DIR, f"debug_segments_{job_id}")
        save_audio_segments(audio_results, debug_dir)

        current_status["message"] = "Combining audio segments..."
        set_job_status(job_id, current_status)
        print(f"\n[Job {job_id}] --- Combining Audio Segments ---")
        input_filename_stem = Path(original_filename).stem
        output_filename = f"{input_filename_stem}_podcast.wav"
        final_audio_path = os.path.join(FINAL_AUDIO_DIR, output_filename)

        if os.path.exists(SILENT_AUDIO_PATH):
            print(f"Adding silent audio from: {SILENT_AUDIO_PATH}")
            audio_results.insert(0, open(SILENT_AUDIO_PATH, "rb").read())

        if not combine_audio_segments(audio_results, final_audio_path, intro_audio_path=INTRO_AUDIO_PATH):
             raise ValueError(f"Audio combination failed. Segments synthesized: {success_count}")
       
        current_status["status"] = "COMPLETED"
        current_status["message"] = f"Podcast generated successfully! Combined {success_count} segments (intro added)."
        current_status["result_path"] = final_audio_path
        current_status["error"] = None
        set_job_status(job_id, current_status)
        print(f"[Job {job_id}] Processing COMPLETED. Result: {final_audio_path}")

    except Exception as e:
        error_message = f"Processing failed: {e}"
        print(f"[Job {job_id}] Error during background processing: {error_message}")
        current_status["status"] = "FAILED"
        current_status["message"] = status_message if status_message else error_message 
        current_status["error"] = error_message
        set_job_status(job_id, current_status)
        if final_audio_path and os.path.exists(final_audio_path):
            try: os.remove(final_audio_path)
            except: pass

    finally:
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                print(f"[Job {job_id}] Cleaned up temporary PDF: {temp_pdf_path}")
            except OSError as rm_err:
                 print(f"[Job {job_id}] Error cleaning up temp PDF {temp_pdf_path}: {rm_err}")

@app.get("/")
def read_root():
    return {"message": "XTTS Backend is running!"}

@app.post("/generate-podcast-async/", status_code=202)
async def start_podcast_generation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="The PDF file to process")
):
    """Accepts PDF, starts background processing, returns job ID."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are accepted.")
    if not generate_podcast_script or not submit_tts_job or not get_tts_job_result:
        raise HTTPException(status_code=500, detail="Required processing modules not loaded correctly.")
    if not RUNPOD_API_KEY:
        raise HTTPException(status_code=500, detail="RUNPOD_API_KEY is not configured.")

    job_id = str(uuid.uuid4())
    print(f"Received new job request: {job_id}")

   
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

    initial_status = {"status": "PENDING", "message": "Job accepted, waiting to start...", "result_path": None, "error": None}
    set_job_status(job_id, initial_status)

    background_tasks.add_task(process_podcast_job, job_id, temp_file_path, file.filename)
    print(f"[Job {job_id}] Task added to background queue.")

    return {"message": "Podcast generation started.", "job_id": job_id}

@app.get("/job-status/{job_id}")
def get_job_status(job_id: str):
    """Returns the current status of a background job from Redis."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Job status store (Redis) is unavailable.")
    
    status_info = get_job_status_from_redis(job_id)
    
    if not status_info:
        
        raise HTTPException(status_code=404, detail="Job ID not found or status expired.")
    return status_info

@app.get("/download-result/{job_id}")
def download_result(job_id: str):
    """Downloads the final audio file if the job is complete, checking Redis status."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Job status store (Redis) is unavailable.")

    status_info = get_job_status_from_redis(job_id)
    
    if not status_info:
        raise HTTPException(status_code=404, detail="Job ID not found or status expired.")

    if status_info["status"] == "COMPLETED" and status_info.get("result_path"):
        result_path = status_info["result_path"]
        if os.path.exists(result_path):
            return FileResponse(path=result_path, filename=Path(result_path).name, media_type='audio/wav')
        else:
            raise HTTPException(status_code=404, detail="Result file not found on server.")
    elif status_info["status"] == "FAILED":
        raise HTTPException(status_code=400, detail=f"Job failed: {status_info.get('error', 'Unknown error')}")
    else:
        raise HTTPException(status_code=400, detail=f"Job is still processing (status: {status_info['status']}).")

