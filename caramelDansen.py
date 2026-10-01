import os
import sys
import time
import shutil
import atexit
import signal
import tempfile
import subprocess
import argparse

try:
    import cv2
    import numpy as np
    import imageio_ffmpeg
except ImportError as exc:
    raise SystemExit(
        "Missing project dependencies. Install them with: "
        "python -m pip install -r requirements.txt"
    ) from exc

try:
    import winsound
except ImportError:
    winsound = None

try:
    import msvcrt
except ImportError:
    msvcrt = None

# ANSI escape sequences
C_HIDE_CURSOR = "\033[?25l"
C_SHOW_CURSOR = "\033[?25h"
C_RESET = "\033[0m"
C_HOME = "\033[H"
C_CLEAR = "\033[2J"
C_CLEAR_EOL = "\033[K"
C_CLEAR_DOWN = "\033[J"

ASCII_CHARS = " .:-=+*#%@"
ASCII_ARRAY = np.array(list(ASCII_CHARS))
NUM_CHARS = len(ASCII_CHARS)

temp_audio_file = None

def cleanup():
    global temp_audio_file
    if winsound:
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
    # Restore cursor visibility and reset ANSI colors
    sys.stdout.write(f"{C_SHOW_CURSOR}{C_RESET}\n")
    sys.stdout.flush()
    if temp_audio_file and os.path.exists(temp_audio_file):
        try:
            os.remove(temp_audio_file)
        except Exception:
            pass

atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

def extract_audio(video_path):
    global temp_audio_file
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        temp_dir = tempfile.gettempdir()
        temp_audio_file = os.path.join(temp_dir, f"carameldansen_audio_{os.getpid()}_{int(time.time())}.wav")
        # Extract audio to 16-bit PCM WAV (stereo, 44100Hz) for winsound
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            temp_audio_file
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(temp_audio_file) and os.path.getsize(temp_audio_file) > 1000:
            return temp_audio_file
    except Exception as e:
        pass
    return None

def main():
    # Enable ANSI escape processing in Windows console
    os.system("")

    parser = argparse.ArgumentParser(
        description="Play a video as full-color ASCII art in the terminal."
    )
    parser.add_argument("video", help="path to the video file to play")
    video_path = parser.parse_args().video
    if not os.path.isfile(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    print(f"Loading Caramelldansen video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file: {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or np.isnan(fps):
        fps = 30.0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    video_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    if video_width <= 0 or video_height <= 0:
        video_width, video_height = 16.0, 9.0

    print("Extracting audio track for sync playback...")
    audio_path = extract_audio(video_path)

    # Hide cursor and clear screen initially
    sys.stdout.write(f"{C_HIDE_CURSOR}{C_CLEAR}{C_HOME}")
    sys.stdout.flush()

    last_term_size = None
    target_w, target_h = 80, 24

    # Start audio playback asynchronously at the exact moment video playback begins
    if audio_path and winsound:
        try:
            winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass

    start_time = time.perf_counter()
    current_frame_idx = -1

    try:
        while True:
            # Check for keyboard quit ('q' or ESC)
            if msvcrt and msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b'q', b'Q', b'\x1b', b'\x03'):
                    break

            # Dynamic terminal resize adaptation
            term_size = shutil.get_terminal_size((80, 24))
            if term_size != last_term_size:
                last_term_size = term_size
                cols, rows = term_size
                max_w = cols
                max_h = max(1, rows - 1)

                # Character cells are roughly twice as tall as they are wide (~0.5 aspect ratio).
                # To maintain correct visual proportions:
                char_aspect = 2.0
                video_aspect = (video_width / video_height) * char_aspect

                w_candidate = int(max_h * video_aspect)
                if w_candidate <= max_w:
                    target_w = max(1, w_candidate)
                    target_h = max_h
                else:
                    target_w = max_w
                    target_h = max(1, int(max_w / video_aspect))

                sys.stdout.write(C_CLEAR)

            # Compute which frame should show based on real elapsed time
            elapsed = time.perf_counter() - start_time
            target_frame = int(elapsed * fps)

            if total_frames > 0 and target_frame >= total_frames:
                break

            # If ahead of schedule, sleep briefly
            if target_frame <= current_frame_idx:
                sleep_dur = (current_frame_idx + 1) / fps - (time.perf_counter() - start_time)
                if sleep_dur > 0.002:
                    time.sleep(sleep_dur * 0.75)
                continue

            # If behind schedule, skip frames to maintain perfect synchronization
            frames_to_skip = target_frame - (current_frame_idx + 1)
            if frames_to_skip > 0:
                if frames_to_skip < 15:
                    for _ in range(frames_to_skip):
                        cap.grab()
                else:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            ret, frame = cap.read()
            if not ret:
                break

            current_frame_idx = target_frame

            # Resize to terminal dimensions
            resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

            # Convert color channels and grayscale luminance
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

            # Map brightness to ASCII characters
            char_indices = (gray.astype(np.int32) * NUM_CHARS) // 256
            np.clip(char_indices, 0, NUM_CHARS - 1, out=char_indices)
            chars = ASCII_ARRAY[char_indices]

            # Build 24-bit ANSI colored ASCII frame
            lines = []
            for y in range(target_h):
                row_rgb = rgb[y]
                row_chars = chars[y]
                line_str = "".join(
                    f"\033[38;2;{r};{g};{b}m{c}"
                    for (r, g, b), c in zip(row_rgb, row_chars)
                ) + C_CLEAR_EOL
                lines.append(line_str)

            # Redraw using cursor-home without clearing screen for zero flicker
            frame_output = C_HOME + "\n".join(lines) + C_CLEAR_DOWN + C_RESET
            sys.stdout.write(frame_output)
            sys.stdout.flush()

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cleanup()

if __name__ == "__main__":
    main()
