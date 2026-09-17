import unittest

from itu_p1203 import P1203Pa
from itu_p1203.errors import P1203StandaloneError


class TestP12032Validation(unittest.TestCase):

    def setUp(self):
        self.model = P1203Pa([])

    def test_invalid_codec(self):

        with self.assertRaises(P1203StandaloneError):

            self.model.audio_model_function(
                "invalid_codec",
                128.0
            )


if __name__ == "__main__":
    unittest.main()