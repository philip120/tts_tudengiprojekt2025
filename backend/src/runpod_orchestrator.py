import requests
import time
import os
import base64
import json


RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
DEFAULT_RUNPOD_ENDPOINT_ID = "lgbbthjyjvwxlo" 
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", DEFAULT_RUNPOD_ENDPOINT_ID)


TTS_RUN_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run"
TTS_STATUS_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status"
HEADERS = {
    "Content-Type": "application/json"
}
POLL_INTERVAL_S = 3  
JOB_TIMEOUT_S = 300 


def _get_auth_header():
    """Returns the auth header if API key is available."""
    if not RUNPOD_API_KEY:
        raise ValueError("RUNPOD_API_KEY environment variable not set.")
    return {"Authorization": f"Bearer {RUNPOD_API_KEY}"}

def submit_tts_job(text: str, speaker_filename: str, language: str = "en") -> str | None:
    """
    Submits a TTS job to the Runpod endpoint asynchronously.

    Args:
        text: The text to synthesize.
        speaker_filename: The filename of the speaker reference WAV (e.g., 'philip.wav').
        language: The language code (default 'en').

    Returns:
        The job ID if submission is successful, otherwise None.
    """
    try:
        auth_header = _get_auth_header()
    except ValueError as e:
        print(f"Error: {e}")
        return None

    payload = {
        "input": {
            "text": text,
            "speaker_filename": speaker_filename,
            "language": language
        }
    }
    submit_headers = {**HEADERS, **auth_header} 

    try:
        response = requests.post(TTS_RUN_URL, headers=submit_headers, json=payload)
        response.raise_for_status() 
        result = response.json()
        job_id = result.get("id")
        if job_id:
            print(f"Submitted TTS job ({speaker_filename}): {job_id}")
            return job_id
        else:
            print(f"Error: Runpod submission response missing job ID. Response: {result}")
            return None
    except requests.exceptions.RequestException as e:
        error_message = f"Error submitting job to Runpod: {e}"
        if e.response is not None:
             error_message += f" - Status: {e.response.status_code}, Response: {e.response.text}"
        print(error_message)
        return None
    except json.JSONDecodeError:
        print(f"Error decoding Runpod submission response: {response.text if 'response' in locals() else 'N/A'}")
        return None


def get_tts_job_result(job_id: str) -> bytes | None:
    """
    Polls the Runpod status endpoint for a given job ID until completion or timeout.

    Args:
        job_id: The ID of the job to poll.

    Returns:
        The decoded audio bytes if the job completes successfully, otherwise None.
    """
    if not job_id:
        return None

    try:
        auth_header = _get_auth_header()
    except ValueError as e:
        print(f"Error: {e}")
        return None

    start_time = time.time()
    status_url = f"{TTS_STATUS_URL}/{job_id}"
    status_headers = {**HEADERS, **auth_header} 

    while time.time() - start_time < JOB_TIMEOUT_S:
        try:
            response = requests.get(status_url, headers=status_headers)
            response.raise_for_status() 
            result = response.json()
            status = result.get("status")

            if status == "COMPLETED":
                print(f"Job {job_id} completed.")
                base64_audio = result.get("output", {}).get("audio_base64")
                if base64_audio:
                    try:
                        return base64.b64decode(base64_audio)
                    except (base64.binascii.Error, ValueError) as decode_err:
                        print(f"Error decoding Base64 audio for job {job_id}: {decode_err}")
                        return None
                else:
                    print(f"Error: Job {job_id} completed but no audio_base64 found in output. Response: {result}")
                    return None
            elif status == "FAILED":
                print(f"Error: Job {job_id} failed. Status response: {result}")
                return None
            elif status in ["IN_QUEUE", "IN_PROGRESS"]:
                print(f"Job {job_id} status: {status}. Waiting ({int(time.time() - start_time)}s elapsed)...")
                time.sleep(POLL_INTERVAL_S)
            else:
                 print(f"Job {job_id} encountered unexpected status: '{status}'. Waiting...")
                 time.sleep(POLL_INTERVAL_S)

        except requests.exceptions.RequestException as e:
            error_message = f"Error polling job {job_id}: {e}"
            if e.response is not None:
                 error_message += f" - Status: {e.response.status_code}, Response: {e.response.text}"
            print(error_message)
            time.sleep(POLL_INTERVAL_S * 2)
        except json.JSONDecodeError:
             print(f"Error decoding Runpod status response for {job_id}: {response.text if 'response' in locals() else 'N/A'}")
             time.sleep(POLL_INTERVAL_S * 2)

    print(f"Error: Job {job_id} timed out after {JOB_TIMEOUT_S}s.")
    return None 