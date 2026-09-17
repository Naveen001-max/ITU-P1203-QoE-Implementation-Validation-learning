import json
import subprocess
import sys
from pathlib import Path


def inspect_dash(mpd_url: str):
    """
    Inspect a MPEG-DASH MPD using FFmpeg without modifying
    or downloading the complete stream.
    """

    command = [
        "ffprobe",
        "-v", "error",
        "-show_programs",
        "-show_streams",
        "-of", "json",
        mpd_url,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    data = json.loads(result.stdout)

    streams = []

    for stream in data.get("streams", []):
        entry = {
            "index": stream.get("index"),
            "codec_type": stream.get("codec_type"),
            "codec_name": stream.get("codec_name"),
            "codec_long_name": stream.get("codec_long_name"),
            "width": stream.get("width"),
            "height": stream.get("height"),
            "bit_rate": stream.get("bit_rate"),
            "sample_rate": stream.get("sample_rate"),
            "channels": stream.get("channels"),
            "avg_frame_rate": stream.get("avg_frame_rate"),
            "duration": stream.get("duration"),
            "id": stream.get("id"),
            "metadata": stream.get("tags", {}),
        }

        streams.append(entry)

    return {
        "source": mpd_url,
        "streams": streams,
    }


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("python dash_integration\\dash_inspector.py <MPD_URL>")
        sys.exit(1)

    mpd_url = sys.argv[1]

    result = inspect_dash(mpd_url)

    output = Path("dash_integration/output/dash_stream_info.json")
    output.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2))
    print()
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()