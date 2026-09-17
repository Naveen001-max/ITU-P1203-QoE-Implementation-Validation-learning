from itu_p1203 import P1203Pa


def run_case(name, segments):

    model = P1203Pa(
        segments,
        stream_id=1
    )

    result = model.calculate()

    scores = result["audio"]["O21"]

    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    print(f"Segments : {len(segments)}")
    print(
        f"Duration : "
        f"{sum(s['duration'] for s in segments):.2f} sec"
    )
    print(f"Samples  : {len(scores)}")

    print()

    for index, score in enumerate(scores, start=1):

        print(
            f"t={index:02d}s    "
            f"O.21={score:.6f}"
        )

    print()


if __name__ == "__main__":

    run_case(
        "Constant AAC-LC / 128 kbps",
        [
            {
                "start": 0,
                "dts": 0,
                "duration": 20,
                "type": "audio",
                "codec": "aaclc",
                "bitrate": 128,
            }
        ]
    )

    run_case(
        "Adaptive AAC-LC",
        [
            {
                "start": 0,
                "dts": 0,
                "duration": 5,
                "type": "audio",
                "codec": "aaclc",
                "bitrate": 32,
            },
            {
                "start": 5,
                "dts": 5,
                "duration": 5,
                "type": "audio",
                "codec": "aaclc",
                "bitrate": 64,
            },
            {
                "start": 10,
                "dts": 10,
                "duration": 5,
                "type": "audio",
                "codec": "aaclc",
                "bitrate": 48,
            },
            {
                "start": 15,
                "dts": 15,
                "duration": 5,
                "type": "audio",
                "codec": "aaclc",
                "bitrate": 64,
            },
        ]
    )