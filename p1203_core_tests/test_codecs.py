import unittest

from itu_p1203 import P1203Pa


class TestP12032Codecs(unittest.TestCase):

    CODECS = [
        "aaclc",
        "heaac",
        "mp2",
        "ac3",
    ]

    def setUp(self):
        self.model = P1203Pa([])

    def test_all_supported_codecs(self):

        for codec in self.CODECS:

            with self.subTest(codec=codec):

                score = self.model.audio_model_function(
                    codec,
                    128.0
                )

                self.assertIsInstance(score, float)

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