import json
from pathlib import Path

from itu_p1203 import P1203Pa


def calculate_case(name, segments):

    model = P1203Pa(
        segments,
        stream_id=1
    )

    result = model.calculate()

    # P.1203Pa returns:
    #
    # {
    #     "audio": {
    #         "streamId": ...,
    #         "O21": [...]
    #     }
    # }
    #
    # Extract the actual numeric O.21 sequence.
    scores = result["audio"]["O21"]

    return {
        "name": name,
        "duration_seconds": sum(
            s["duration"]
            for s in segments
        ),
        "number_of_segments": len(segments),
        "number_of_output_samples": len(scores),
        "O21": scores,
        "min_O21": min(scores),
        "max_O21": max(scores),
        "average_O21": sum(scores) / len(scores),
    }


cases = [

    (
        "constant_aaclc_128",
        [
            {
                "start": 0,
                "dts": 0,
                "duration": 20,
                "type": "audio",
                "codec": "aaclc",
                "bitrate": 128,
            }
        ],
    ),

    (
        "adaptive_aaclc",
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
        ],
    ),
]


results = []

for name, segments in cases:

    results.append(
        calculate_case(
            name,
            segments
        )
    )


output = Path(
    "p1203_core_tests/reports/core_report.json"
)

output.parent.mkdir(
    parents=True,
    exist_ok=True
)

output.write_text(
    json.dumps(
        results,
        indent=2
    ),
    encoding="utf-8"
)

print(
    f"Report written to: {output}"
)

print()

for case in results:

    print("=" * 60)
    print(case["name"])
    print("=" * 60)

    print(
        f"Duration: "
        f"{case['duration_seconds']:.2f} sec"
    )

    print(
        f"Segments: "
        f"{case['number_of_segments']}"
    )

    print(
        f"O.21 samples: "
        f"{case['number_of_output_samples']}"
    )

    print(
        f"Minimum O.21: "
        f"{case['min_O21']:.6f}"
    )

    print(
        f"Maximum O.21: "
        f"{case['max_O21']:.6f}"
    )

    print(
        f"Average O.21: "
        f"{case['average_O21']:.6f}"
    )

    print()