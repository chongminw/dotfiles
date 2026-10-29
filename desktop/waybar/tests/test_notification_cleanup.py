"""通知删除的离线业务及 CLI 测试；全部使用内存替身，不连接桌面。"""

import contextlib
import importlib.util
import io
import json
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location("waybar_notification_cleanup", SCRIPTS / "notification-cleanup.py")
cleanup = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC.loader.exec_module(cleanup)
finally:
    sys.path.pop(0)


class BusError(Exception):
    pass


class FakeMako:
    def __init__(self, current=(), history=(), modes=()):
        self.owner = self.live_owner = ":1.42"
        self.current, self.archived, self.current_modes = list(current), list(history), list(modes)
        self.deleted, self.restored, self.mode_changes = [], [], []
        self.on_restore = self.on_modes = self.on_dismiss = None

    def assert_owner(self):
        if self.owner != self.live_owner:
            raise cleanup.MakoOwnerChanged("owner changed")

    def notifications(self): return [{"id": ident} for ident in self.current]
    def history(self): return [{"id": ident} for ident in self.archived]
    def modes(self): return list(self.current_modes)

    def set_modes(self, modes):
        self.current_modes = list(modes)
        self.mode_changes.append(list(modes))
        if self.on_modes:
            self.on_modes()

    def restore(self):
        if self.on_restore:
            self.on_restore()
        if self.archived:
            ident = self.archived.pop(0)
            self.current.append(ident)
            self.restored.append(ident)

    def dismiss(self, ident):
        if self.on_dismiss:
            self.on_dismiss()
        if ident in self.current:
            self.current.remove(ident)
            self.deleted.append(ident)


class CleanupTests(unittest.TestCase):
    def clear(self, client, snapshot, scope="all", **kwargs):
        return cleanup.clear_snapshot(client, snapshot, scope, service_errors=(BusError,), **kwargs)

    def test_snapshot_is_read_only_and_menu_counts_deduplicate(self):
        client = FakeMako([1, 2, 2], [2, 3, 3])
        snapshot = cleanup.make_snapshot(client)
        self.assertEqual(snapshot, {"owner": ":1.42", "current": [1, 2], "history": [2, 3]})
        self.assertEqual(cleanup.menu_lines(snapshot), ["清除当前通知 · 2", "清空历史记录 · 2", "全部清空 · 3"])
        self.assertEqual((client.deleted, client.restored, client.mode_changes), ([], [], []))

    def test_each_scope_only_deletes_its_initial_ids(self):
        for scope, expected in (("current", {1}), ("history", {2}), ("all", {1, 2})):
            with self.subTest(scope=scope):
                client = FakeMako([1], [2])
                snapshot = cleanup.make_snapshot(client)
                client.current.append(99)
                result, code = self.clear(client, snapshot, scope)
                self.assertEqual(code, 0)
                self.assertTrue(result["complete"])
                self.assertEqual(result["deleted"], len(expected))
                self.assertEqual(set(client.deleted), expected)
                self.assertIn(99, client.current)

    def test_empty_and_already_absent_ids_are_success_without_writes(self):
        for current in ([], [1]):
            with self.subTest(current=current):
                client = FakeMako(current)
                snapshot = cleanup.make_snapshot(client)
                client.current.clear()
                result, code = self.clear(client, snapshot)
                self.assertEqual((code, result["deleted"], result["remaining"], result["complete"]), (0, 0, 0, True))
                self.assertEqual((client.deleted, client.restored, client.mode_changes), ([], [], []))

    def test_targets_can_move_between_current_and_history_since_snapshot(self):
        for scope in ("current", "history"):
            with self.subTest(scope=scope):
                client = FakeMako([1] if scope == "current" else [], [1] if scope == "history" else [])
                snapshot = cleanup.make_snapshot(client)
                client.current, client.archived = client.archived, client.current
                result, code = self.clear(client, snapshot, scope)
                self.assertEqual((code, result["deleted"], result["complete"]), (0, 1, True))

    def test_new_history_top_blocks_cleanup_without_restoring_or_deleting_it(self):
        client = FakeMako(history=[1, 2])
        snapshot = cleanup.make_snapshot(client)
        client.archived.insert(0, 99)
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["remaining"], result["complete"]), (3, 2, False))
        self.assertEqual(client.archived, [99, 1, 2])
        self.assertEqual((client.deleted, client.restored, client.mode_changes), ([], [], []))

    def test_partial_current_progress_is_reported_when_new_history_blocks(self):
        client = FakeMako([1], [2])
        snapshot = cleanup.make_snapshot(client)
        client.archived.insert(0, 99)
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["deleted"], result["remaining"]), (3, 1, 1))
        self.assertEqual(client.archived, [99, 2])

    def test_hidden_mode_preserves_dnd_and_other_modes(self):
        client = FakeMako(history=[1, 2], modes=["default", "do-not-disturb", "custom"])
        snapshot = cleanup.make_snapshot(client)

        def while_restoring():
            self.assertIn(cleanup.CLEANUP_MODE, client.current_modes)
            self.assertIn("do-not-disturb", client.current_modes)
            if "new-mode" not in client.current_modes:
                client.current_modes.append("new-mode")

        client.on_restore = while_restoring
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["deleted"]), (0, 2))
        self.assertEqual(client.current_modes, ["default", "do-not-disturb", "custom", "new-mode"])

    def test_preexisting_cleanup_mode_is_not_removed(self):
        client = FakeMako(history=[1], modes=["do-not-disturb", cleanup.CLEANUP_MODE])
        result, code = self.clear(client, cleanup.make_snapshot(client))
        self.assertEqual((code, result["complete"]), (0, True))
        self.assertEqual(client.mode_changes, [])
        self.assertIn(cleanup.CLEANUP_MODE, client.current_modes)

    def test_restore_race_preserves_unexpected_new_id_and_removes_owned_mode(self):
        client = FakeMako(history=[1])
        snapshot = cleanup.make_snapshot(client)
        client.on_restore = lambda: client.archived.insert(0, 99)
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["remaining"]), (3, 1))
        self.assertEqual(client.current, [99])
        self.assertEqual(client.archived, [1])
        self.assertEqual(client.deleted, [])
        self.assertNotIn(cleanup.CLEANUP_MODE, client.current_modes)

    def test_external_restore_then_new_restore_is_detected_even_if_expected_id_is_current(self):
        client = FakeMako(history=[1])
        snapshot = cleanup.make_snapshot(client)

        def concurrent_restore_and_arrival():
            client.archived.remove(1)
            client.current.append(1)
            client.archived.insert(0, 99)

        client.on_restore = concurrent_restore_and_arrival
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["remaining"], result["complete"]), (3, 1, False))
        self.assertEqual(client.deleted, [])
        self.assertEqual(client.current, [1, 99])
        self.assertNotIn(cleanup.CLEANUP_MODE, client.current_modes)

    def test_external_disappearance_is_not_counted_as_a_delete(self):
        client = FakeMako([1])
        snapshot = cleanup.make_snapshot(client)
        original = client.assert_owner
        checks = [0]

        def external_delete_before_first_mutation():
            original()
            checks[0] += 1
            if checks[0] == 2:
                client.current.clear()

        client.assert_owner = external_delete_before_first_mutation
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["deleted"], result["complete"]), (0, 0, True))
        self.assertEqual(client.deleted, [])

    def test_mode_add_timeout_still_attempts_finally_removal(self):
        client = FakeMako(history=[1], modes=["do-not-disturb"])
        snapshot = cleanup.make_snapshot(client)

        def add_times_out():
            if cleanup.CLEANUP_MODE in client.current_modes:
                raise BusError("reply lost after mode was added")

        client.on_modes = add_times_out
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["complete"]), (3, False))
        self.assertEqual(client.current_modes, ["do-not-disturb"])
        self.assertEqual(client.archived, [1])

    def test_finally_failure_is_reported_with_precise_recovery_command(self):
        client = FakeMako(history=[1])
        snapshot = cleanup.make_snapshot(client)
        original = client.set_modes

        def fail_remove(modes):
            if cleanup.CLEANUP_MODE not in modes:
                raise BusError("cannot remove mode")
            original(modes)

        client.set_modes = fail_remove
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["deleted"], result["complete"]), (3, 1, False))
        self.assertIn("makoctl mode -r waybar-cleanup", result["message"])

    def test_snapshot_owner_change_rejects_all_writes(self):
        client = FakeMako([1], [2])
        snapshot = cleanup.make_snapshot(client)
        client.owner = client.live_owner = ":1.43"
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["complete"]), (1, False))
        self.assertEqual((client.deleted, client.restored, client.mode_changes), ([], [], []))

    def test_service_owner_change_during_restore_stops_delete_and_cleans_original_mode(self):
        client = FakeMako(history=[1], modes=["do-not-disturb"])
        snapshot = cleanup.make_snapshot(client)
        client.on_restore = lambda: setattr(client, "live_owner", ":1.43")
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["complete"]), (3, False))
        self.assertEqual(client.deleted, [])
        self.assertEqual(client.current, [1])
        self.assertEqual(client.current_modes, ["do-not-disturb"])

    def test_timeout_after_hiding_still_restores_modes_without_restoring_notifications(self):
        client = FakeMako(history=[1], modes=["do-not-disturb"])
        snapshot = cleanup.make_snapshot(client)
        now = [0]
        client.on_modes = lambda: now.__setitem__(0, 20)
        result, code = self.clear(client, snapshot, clock=lambda: now[0], budget=1)
        self.assertEqual((code, result["remaining"]), (3, 1))
        self.assertEqual(client.restored, [])
        self.assertEqual(client.current_modes, ["do-not-disturb"])

    def test_nonprogress_is_bounded(self):
        client = FakeMako([1])
        snapshot = cleanup.make_snapshot(client)
        calls = []
        client.dismiss = lambda ident: calls.append(ident)
        result, code = self.clear(client, snapshot)
        self.assertEqual((code, result["remaining"]), (3, 1))
        self.assertEqual(len(calls), 4)

    def test_invalid_snapshot_cannot_trigger_writes(self):
        client = FakeMako([1])
        with self.assertRaises(ValueError):
            self.clear(client, {"owner": client.owner, "current": [True], "history": []})
        self.assertEqual(client.deleted, [])

    def test_snapshot_file_is_private_and_symlinks_are_rejected(self):
        snapshot = {"owner": ":1.42", "current": [1], "history": []}
        with tempfile.TemporaryDirectory(prefix="waybar-cleanup-test-") as directory:
            path = Path(directory) / "snapshot"
            path.touch(mode=0o600)
            cleanup.write_snapshot(path, snapshot)
            self.assertEqual(cleanup.read_snapshot(path), snapshot)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            link = Path(directory) / "symlink"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                cleanup.write_snapshot(link, snapshot)

    def test_cli_term_sets_cancel_flag_and_finally_removes_hidden_mode(self):
        client = FakeMako(history=[1], modes=["do-not-disturb"])
        snapshot = cleanup.make_snapshot(client)
        repository = SimpleNamespace(GLib=SimpleNamespace(Error=BusError))
        fake_modules = {"gi": SimpleNamespace(repository=repository), "gi.repository": repository}
        previous_handler = signal.getsignal(signal.SIGTERM)

        def receive_term():
            if cleanup.CLEANUP_MODE in client.current_modes:
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)

        client.on_modes = receive_term
        with tempfile.TemporaryDirectory(prefix="waybar-cleanup-test-") as directory:
            path = Path(directory) / "snapshot"
            path.write_text(json.dumps(snapshot))
            stdout = io.StringIO()
            with patch.dict(sys.modules, fake_modules), patch.object(cleanup, "MakoClient", return_value=client):
                with contextlib.redirect_stdout(stdout):
                    code = cleanup.main(["clear", "history", str(path)])
        self.assertEqual(code, 3)
        self.assertFalse(json.loads(stdout.getvalue())["complete"])
        self.assertEqual(client.current_modes, ["do-not-disturb"])
        self.assertEqual(client.restored, [])
        self.assertIs(signal.getsignal(signal.SIGTERM), previous_handler)
