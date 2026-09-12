# UN Web TV Extractor

A modular Python package and Command Line Interface (CLI) tool for extracting metadata and downloading videos directly from UN Web TV. 

## Features
* **Metadata Extraction:** Retrieve video names, creation dates, duration, and available stream URLs.
* **Smart Stream Selection:** Evaluates and downloads video (by resolution) and audio (by language) tracks independently to ensure precise matching.
* **Automatic Muxing:** Automatically merges separated video and audio tracks losslessly using `FFmpeg`.
* **CLI & Python API:** Use it directly from your terminal or import it as a dependency in your own Python projects
* **Progress Tracking:** Terminal progress bars using `tqdm`, with options for silent execution

## Prerequisites

To merge downloaded audio and video streams automatically, **FFmpeg** must be installed and accessible via your system's PATH. 
* **macOS:** `brew install ffmpeg`
* **Linux (Ubuntu/Debian):** `sudo apt install ffmpeg`
* **Windows:** Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or install via Winget: `winget install ffmpeg`

## Installation

**From GitHub**  
You can install the package directly from the repository using `pip`:
```bash
pip install git+https://github.com/saydemr/unwebtv.git
```

**From Source (Local)**  
You can also install this package locally. Navigate to the root directory of the project (where `pyproject.toml` is located) and run:
```bash
pip install .
```

If you are developing the package and want changes to reflect immediately, install it in editable mode:
```bash
pip install -e .
```

## Usage

### Command Line Interface (CLI)

Installing the package automatically adds the `unwebtv` command to your terminal.

**1. List available streams (Languages and Resolutions):**
```bash
unwebtv "https://webtv.un.org/..." --list
```

**2. Download with default settings (English, highest resolution up to 1080p, automatically muxed):**
```bash
unwebtv "https://webtv.un.org/..."
```

**3. Download a specific language and resolution:**
```bash
unwebtv "https://webtv.un.org/..." --lang fr --res 720 --out custom_name.mp4
```

**4. Download tracks separately (Bypass FFmpeg muxing):**
```bash
unwebtv "https://webtv.un.org/..." --no-mux
```

**5. Disable the progress bar:**
```bash
unwebtv "https://webtv.un.org/..." --no-progress
```

**6. Run silently (no terminal output or progress bar):**
```bash
unwebtv "https://webtv.un.org/..." --quiet
# or
unwebtv "https://webtv.un.org/..." -q
```

### Python API

You can import the module into your own Python scripts to automate downloads or extract metadata.

```python
from unwebtv import download_video, get_metadata, extract_entry_id

media_url = "https://webtv.un.org/..."

# Example 1: Simple Download (Defaults to English, 1080p, automatic muxing, shows progress bar)
download_video(media_url)

# Example 2: Download specific stream
download_video(media_url, language='fr', resolution='720', output_filename='speech.mp4')

# Example 3: Download silently (ideal for background scripts/cron jobs)
download_video(media_url, quiet=True)

# Example 4: Bypass automatic muxing (saves _video.mp4 and _audio.mp4 separately)
download_video(media_url, mux=False)

# Example 5: Download with output text but no progress bar
download_video(media_url, show_progress=False)

# Example 6: Just fetch metadata and URLs without downloading
entry_id = extract_entry_id(media_url)
if entry_id:
    metadata = get_metadata(entry_id)
    print(f"Title: {metadata['name']}")
    print(f"Available streams: {len(metadata['streams'])}")
```

## Acknowledgments

This project is a refactored and modularized derivative of the [un-web-tv-downloader](https://github.com/NiceLabs/un-web-tv-downloader) created by [NiceLabs](https://github.com/NiceLabs). 

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**. 

* Copyright (c) 2026 saydemr (Modifications, CLI, and package structure)
* Copyright (c) 2023 NiceLabs (Original core extraction logic)

You may freely use, modify, and distribute this software, provided that any derivative works are also open-source and licensed under GPL-3.0. See the `LICENSE` file for more details.