import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen

from tqdm import tqdm

RE_ENTRY_ID = re.compile(
    r"https?://(?:webtv\.|media\.)un\.org/[a-z]{2}/asset/k[a-z\d]+/k([a-z\d]+)"
)


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


def download_video(
    media_url: str,
    language: str = "en",
    resolution: str = "1080",
    output_filename: Optional[str] = None,
    show_progress: bool = True,
    quiet: bool = False,
) -> Optional[str]:
    """
    Finds the matching stream and downloads it.
    Can be run silently (quiet=True) or without a progress bar (show_progress=False).
    """
    entry_id = extract_entry_id(media_url)
    if not entry_id:
        raise ValueError("Invalid UN Web TV URL")

    data = get_metadata(entry_id)

    video_streams = [s for s in data["streams"] if s["type"] == "video"]
    if not video_streams:
        raise ValueError("No video streams found for this URL.")

    lang_streams = [
        s for s in video_streams if s["language"].lower() == language.lower()
    ]
    if not lang_streams:
        if not quiet:
            print(f"Warning: Language '{language}' not found. Falling back to default.")
        lang_streams = video_streams

    target_res = int(resolution.replace("p", ""))
    best_stream = None

    for stream in lang_streams:
        if stream["resolution"] <= target_res:
            best_stream = stream
            break

    if not best_stream:
        best_stream = lang_streams[0]

    if not output_filename:
        safe_name = "".join(
            [c for c in data["name"] if c.isalpha() or c.isdigit() or c == " "]
        ).rstrip()
        res_label = f"{best_stream['resolution']}p"
        lang_label = best_stream["language"]
        output_filename = f"{safe_name}_{lang_label}_{res_label}.mp4"

    if not quiet:
        print(
            f"Selected Stream: Video ({best_stream['language']}, {best_stream['resolution']}p)"
        )

    req = Request(best_stream["url"], headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req) as response:
        total_size = int(response.getheader("Content-Length", 0))
        block_size = 1024 * 8

        # Disable tqdm if show_progress is False OR if quiet mode is active
        disable_pbar = not show_progress or quiet

        with open(output_filename, "wb") as out_file:
            with tqdm(
                total=total_size,
                unit="iB",
                unit_scale=True,
                desc=f"Downloading {output_filename}",
                ascii=True,
                disable=disable_pbar,
            ) as progress_bar:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    progress_bar.update(len(chunk))

    if not quiet:
        print("Download complete!")

    return os.path.abspath(output_filename)
