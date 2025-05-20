# src/audio_combiner.py

import os
from pydub import AudioSegment

def combine_audio_segments(segment_paths: list[str], output_path: str):
    """
    Combines multiple WAV audio segments into a single WAV file.

    Args:
        segment_paths: A list of paths to the WAV audio segments, in the order
                       they should be combined.
        output_path: The path to save the final combined WAV file.
    """
    if not segment_paths:
        print("Error: No audio segments provided to combine.")
        return

    print(f"Combining {len(segment_paths)} audio segments into {output_path}...")
    
    combined_audio = None

    for i, path in enumerate(segment_paths):
        if not os.path.exists(path):
            print(f"Warning: Segment file not found, skipping: {path}")
            continue
        try:
            print(f"  Loading segment {i+1}/{len(segment_paths)}: {os.path.basename(path)}")
            segment = AudioSegment.from_wav(path)
            
            if combined_audio is None:
                combined_audio = segment
            else:
                combined_audio += segment
        except FileNotFoundError:
             print(f"Warning: Segment file not found (redundant check), skipping: {path}")
             continue
        except Exception as e:
            print(f"Warning: Error processing segment {path}: {e}. Skipping this segment.")
            continue 

    if combined_audio is None:
        print("Error: No valid audio segments were loaded. Cannot save output.")
        return

    try:
        print(f"Exporting combined audio to: {output_path}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        combined_audio.export(output_path, format="wav")
        print("Combined audio saved successfully.")
    except Exception as e:
        print(f"Error exporting combined audio to {output_path}: {e}")
        raise
