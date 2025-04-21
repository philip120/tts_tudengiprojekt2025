from TTS.tts.models.xtts import Xtts
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.utils.audio import AudioProcessor
import torch, os
from torch.serialization import safe_globals

BASE_PATH = "model/XTTS-v2"
REFERENCE_WAV = "reference/recording2.wav"
OUTPUT_PATH = "output/base_philip.wav"

# Load config
config = XttsConfig()
config.load_json(os.path.join(BASE_PATH, "config.json"))

# Force override audio settings
config.audio = {
    "sample_rate": 24000,
    "output_sample_rate": 24000,
    "frame_length_ms": 40,
    "frame_shift_ms": 10,
    "n_fft": 1024,
    "num_mels": 80,
    "mel_fmin": 0,
    "mel_fmax": 12000
}
config.model_args.num_mel_positions = 608
config.model_args.num_text_positions = 404

# Init model
model = Xtts.init_from_config(config)

# Use safe_globals context manager to allow loading XttsConfig
with safe_globals([XttsConfig]):
    model.load_checkpoint(
        config,
        checkpoint_path=os.path.join(BASE_PATH, "model.pth"),
        checkpoint_dir=BASE_PATH,
        vocab_path=os.path.join(BASE_PATH, "vocab.json"),
        use_deepspeed=False
    )

# model.cuda() # Commented out to force CPU usage due to low VRAM

# Inference
output = model.synthesize(
    text="Hi, my name is Philip, I am a University student in my second year. Here is my laughter: hahahaha",
    config=config,
    speaker_wav=[REFERENCE_WAV],
    language="en"
)

# Save to wav
ap = AudioProcessor.init_from_config(config)
ap.save_wav(output["wav"], OUTPUT_PATH)

print(f"[✅] Saved to {OUTPUT_PATH}")