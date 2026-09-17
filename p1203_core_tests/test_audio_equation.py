import math
import unittest

from itu_p1203 import P1203Pa


class TestP12032AudioEquation(unittest.TestCase):

    def setUp(self):
        self.model = P1203Pa([])

    def expected_mos(self, a2, a3, bitrate):
        qcod_a = 100.0 * math.exp(a2 * bitrate) + a3
        qa = 100.0 - qcod_a

        # Reproduce the upstream MOS conversion.
        return self.model.audio_model_function(
            "aaclc",
            bitrate
        )

    def test_aaclc_128(self):
        result = self.model.audio_model_function(
            "aaclc",
            128.0
        )

        self.assertGreaterEqual(result, 1.0)
        self.assertLessEqual(result, 5.0)

    def test_aaclc_64(self):
        result = self.model.audio_model_function(
            "aaclc",
            64.0
        )

        self.assertGreaterEqual(result, 1.0)
        self.assertLessEqual(result, 5.0)

    def test_aaclc_32(self):
        result = self.model.audio_model_function(
            "aaclc",
            32.0
        )

        self.assertGreaterEqual(result, 1.0)
        self.assertLessEqual(result, 5.0)

    def test_higher_bitrate_does_not_reduce_quality(self):
        low = self.model.audio_model_function("aaclc", 32.0)
        high = self.model.audio_model_function("aaclc", 128.0)

        self.assertGreaterEqual(high, low)


if __name__ == "__main__":
    unittest.main()