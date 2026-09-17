import unittest

from itu_p1203 import P1203Pa


class TestSegmentSwitch(unittest.TestCase):

    def test_bitrate_switch_changes_quality(self):

        frames = [
            {
                "start": 0,
                "dts": 0,
                "duration": 10,
                "type": "audio",
                "codec": "aaclc",
                "bitrate": 32,
            },
            {
                "start": 10,
                "dts": 10,
                "duration": 10,
                "type": "audio",
                "codec": "aaclc",
                "bitrate": 128,
            },
        ]

        model = P1203Pa(
            frames,
            stream_id=1
        )

        result = model.calculate()

        scores = result["audio"]["O21"]

        # A 20-second input must produce 20 one-second O.21 outputs.
        self.assertEqual(
            len(scores),
            20
        )

        # Every output must be a valid MOS/O.21 value.
        for score in scores:

            self.assertIsInstance(
                score,
                float
            )

            self.assertGreaterEqual(
                score,
                1.0
            )

            self.assertLessEqual(
                score,
                5.0
            )

        # Because the stream changes from 32 kbps to 128 kbps,
        # the resulting quality sequence should contain more than
        # one distinct value.
        unique_scores = {
            round(score, 10)
            for score in scores
        }

        self.assertGreater(
            len(unique_scores),
            1
        )


if __name__ == "__main__":
    unittest.main()