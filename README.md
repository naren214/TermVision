# Caramelldansen Terminal Video Player

A small Windows terminal player that turns a video into a live, full-color ASCII animation. It renders frames with ANSI true color, adapts to terminal resizing, synchronizes playback to the video frame rate, and extracts audio through the FFmpeg binary bundled with `imageio-ffmpeg`.

> Bring your own video file. Media files are not included in this repository.

## Features

- Full-color ANSI output using 24-bit RGB
- Brightness-based ASCII shading (` .:-=+*#%@`)
- Terminal-size-aware rendering with character-cell aspect correction
- Frame timing based on a monotonic clock, with frame skipping when rendering falls behind
- Optional synchronized audio playback on Windows
- Temporary extracted audio is removed during normal shutdown
- Quit with **Q**, **Esc**, or **Ctrl+C**

## Requirements

- Windows 10/11 and Windows Terminal (recommended) or a compatible ANSI terminal
- Python 3.10 or newer
- A video file readable by OpenCV

Python packages: `opencv-python`, `numpy`, and `imageio-ffmpeg`. Audio playback uses Python's Windows-only `winsound` standard-library module; video playback can still run where `winsound` is unavailable, but audio will be silent.

## Setup

Open PowerShell in the project directory and install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, run the install commands with `.venv\Scripts\python.exe` directly instead.

## Run

Pass the path to a video as the first argument:

```powershell
python .\caramelDansen.py "C:\Path\To\video.mp4"
```

The path may contain spaces when it is quoted. The script does not assume a particular video is installed on your computer.

## How it works

1. OpenCV reads video metadata and decodes frames.
2. The current terminal dimensions determine the output grid while preserving the video's proportions for typical monospace fonts.
3. Each frame is resized, converted to RGB and grayscale, and each pixel's brightness selects an ASCII character.
4. RGB ANSI escape sequences color the characters. A buffered frame is written at once, and cursor positioning updates the display without clearing it on every frame.
5. A monotonic clock selects the frame due at the current playback time. Frames are skipped if rendering falls behind, helping video track real time.
6. On Windows, `imageio-ffmpeg` extracts audio to a temporary PCM WAV file and `winsound` plays it asynchronously.

## Notes and limitations

- This project targets Windows. `winsound` and `msvcrt` provide Windows audio and keyboard handling; those controls are unavailable on other platforms.
- Use a terminal with ANSI true-color support. Windows Terminal is recommended.
- Playback performance depends on terminal size, terminal rendering speed, video codec, and computer hardware. A smaller terminal window can improve performance.
- Audio extraction requires a video with an audio stream. If extraction or playback is unavailable, the video renderer can continue without sound.
- The current implementation uses a fixed ASCII brightness ramp and does not provide a graphical window or audio controls beyond stopping playback.

## Repository contents

```text
.
├── caramelDansen.py   # Player
├── requirements.txt   # Python dependencies
├── .gitignore
└── README.md
```

## License

No license has been added yet. Until one is chosen, normal copyright applies and others should not assume they have permission to reuse or redistribute the code.
