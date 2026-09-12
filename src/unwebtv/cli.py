import argparse
import sys

from .core import download_video, extract_entry_id, get_metadata


def main():
    parser = argparse.ArgumentParser(
        description="Extract and download UN Web TV videos."
    )
    parser.add_argument("url", help="The UN Web TV media URL")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available languages and resolutions without downloading",
    )
    parser.add_argument("--lang", default="en", help="Target language (default: 'en')")
    parser.add_argument(
        "--res",
        default="1080",
        help="Target resolution, e.g., '1080' or '720' (default: 1080)",
    )
    parser.add_argument("--out", help="Output filename (optional)")
    parser.add_argument(
        "--no-progress", action="store_true", help="Disable the progress bar"
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress all terminal output (implies --no-progress)",
    )
    parser.add_argument(
        "--no-mux",
        action="store_true",
        help="Download video and audio streams separately without muxing",
    )
    parser.add_argument(
        "--keep-streams",
        action="store_true",
        help="Keep the separate audio and video files after muxing",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files instead of skipping download",
    )

    args = parser.parse_args()

    entry_id = extract_entry_id(args.url)
    if not entry_id:
        if not args.quiet:
            print(
                "Error: Could not extract entry ID from the provided URL.",
                file=sys.stderr,
            )
        sys.exit(1)

    if args.list:
        try:
            data = get_metadata(entry_id)
            if not args.quiet:
                print(f"\nTitle: {data['name']}")
                print("-" * 30)
                print(f"{'TYPE':<10} | {'LANGUAGE':<10} | {'RESOLUTION'}")
                print("-" * 30)
                for stream in data["streams"]:
                    res = (
                        f"{stream['resolution']}p"
                        if stream["type"] == "video"
                        else "N/A"
                    )
                    print(
                        f"{stream['type'].upper():<10} | {stream['language']:<10} | {res}"
                    )
        except Exception as e:
            if not args.quiet:
                print(f"Error fetching metadata: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            download_video(
                media_url=args.url,
                language=args.lang,
                resolution=args.res,
                output_filename=args.out,
                show_progress=not args.no_progress,
                quiet=args.quiet,
                mux=not args.no_mux,
                keep_streams=args.keep_streams,
                overwrite=args.overwrite,
            )
        except Exception as e:
            if not args.quiet:
                print(f"Error during download: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
