# worker/app.py

import os
import sys
import base64
import logging
import runpod # Import runpod library

# Add src directory to Python path to allow importing TTSEngine
# This assumes the script is run from the root of the project where 'src' is a subdirectory
# In the Docker container, the working directory is /app, and src is directly under it.
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir) # Go up one level from worker to the root
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, '/app/src') # Explicitly add /app/src for Docker environment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from tts_engine import TTSEngine # Now this should work
except ImportError as e:
    logger.error(f"Failed to import TTSEngine: {e}. Check PYTHONPATH and file locations.")
    # If the engine can't be imported, the app can't function. Exit or handle gracefully.
    sys.exit("Critical Error: Could not import TTSEngine.")

# --- Global TTSEngine Instance ---
# Instantiate the engine once when the application starts.
# This loads the model into memory.
# Paths are relative to the container's /app directory
MODEL_PATH = "/app/model/XTTS-v2"
REFERENCE_DIR = "/app/reference"

tts_engine = None
try:
    logger.info(f"Initializing TTSEngine with model_path='{MODEL_PATH}' and reference_dir='{REFERENCE_DIR}'")
    tts_engine = TTSEngine(model_path=MODEL_PATH, reference_dir=REFERENCE_DIR, use_gpu=True)
    logger.info("TTSEngine initialized successfully.")
except Exception as e:
    logger.error(f"FATAL: Failed to initialize TTSEngine during app startup: {e}", exc_info=True)
    # Depending on deployment strategy, might want to exit or prevent app from starting
    # For now, we'll let Flask start, but synthesis requests will fail.
    tts_engine = None # Ensure it's None if initialization failed

def handler(job):
    """ Handler function that will be called by Runpod serverless. """
    
    if tts_engine is None:
        logger.error("Handler called but TTSEngine is not initialized.")
        # Return an error structure that Runpod might understand
        return {"error": "TTS Engine failed to initialize. Check worker logs."}

    job_input = job.get('input', None)

    if job_input is None:
        return {"error": "Missing 'input' key in job payload"}

    text = job_input.get('text')
    speaker_filename = job_input.get('speaker_filename')
    language = job_input.get('language', 'en')

    logger.info(f"Received job: {job['id']}")

    if not text or not speaker_filename:
        logger.warning(f"Missing 'text' or 'speaker_filename' in job input: {job_input}")
        return {"error": "Missing 'text' or 'speaker_filename' in job input"}

    logger.info(f"Processing synthesis request: speaker='{speaker_filename}', lang='{language}', text='{text[:50]}...'")

    try:
        wav_bytes = tts_engine.synthesize(text, speaker_filename, language=language)
        audio_base64 = base64.b64encode(wav_bytes).decode('utf-8')
        logger.info(f"Synthesis successful for job '{job['id']}'. Returning base64 audio.")
        # Return the result dictionary directly
        return {"audio_base64": audio_base64}

    except FileNotFoundError as e:
        logger.error(f"Speaker file not found for job '{job['id']}': {e}")
        return {"error": f"Speaker file '{speaker_filename}' not found.", "details": str(e)}
    
    except ValueError as e:
        logger.error(f"Value error during synthesis for job '{job['id']}': {e}")
        return {"error": "Synthesis failed.", "details": str(e)}

    except Exception as e:
        logger.error(f"Unexpected error during synthesis for job '{job['id']}': {e}", exc_info=True)
        return {"error": "An unexpected error occurred during synthesis.", "details": str(e)}

# Start the Runpod serverless worker
logger.info("--- Starting Runpod serverless worker --- ")
runpod.serverless.start({"handler": handler})

if __name__ == '__main__':
    # Use 0.0.0.0 to be accessible externally (within the container network)
    # Port 8000 is exposed in the Dockerfile
    # Turn off debug mode for production/deployment
    logger.info("--- Preparing to start Flask server ---")
    app.run(host='0.0.0.0', port=8000, debug=False) 