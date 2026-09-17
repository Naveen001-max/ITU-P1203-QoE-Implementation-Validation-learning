import unittest

from itu_p1203 import P1203Pa


class TestConstantStream(unittest.TestCase):

    def test_constant_aaclc_stream(self):

        frames = [
            {
                "dts": 0,
                "duration": 20,
                "type": "audio",
                "codec": "aaclc",
                "bitrate": 128,
            }
        ]

        model = P1203Pa(
            frames,
            stream_id=1
        )

        result = model.calculate()

        scores = result["audio"]["O21"]

        self.assertEqual(
            len(scores),
            20
        )

        first = scores[0]

        for score in scores:

            self.assertAlmostEqual(
                score,
                first,
                places=12
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