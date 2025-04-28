# src/tts_engine.py

import os
import torch
from TTS.tts.models.xtts import Xtts, XttsAudioConfig
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.config.shared_configs import BaseDatasetConfig
from TTS.utils.audio import AudioProcessor
# Need safe_globals for loading checkpoints containing non-weight data (like XttsConfig)
from torch.serialization import safe_globals 
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Default model path (can be overridden in constructor)
DEFAULT_MODEL_PATH = "../model/XTTS-v2" 
# Determine if CUDA is available and desired
USE_CUDA = torch.cuda.is_available()
# USE_CUDA = False # Uncomment to force CPU (e.g., for low VRAM)

class TTSEngine:
    """A class to handle XTTS model loading and synthesis."""

    def __init__(self, model_path="model/XTTS-v2", reference_dir="reference", use_gpu=True):
        logger.info("Initializing TTSEngine...")
        self.model_path = model_path
        self.reference_dir = reference_dir
        self.config = self._load_config()
        self.model = self._load_model()
        
        logger.info("--- About to initialize AudioProcessor ---")
        try:
            self.processor = AudioProcessor.init_from_config(self.config)
            logger.info("--- AudioProcessor initialized successfully ---")
        except Exception as ap_e:
             logger.error(f"FATAL: Failed during AudioProcessor initialization: {ap_e}", exc_info=True)
             raise # Re-raise the error to make sure it stops the script visibly

        if use_gpu and torch.cuda.is_available():
            logger.info("CUDA is available. Attempting to move model to GPU...")
            try:
                self.model.cuda()
                self.device = "cuda"
                logger.info("Model successfully moved to GPU.")
            except Exception as e:
                logger.error(f"FATAL: Failed to move model to GPU: {e}", exc_info=True)
                # Decide how to handle: re-raise, or fall back to CPU?
                # For now, let's try falling back to CPU if GPU fails.
                logger.warning("Falling back to CPU due to GPU error.")
                self.device = "cpu"
                # Ensure model is on CPU if cuda() failed partially (unlikely but possible)
                try:
                    self.model.cpu()
                except Exception as cpu_e:
                    logger.error(f"Error moving model back to CPU after GPU failure: {cpu_e}")
                    # If this fails, the engine state is uncertain, maybe raise?
                    raise RuntimeError(f"Failed to initialize model on any device after GPU failure: {e}") from e 
        else:
            if use_gpu:
                logger.warning("CUDA requested but not available. Using CPU.")
            else:
                logger.info("Using CPU.")
            self.device = "cpu"
        logger.info(f"TTSEngine initialized on device: {self.device}")

    def _load_config(self):
        """Loads the XTTS configuration file."""
        config_path = os.path.join(self.model_path, "config.json")
        logger.info(f"Loading config from: {config_path}")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at {config_path}")
        
        print("Loading configuration...")
        config = XttsConfig()
        config.load_json(config_path)

        # --- Apply necessary overrides ---
        # These might be needed if the checkpoint expects different settings
        # than the default config provides, or if you want specific audio quality.
        # Based on the original xtts.py:
        print("Applying audio configuration overrides...")
        config.audio = {
            "sample_rate": 24000,
            "output_sample_rate": 24000, # Important: Ensure output matches model
            "frame_length_ms": 40,
            "frame_shift_ms": 10,
            "n_fft": 1024,
            "num_mels": 80,
            "mel_fmin": 0,
            "mel_fmax": 12000 
        }
        # These seem specific to the checkpoint used in xtts.py
        print("Applying model argument overrides (mel/text positions)...")
        config.model_args.num_mel_positions = 608 
        config.model_args.num_text_positions = 404 

        return config

    def _load_model(self):
        """Initializes and loads the XTTS model checkpoint."""
        if not self.config:
            raise ValueError("Configuration must be loaded before loading the model.")

        logger.info("Loading model checkpoint...")
        # Use safe_globals context manager to allow loading XttsConfig
        with safe_globals([XttsConfig]):
             model = Xtts.init_from_config(self.config)
             model.load_checkpoint(
                 self.config,
                 checkpoint_path=os.path.join(self.model_path, "model.pth"),
                 checkpoint_dir=self.model_path, # Pass the directory containing model.pth
                 vocab_path=os.path.join(self.model_path, "vocab.json"),
                 use_deepspeed=False
             )
        logger.info("Model loaded successfully.")
        return model

    def synthesize(self, text, speaker_filename, language="en"):
        speaker_wav_path = os.path.join(self.reference_dir, speaker_filename)

        if not os.path.exists(speaker_wav_path):
            logger.error(f"Reference speaker WAV not found: {speaker_wav_path}")
            raise FileNotFoundError(f"Reference speaker WAV not found: {speaker_wav_path}")

        logger.info(f"Synthesizing text: '{text[:50]}...' using speaker: {speaker_filename}")
        try:
            # Ensure the model is in evaluation mode
            self.model.eval()
            
            # Perform inference
            with torch.no_grad(): # Important for inference
                outputs = self.model.synthesize(
                    text=text,
                    config=self.config,
                    speaker_wav=[speaker_wav_path], # Must be a list
                    language=language,
                    # Add any other specific XTTS parameters here if needed
                    # gpt_cond_len=gpt_cond_len, 
                    # temperature=temperature,
                    # ...
                )
            
            # The output['wav'] is likely a numpy array or tensor on the correct device
            wav_data = outputs.get("wav") 
            if wav_data is None:
                 logger.error("Synthesis failed: 'wav' key not found in model output.")
                 raise ValueError("Synthesis failed: Model did not return 'wav' data.")

            logger.info("Synthesis successful.")
            
            # Convert tensor/array to WAV bytes using the AudioProcessor
            # Note: save_wav normally writes to file, we need the bytes
            # We can use a BytesIO buffer for this
            import io
            buffer = io.BytesIO()
            # Ensure data is on CPU and is a numpy array for save_wav
            if isinstance(wav_data, torch.Tensor):
                wav_data_np = wav_data.detach().cpu().numpy()
            else: # Assume it's already a numpy array if not a tensor
                 wav_data_np = wav_data
            
            self.processor.save_wav(wav=wav_data_np, path=buffer)
            wav_bytes = buffer.getvalue()
            return wav_bytes

        except Exception as e:
            logger.error(f"Error during synthesis: {e}", exc_info=True) # Log stack trace
            # Re-raise the exception to be handled by the caller (Flask app)
            raise
