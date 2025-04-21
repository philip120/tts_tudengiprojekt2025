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
             # Redundant check, but good practice
             print(f"Warning: Segment file not found (redundant check), skipping: {path}")
             continue
        except Exception as e:
            # Catch potential errors during pydub loading/processing
            print(f"Warning: Error processing segment {path}: {e}. Skipping this segment.")
            continue # Skip to the next segment

    if combined_audio is None:
        print("Error: No valid audio segments were loaded. Cannot save output.")
        return

    try:
        print(f"Exporting combined audio to: {output_path}")
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        combined_audio.export(output_path, format="wav")
        print("Combined audio saved successfully.")
    except Exception as e:
        print(f"Error exporting combined audio to {output_path}: {e}")
        # Consider raising the exception if saving is critical
        raise

# --- Simple Test ---
# Removing the test block as requested
# if __name__ == "__main__":
#     print("Running audio_combiner.py standalone test...")
# 
#     # Create dummy WAV files for testing
#     # This requires pydub and potentially ffmpeg/libav installed
#     test_output_dir = "output/combiner_test/"
#     test_temp_dir = os.path.join(test_output_dir, "temp_audio/")
#     final_output = os.path.join(test_output_dir, "combined_test.wav")
# 
#     os.makedirs(test_temp_dir, exist_ok=True)
# 
#     segment_paths_for_test = []
#     silence_duration_ms = 500 # ms
# 
#     try:
#         # Create a few short silent WAVs to combine
#         for i in range(3):
#             segment_path = os.path.join(test_temp_dir, f"dummy_segment_{i}.wav")
#             silence = AudioSegment.silent(duration=silence_duration_ms)
#             silence.export(segment_path, format="wav")
#             segment_paths_for_test.append(segment_path)
#             print(f"Created dummy segment: {segment_path}")
# 
#         print(f"\nAttempting to combine {len(segment_paths_for_test)} dummy segments...")
#         combine_audio_segments(segment_paths_for_test, final_output)
# 
#         if os.path.exists(final_output):
#              print(f"\nTest successful. Combined file created at: {final_output}")
#              # You could optionally play the file here if you have a player library
#              # import simpleaudio as sa
#              # wave_obj = sa.WaveObject.from_wave_file(final_output)
#              # play_obj = wave_obj.play()
#              # play_obj.wait_done()
#         else:
#              print("\nTest failed. Combined file was not created.")
# 
#         # Optional: Clean up dummy files
#         # for p in segment_paths_for_test:
#         #     if os.path.exists(p): os.remove(p)
#         # if os.path.exists(test_temp_dir) and not os.listdir(test_temp_dir): os.rmdir(test_temp_dir)
#         # if os.path.exists(final_output): os.remove(final_output)
#         # if os.path.exists(test_output_dir) and not os.listdir(test_output_dir): os.rmdir(test_output_dir)
# 
#     except ImportError:
#         print("\nError: Requires 'pydub'. Please install it ('pip install pydub').")
#         print("         You might also need ffmpeg or libav installed on your system for pydub.")
#     except Exception as e:
#         print(f"An error occurred during the audio_combiner test: {e}")
#         import traceback
#         traceback.print_exc() 