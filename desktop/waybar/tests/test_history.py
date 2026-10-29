"""原生恢复与勿扰兼容规则的纯业务测试，不连接桌面。"""

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location("waybar_history", SCRIPTS / "history.py")
history = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC.loader.exec_module(history)
finally:
    sys.path.pop(0)


class FakeMako:
    def __init__(self, modes, records):
        self.current_modes, self.archived = modes, list(records)
        self.active, self.shown, self.restored = [], [], 0

    def modes(self): return self.current_modes
    def history(self): return self.archived
    def notifications(self): return self.active
    def restore(self):
        self.restored += 1
        if self.archived:
            self.active.append(self.archived.pop(0))
    def show(self, fields): self.shown.append(fields)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.record = {"id": 7, "app-name": "Example", "app-icon": "dialog-information",
                       "summary": "标题", "body": "<b>正文</b>", "urgency": 2,
                       "desktop-entry": "example", "actions": {"default": "打开"}}

    def test_normal_mode_only_uses_native_restore(self):
        client = FakeMako([], [self.record])
        history.restore_one(client)
        self.assertEqual(client.restored, 1)
        self.assertEqual(client.shown, [])

    def test_dnd_keeps_mode_and_id_and_copies_public_fields(self):
        client = FakeMako(["do-not-disturb"], [self.record])
        history.restore_one(client)
        fields = client.shown[0]
        self.assertEqual(fields[1], 7)
        self.assertEqual(fields[:6], ("Example", 7, "dialog-information", "标题", "<b>正文</b>", ["default", "打开"]))
        self.assertEqual(fields[6]["category"], history.HISTORY_CATEGORY)
        self.assertEqual(fields[6]["urgency"], 2)
        self.assertEqual(client.current_modes, ["do-not-disturb"])

    def test_repeated_clicks_restore_distinct_records(self):
        client = FakeMako(["do-not-disturb"], [self.record, dict(self.record, id=8)])
        history.restore_one(client)
        history.restore_one(client)
        self.assertEqual([fields[1] for fields in client.shown], [7, 8])

    def test_empty_history_is_noop(self):
        client = FakeMako(["do-not-disturb"], [])
        history.restore_one(client)
        self.assertEqual(client.restored, 0)

    def test_invalid_record_is_not_removed(self):
        for ident in (True, 0, -1, "7", 0x100000000):
            with self.subTest(ident=ident):
                client = FakeMako(["do-not-disturb"], [dict(self.record, id=ident)])
                with self.assertRaises(ValueError):
                    history.restore_one(client)
                self.assertEqual(client.restored, 0)

    def test_invalid_content_is_checked_before_removing_history(self):
        for changes in ({"summary": None}, {"actions": []}, {"actions": {"default": 7}}):
            with self.subTest(changes=changes):
                client = FakeMako(["do-not-disturb"], [dict(self.record, **changes)])
                with self.assertRaises(ValueError):
                    history.restore_one(client)
                self.assertEqual(client.restored, 0)

    def test_missing_restored_id_never_creates_a_new_notification(self):
        class MissingRestoredNotification(FakeMako):
            def notifications(self):
                return [dict(self.active[0], id=99)]

        client = MissingRestoredNotification(["do-not-disturb"], [self.record])
        history.restore_one(client)
        self.assertEqual(client.restored, 1)
        self.assertEqual(client.shown, [])
