import unittest

from itu_p1203 import P1203Pa


class TestBitrateResponse(unittest.TestCase):

    def get_score(self, bitrate):

        frames = [
            {
                "dts": 0,
                "duration": 20,
                "type": "audio",
                "codec": "aaclc",
                "bitrate": bitrate,
            }
        ]

        model = P1203Pa(frames)

        result = model.calculate()

        return result["audio"]["O21"][0]

    def test_bitrate_ordering(self):

        score_32 = self.get_score(32.0)
        score_64 = self.get_score(64.0)
        score_128 = self.get_score(128.0)

        self.assertLessEqual(
            score_32,
            score_64
        )

        self.assertLessEqual(
            score_64,
            score_128
        )


if __name__ == "__main__":
    unittest.main()