# src/tts_engine.py

import os
import torch
from TTS.tts.models.xtts import Xtts, XttsAudioConfig
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.config.shared_configs import BaseDatasetConfig
from TTS.utils.audio import AudioProcessor
# Need safe_globals for loading checkpoints containing non-weight data (like XttsConfig)
from torch.serialization import safe_globals 

# --- Configuration ---
# Default model path (can be overridden in constructor)
DEFAULT_MODEL_PATH = "../model/XTTS-v2" 
# Determine if CUDA is available and desired
USE_CUDA = torch.cuda.is_available()
# USE_CUDA = False # Uncomment to force CPU (e.g., for low VRAM)

class TTSEngine:
    """A class to handle XTTS model loading and synthesis."""

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, use_cuda: bool = USE_CUDA):
        """
        Initializes the TTS engine by loading the config and model.

        Args:
            model_path: Path to the XTTS model directory.
            use_cuda: Whether to attempt using CUDA for inference.
        """
        print(f"Initializing TTSEngine from: {model_path}")
        print(f"Using CUDA: {use_cuda}")

        self.model_path = model_path
        self.use_cuda = use_cuda
        self.config = None
        self.model = None
        self.ap = None # Audio Processor

        try:
            self._load_config()
            self._load_model()
            self._init_audio_processor()
            print("TTSEngine initialized successfully.")
        except Exception as e:
            print(f"Error during TTSEngine initialization: {e}")
            # Depending on the error, you might want to raise it or handle it
            # For now, the engine will be in a non-functional state if init fails
            self.model = None 
            self.ap = None

    def _load_config(self):
        """Loads the XTTS configuration file."""
        config_path = os.path.join(self.model_path, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at {config_path}")
        
        print("Loading configuration...")
        self.config = XttsConfig()
        self.config.load_json(config_path)

        # --- Apply necessary overrides ---
        # These might be needed if the checkpoint expects different settings
        # than the default config provides, or if you want specific audio quality.
        # Based on the original xtts.py:
        print("Applying audio configuration overrides...")
        self.config.audio = {
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
        self.config.model_args.num_mel_positions = 608 
        self.config.model_args.num_text_positions = 404 

    def _load_model(self):
        """Initializes and loads the XTTS model checkpoint."""
        if not self.config:
            raise ValueError("Configuration must be loaded before loading the model.")

        # checkpoint_path = os.path.join(self.model_path, "model.pth") # Not explicitly needed if using checkpoint_dir
        vocab_path = os.path.join(self.model_path, "vocab.json")

        # if not os.path.exists(checkpoint_path):
        #     raise FileNotFoundError(f"Model checkpoint file not found at {checkpoint_path}")
        if not os.path.exists(self.model_path):
             raise FileNotFoundError(f"Model directory not found at {self.model_path}")
        if not os.path.exists(vocab_path):
             raise FileNotFoundError(f"Vocabulary file not found at {vocab_path}")
            
        print("Initializing model from config...")
        self.model = Xtts.init_from_config(self.config)
        
        print("Loading model checkpoint...")
        # Use safe_globals context manager to allow loading specific classes
        # Add ALL classes mentioned in the PyTorch error messages here
        with safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig]):
            self.model.load_checkpoint(
                config=self.config, 
                checkpoint_dir=self.model_path, 
                vocab_path=vocab_path, 
                use_deepspeed=False
            )

        if self.use_cuda:
            print("Moving model to CUDA...")
            try:
                self.model.cuda()
            except Exception as e:
                print(f"Warning: Failed to move model to CUDA: {e}. Using CPU.")
                self.use_cuda = False # Fallback to CPU
        else:
             print("Using CPU for model inference.")

    def _init_audio_processor(self):
         """Initializes the audio processor from the config."""
         if not self.config:
             raise ValueError("Configuration must be loaded before initializing AudioProcessor.")
         print("Initializing Audio Processor...")
         self.ap = AudioProcessor.init_from_config(self.config)

    def synthesize_segment(self, text: str, speaker_wav: str, output_path: str, language: str = "en"):
        """
        Synthesizes audio for a given text segment using a speaker reference.

        Args:
            text: The text to synthesize.
            speaker_wav: Path to the reference WAV file for voice cloning.
            output_path: Path to save the generated WAV file.
            language: Language code for synthesis (default: 'en').
        """
        if not self.model or not self.config or not self.ap:
            print("Error: TTSEngine is not properly initialized. Cannot synthesize.")
            return

        if not os.path.exists(speaker_wav):
             print(f"Error: Speaker reference file not found: {speaker_wav}")
             return # Or raise an error

        try:
            print(f"  Synthesizing text: '{text[:60]}...' with speaker: {os.path.basename(speaker_wav)}")
            
            # Perform inference
            outputs = self.model.synthesize(
                text=text,
                config=self.config,
                speaker_wav=[speaker_wav], # Expects a list
                language=language,
                # Potentially add other parameters like gpt_cond_len, temperature etc. if needed
            )

            # Check if 'wav' key exists in the output
            if "wav" not in outputs:
                print("Error: TTS model did not return 'wav' data in the output.")
                # You might want to inspect the 'outputs' dictionary here for error details
                print(f"Model outputs: {outputs}") 
                return

            # Save the synthesized audio
            print(f"  Saving synthesized audio to: {output_path}")
            self.ap.save_wav(outputs["wav"], output_path)
            print("  Audio saved successfully.")

        except RuntimeError as e:
            # Catch potential CUDA OOM errors or other runtime issues
            print(f"Error during TTS synthesis for '{text[:60]}...': {e}")
            # Re-raise or handle as needed
            raise 
        except Exception as e:
            print(f"An unexpected error occurred during synthesis or saving: {e}")
            # Re-raise or handle as needed
            raise
