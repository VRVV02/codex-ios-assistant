import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from iphone_cli.errors import IPhoneError
from iphone_cli.resolve import (
    Chat,
    _load_group_id,
    parse_contacts_output,
    resolve_message_compose_target,
)


class ContactParsingTests(unittest.TestCase):
    def test_parses_contacts_cli_output(self):
        output = """Jane Appleseed
  +15550101001

John Appleseed
  john@example.com
  +15550101002
"""
        contacts = parse_contacts_output(output)
        self.assertEqual([contact.name for contact in contacts], ["Jane Appleseed", "John Appleseed"])
        self.assertEqual(contacts[1].phones, ("+15550101002",))
        self.assertEqual(contacts[1].emails, ("john@example.com",))

    def test_no_results(self):
        self.assertEqual(parse_contacts_output("No contacts found.\n"), [])


class GroupComposeResolutionTests(unittest.TestCase):
    def test_exact_capitalization_selects_the_intended_group(self):
        chats = [
            Chat(2859, "best boys", "chat-old", ("+1", "+2"), True, "iMessage", ""),
            Chat(2929, "Best Boys", "chat-new", ("+1", "+2"), True, "iMessage", ""),
        ]
        group_id = "BF86E595-E17B-4D78-8178-49EE8B53C06C"
        with (
            patch("iphone_cli.resolve._load_chats", return_value=chats),
            patch("iphone_cli.resolve._load_group_id", return_value=group_id),
        ):
            target = resolve_message_compose_target("best boys")

        self.assertEqual(target.label, "best boys")
        self.assertEqual(target.group_id, group_id)
        self.assertTrue(target.is_group)

    def test_case_insensitive_duplicate_group_names_are_ambiguous(self):
        chats = [
            Chat(2859, "best boys", "chat-old", ("+1", "+2"), True, "iMessage", ""),
            Chat(2929, "Best Boys", "chat-new", ("+1", "+2"), True, "iMessage", ""),
        ]
        with patch("iphone_cli.resolve._load_chats", return_value=chats):
            with self.assertRaisesRegex(IPhoneError, "exact capitalization"):
                resolve_message_compose_target("BEST BOYS")

    def test_group_id_is_read_from_the_messages_chat_row(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "chat.db"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE chat (group_id TEXT)")
                connection.execute(
                    "INSERT INTO chat (ROWID, group_id) VALUES (?, ?)",
                    (2859, "bf86e595-e17b-4d78-8178-49ee8b53c06c"),
                )
            chat = Chat(2859, "best boys", "chat", (), True, "iMessage", "")
            with patch.dict(os.environ, {"IPHONE_MESSAGES_DB": str(database)}):
                group_id = _load_group_id(chat)

        self.assertEqual(group_id, "BF86E595-E17B-4D78-8178-49EE8B53C06C")


if __name__ == "__main__":
    unittest.main()
