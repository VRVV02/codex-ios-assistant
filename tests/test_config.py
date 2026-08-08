import os
from unittest.mock import patch
import unittest

from iphone_cli.bridge import _correlation_id
from iphone_cli.config import command_prefix, receiver_admin_token, shortcut_receiver_url
from iphone_cli.errors import IPhoneError


class HardenedConfigTests(unittest.TestCase):
    def test_tailnet_receiver_origin_is_required(self):
        with patch.dict(
            os.environ,
            {"IPHONE_RECEIVER_URL": "https://mac.example-tailnet.ts.net"},
            clear=False,
        ):
            self.assertEqual(shortcut_receiver_url(), "https://mac.example-tailnet.ts.net")

        for value in (
            "https://receiver.example.com",
            "http://mac.example-tailnet.ts.net",
            "https://user@mac.example-tailnet.ts.net",
            "https://mac.example-tailnet.ts.net:443",
            "https://mac.example-tailnet.ts.net/path",
        ):
            with self.subTest(value=value), patch.dict(
                os.environ, {"IPHONE_RECEIVER_URL": value}, clear=False
            ), self.assertRaises(IPhoneError):
                shortcut_receiver_url()

    def test_admin_token_is_distinct_required_configuration(self):
        token = "a" * 40
        with patch.dict(os.environ, {"IPHONE_RECEIVER_ADMIN_TOKEN": token}, clear=False):
            self.assertEqual(receiver_admin_token(), token)
        with patch.dict(os.environ, {"IPHONE_RECEIVER_ADMIN_TOKEN": "short"}, clear=False):
            with self.assertRaises(IPhoneError):
                receiver_admin_token()

    def test_random_prefix_shape_and_128_bit_request_id(self):
        with patch.dict(os.environ, {"IPHONE_COMMAND_PREFIX": "ios_deadbeef"}, clear=False):
            self.assertEqual(command_prefix(), "ios_deadbeef")
        request_id = _correlation_id()
        self.assertRegex(request_id, r"^[0-9a-f]{32}$")


if __name__ == "__main__":
    unittest.main()
