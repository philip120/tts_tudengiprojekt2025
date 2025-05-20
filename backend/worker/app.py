# worker/app.py

import os
import sys
import base64
import logging
import runpod 

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir) 
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, '/app/src') 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from tts_engine import TTSEngine 
except ImportError as e:
    logger.error(f"Failed to import TTSEngine: {e}. Check PYTHONPATH and file locations.")
    sys.exit("Critical Error: Could not import TTSEngine.")


MODEL_PATH = "/app/model/XTTS-v2"
REFERENCE_DIR = "/app/reference"

tts_engine = None
try:
    logger.info(f"Initializing TTSEngine with model_path='{MODEL_PATH}' and reference_dir='{REFERENCE_DIR}'")
    tts_engine = TTSEngine(model_path=MODEL_PATH, reference_dir=REFERENCE_DIR, use_gpu=True)
    logger.info("TTSEngine initialized successfully.")
except Exception as e:
    logger.error(f"FATAL: Failed to initialize TTSEngine during app startup: {e}", exc_info=True)
    
    tts_engine = None # Ensure it's None if initialization failed

def handler(job):
    """ Handler function that will be called by Runpod serverless. """
    
    if tts_engine is None:
        logger.error("Handler called but TTSEngine is not initialized.")
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

logger.info("--- Starting Runpod serverless worker --- ")
runpod.serverless.start({"handler": handler})

if __name__ == '__main__':
    
    logger.info("--- Preparing to start Flask server ---")
    app.run(host='0.0.0.0', port=8000, debug=False) 