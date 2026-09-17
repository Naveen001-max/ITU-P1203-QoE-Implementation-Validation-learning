import unittest

from itu_p1203 import P1203Pa


class TestP12032MeasurementWindow(unittest.TestCase):

    def make_segments(self):

        return [
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

    def test_twenty_second_output(self):

        model = P1203Pa(
            self.make_segments(),
            stream_id=1
        )

        result = model.calculate()

        scores = result["audio"]["O21"]

        self.assertEqual(
            len(scores),
            20
        )

    def test_scores_are_numeric(self):

        model = P1203Pa(
            self.make_segments(),
            stream_id=1
        )

        result = model.calculate()

        scores = result["audio"]["O21"]

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


if __name__ == "__main__":
    unittest.main()