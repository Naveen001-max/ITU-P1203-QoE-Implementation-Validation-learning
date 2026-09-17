import json
from pathlib import Path

from itu_p1203.p1203_standalone import P1203Standalone


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"

TRACE_FILE = OUTPUT / "dash_playback_trace.json"
STREAM_INFO_FILE = OUTPUT / "dash_stream_info.json"
P1203_FILE = OUTPUT / "p1203_dash_input.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_video_segments(trace, representations, duration):
    playback_events = [
        event
        for event in trace
        if event.get("event") == "PLAYBACK"
        and event.get("representation_id")
    ]

    if not playback_events:
        raise RuntimeError(
            "No PLAYBACK events containing representation_id were found."
        )

    playback_events.sort(
        key=lambda event: float(event["playback_time"])
    )

    segments = []

    current_representation = None
    current_start = 0.0

    for event in playback_events:
        time = float(event["playback_time"])
        representation_id = event["representation_id"]

        # First observed representation is considered active from t=0.
        if current_representation is None:
            current_representation = representation_id
            current_start = 0.0
            continue

        if representation_id == current_representation:
            continue

        metadata = representations.get(current_representation)

        if metadata:
            segment_duration = time - current_start

            if segment_duration > 0:
                segments.append({
                    "codec": metadata["codec"],
                    "start": round(current_start, 6),
                    "duration": round(segment_duration, 6),
                    "resolution": (
                        f'{metadata["width"]}x{metadata["height"]}'
                    ),
                    "bitrate": round(metadata["bitrate"], 6),
                    "fps": metadata["fps"],
                    "representation": current_representation,
                })

        current_representation = representation_id
        current_start = time

    # Close final segment.
    metadata = representations.get(current_representation)

    if metadata:
        segment_duration = duration - current_start

        if segment_duration > 0:
            segments.append({
                "codec": metadata["codec"],
                "start": round(current_start, 6),
                "duration": round(segment_duration, 6),
                "resolution": (
                    f'{metadata["width"]}x{metadata["height"]}'
                ),
                "bitrate": round(metadata["bitrate"], 6),
                "fps": metadata["fps"],
                "representation": current_representation,
            })

    return segments


def build_p1203_input(trace_data, stream_data):
    duration = float(trace_data["duration"])
    trace = trace_data["trace"]

    # ---------------------------------------------------------
    # Representation metadata
    # ---------------------------------------------------------

    representations = {}

    for stream in stream_data["streams"]:
        if stream.get("codec_type") != "video":
            continue

        metadata = stream.get("metadata") or {}
        representation_id = metadata.get("id")

        if not representation_id:
            continue

        representations[representation_id] = {
            "width": stream.get("width"),
            "height": stream.get("height"),
            "bitrate": float(
                metadata.get("variant_bitrate")
                or stream.get("bit_rate")
                or 0
            ) / 1000.0,
            "fps": 25,
            "codec": "h264",
        }

    # ---------------------------------------------------------
    # Video
    # ---------------------------------------------------------

    video_segments = build_video_segments(
        trace,
        representations,
        duration,
    )

    # ---------------------------------------------------------
    # Audio
    # ---------------------------------------------------------

    audio_streams = [
        stream
        for stream in stream_data["streams"]
        if stream.get("codec_type") == "audio"
    ]

    audio_segments = []

    if audio_streams:
        audio = audio_streams[0]

        audio_metadata = audio.get("metadata") or {}

        audio_bitrate = float(
            audio.get("bit_rate")
            or audio_metadata.get("variant_bitrate")
            or 0
        ) / 1000.0

        audio_segments.append({
            "codec": "aaclc",
            "start": 0.0,
            "duration": round(duration, 6),
            "bitrate": round(audio_bitrate, 6),
        })

    # ---------------------------------------------------------
    # Stalling
    #
    # Current trace contains no stall/buffering events.
    # Therefore I23 correctly contains an empty list.
    # ---------------------------------------------------------

    stalling = []

    # ---------------------------------------------------------
    # P.1203 input
    # ---------------------------------------------------------

    return {
        "IGen": {
            "displaySize": "1920x1080",
            "device": "pc",
            "viewingDistance": 0,
        },

        "I13": {
            "streamId": 42,
            "segments": video_segments,
        },

        "I11": {
            "streamId": 42,
            "segments": audio_segments,
        },

        "I23": {
            "streamId": 42,
            "stalling": stalling,
        },
    }


def run_p1203(p1203_input):
    """
    Run the same P.1203 implementation used by:

        python -m itu_p1203 ...

    but directly from Python.
    """

    model = P1203Standalone(
        p1203_input,
        debug=False,
        quiet=True,
    )

    return model.calculate_complete(print_intermediate=False)


def main():
    trace_data = load_json(TRACE_FILE)
    stream_data = load_json(STREAM_INFO_FILE)

    p1203_input = build_p1203_input(
        trace_data,
        stream_data,
    )

    # ---------------------------------------------------------
    # Save P.1203 input
    # ---------------------------------------------------------

    with open(
        P1203_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            p1203_input,
            f,
            indent=2,
        )

    # ---------------------------------------------------------
    # Run P.1203 directly
    # ---------------------------------------------------------

    result = run_p1203(p1203_input)

    print()
    print("========================================")
    print("DASH -> P.1203 PIPELINE COMPLETE")
    print("========================================")
    print()

    print(
        f'Duration: {trace_data["duration"]:.3f} seconds'
    )

    print(
        f'Video segments: '
        f'{len(p1203_input["I13"]["segments"])}'
    )

    print(
        f'Audio segments: '
        f'{len(p1203_input["I11"]["segments"])}'
    )

    print(
        f'Stalling events: '
        f'{len(p1203_input["I23"]["stalling"])}'
    )

    print()
    print("P.1203 OUTPUT")
    print("----------------------------------------")
    print(json.dumps(result, indent=2))

    print()
    print("P.1203 INPUT:")
    print(P1203_FILE)


if __name__ == "__main__":
    main()