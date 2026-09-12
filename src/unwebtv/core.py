import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen

from tqdm import tqdm

RE_ENTRY_ID = re.compile(
    r"https?://(?:webtv\.|media\.)un\.org/[a-z]{2}/asset/k[a-z\d]+/k([a-z\d]+)"
)

lang_dict = {
    "en": "English",
    "fr": "French",
    "og": "Interlingua",
}


def extract_entry_id(url: str) -> Optional[str]:
    """Extracts and formats the Kaltura entry ID from a UN Web TV URL."""
    matched = RE_ENTRY_ID.search(url)
    if not matched:
        return None
    (entry_id,) = matched.groups()
    return entry_id[0] + "_" + entry_id[1:]


def get_metadata(entry_id: str) -> Dict[str, Any]:
    """Fetches metadata and structured streams from the Kaltura API."""
    partner_id = 2503451
    data = {
        "apiVersion": "3.3.0",
        "format": 1,
        "partnerId": partner_id,
        "1": {
            "service": "session",
            "action": "startWidgetSession",
            "widgetId": "_" + str(partner_id),
        },
        "2": {
            "service": "baseEntry",
            "action": "list",
            "ks": "{1:result:ks}",
            "filter": {"redirectFromEntryId": entry_id},
        },
        "3": {
            "service": "baseEntry",
            "action": "getPlaybackContext",
            "ks": "{1:result:ks}",
            "entryId": "{2:result:objects:0:id}",
            "contextDataParams": {
                "objectType": "KalturaContextDataParams",
                "flavorTags": "all",
            },
        },
    }
    request = Request(
        method="POST",
        url="https://cdnapisec.kaltura.com/api_v3/service/multirequest",
        headers={"content-type": "application/json"},
        data=json.dumps(data).encode(),
    )

    with urlopen(request) as response:
        payload = json.load(response)

    meta = payload[1]["objects"][0]
    playback = payload[2]

    streams = []

    for assets in playback["flavorAssets"]:
        tags = assets.get("tags", "").split(",")
        is_audio = "audio_only" in tags
        flavor_id = str(assets["flavorParamsId"])

        base_dl_url = meta["downloadUrl"]
        download_url = base_dl_url.rsplit("/", 1)[0] + "/" + flavor_id

        streams.append(
            {
                "type": "audio" if is_audio else "video",
                "language": assets.get("language", "Unknown"),
                "resolution": 0 if is_audio else assets.get("height", 0),
                "url": download_url,
            }
        )

    streams.sort(key=lambda x: x["resolution"], reverse=True)

    return {
        "name": meta["name"],
        "description": meta["description"],
        "created_at": datetime.fromtimestamp(meta["createdAt"]),
        "updated_at": datetime.fromtimestamp(meta["updatedAt"]),
        "duration": timedelta(milliseconds=meta["msDuration"]),
        "streams": streams,
        "original_url": meta["downloadUrl"],
    }


def mux_streams(
    video_file: str, audio_file: str, output_file: str, quiet: bool = False
) -> None:
    """Merges video and audio streams using FFmpeg."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "FFmpeg is not installed or not in the system PATH. Muxing requires FFmpeg."
        )

    if not quiet:
        print("Muxing video and audio streams...")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_file,
            "-i",
            audio_file,
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            output_file,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def download_video(
    media_url: str,
    language: str = "en",
    resolution: str = "1080",
    output_filename: Optional[str] = None,
    show_progress: bool = True,
    quiet: bool = False,
    mux: bool = True,
    keep_streams: bool = False,
    overwrite: bool = False,
) -> Optional[str]:
    """
    Downloads the matching video and audio streams and optionally muxes them.
    """
    entry_id = extract_entry_id(media_url)
    if not entry_id:
        raise ValueError("Invalid UN Web TV URL")

    data = get_metadata(entry_id)

    video_streams = [s for s in data["streams"] if s["type"] == "video"]
    audio_streams = [s for s in data["streams"] if s["type"] == "audio"]

    if not video_streams:
        raise ValueError("No video streams found for this URL.")

    target_res = int(resolution.replace("p", ""))
    best_video = next(
        (s for s in video_streams if s["resolution"] <= target_res), video_streams[0]
    )

    best_audio = None
    if audio_streams:
        lang_audio = [
            s
            for s in audio_streams
            if s["language"].lower() == lang_dict[language].lower()
        ]
        if not lang_audio:
            if not quiet:
                print(
                    f"Warning: Language '{language}' not found. Falling back to default."
                )
            lang_audio = [
                s
                for s in audio_streams
                if s["language"].lower() == lang_dict[language].lower()
            ]
            if lang_audio:
                best_audio = lang_audio[0]
            else:
                best_audio = audio_streams[0]
        else:
            best_audio = lang_audio[0]

    if not output_filename:
        safe_name = (
            "".join(
                [c for c in data["name"] if c.isalpha() or c.isdigit() or c == " "]
            ).rstrip()
            + "_"
            + data["created_at"].strftime("%m%d%y-%H%M%S")
        )
        res_label = f"{best_video['resolution']}p"

        video_output = f"{safe_name}_{res_label}_video.mp4"

        if best_audio:
            lang_label = best_audio["language"]
            audio_output = f"{safe_name}_{lang_label}_audio.mp4"
            final_output = f"{safe_name}_{lang_label}_{res_label}.mp4"
        else:
            audio_output = ""
            final_output = f"{safe_name}_{res_label}.mp4"
    else:
        base_filename, _ = os.path.splitext(output_filename)
        final_output = f"{base_filename}.mp4"
        video_output = f"{base_filename}_video.mp4"
        audio_output = f"{base_filename}_audio.mp4"

    def download_stream(stream_url, filename, desc_label, check_alt_file=None):
        req = Request(stream_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req) as response:
            total_size = int(response.getheader("Content-Length", 0))

            if not overwrite:
                if os.path.exists(filename) and os.path.getsize(filename) == total_size:
                    if not quiet:
                        print(
                            f"Skipping {desc_label}: '{filename}' already exists with matching size."
                        )
                    return filename

                if (
                    check_alt_file
                    and os.path.exists(check_alt_file)
                    and os.path.getsize(check_alt_file) == total_size
                ):
                    if not quiet:
                        print(
                            f"Skipping {desc_label}: '{check_alt_file}' already exists with matching size."
                        )
                    return check_alt_file

            if not quiet:
                print(f"Downloading Stream: {desc_label}")

            block_size = 1024 * 8
            disable_pbar = not show_progress or quiet

            with open(filename, "wb") as out_file:
                with tqdm(
                    total=total_size,
                    unit="iB",
                    unit_scale=True,
                    desc=desc_label,
                    ascii=True,
                    disable=disable_pbar,
                ) as progress_bar:
                    while True:
                        chunk = response.read(block_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        progress_bar.update(len(chunk))
        return filename

    alt_video_file = final_output if not best_audio else None

    actual_video = download_stream(
        best_video["url"],
        video_output,
        f"Video ({best_video['resolution']}p)",
        check_alt_file=alt_video_file,
    )

    actual_audio = None
    if best_audio:
        actual_audio = download_stream(
            best_audio["url"], audio_output, f"Audio ({best_audio['language']})"
        )

    if mux and best_audio:
        try:
            mux_streams(actual_video, actual_audio, final_output, quiet)
            if not quiet:
                print(f"Download complete: {final_output}")
            return os.path.abspath(final_output)
        finally:
            if not keep_streams:
                if (
                    actual_video
                    and os.path.exists(actual_video)
                    and actual_video != final_output
                ):
                    os.remove(actual_video)
                if (
                    actual_audio
                    and os.path.exists(actual_audio)
                    and actual_audio != final_output
                ):
                    os.remove(actual_audio)

    elif mux and not best_audio:
        if actual_video != final_output:
            if keep_streams:
                shutil.copy(actual_video, final_output)
            else:
                shutil.move(actual_video, final_output)

        if not quiet:
            print(f"Download complete: {final_output}")
        return os.path.abspath(final_output)

    else:
        if not quiet:
            print("Muxing bypassed. Streams kept separate.")
        return os.path.abspath(actual_video)
