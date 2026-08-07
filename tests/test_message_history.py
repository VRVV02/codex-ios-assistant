import unittest

from iphone_cli.errors import IPhoneError
from iphone_cli.message_history import parse_ndjson, run_message_read


class MessageHistoryTests(unittest.TestCase):
    def test_parse_ndjson_collects_records(self):
        self.assertEqual(parse_ndjson('{"id":1}\n{"id":2}\n'), [{"id": 1}, {"id": 2}])

    def test_parse_ndjson_rejects_invalid_output(self):
        with self.assertRaises(IPhoneError):
            parse_ndjson('{"id":1}\nnot-json\n')

    def test_unexposed_imsg_commands_are_rejected(self):
        for action in ("send", "read", "react", "edit", "unsend", "watch", "stats"):
            with self.subTest(action=action), self.assertRaises(IPhoneError):
                run_message_read(
                    action,
                    [],
                    dry_run=True,
                    json_output=False,
                    timeout=30,
                )


if __name__ == "__main__":
    unittest.main()
