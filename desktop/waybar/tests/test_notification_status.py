"""通知数量的离线测试，不连接 D-Bus、不触碰真实通知和历史。"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SPEC = importlib.util.spec_from_file_location("waybar_notification_status", SCRIPTS / "notification-status.py")
status = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC.loader.exec_module(status)
finally:
    sys.path.pop(0)


class FakeMako:
    def __init__(self, current=(), archived=(), modes=()):
        self.current, self.archived, self.current_modes = current, archived, modes
        self.calls = []

    def modes(self):
        self.calls.append("modes")
        return self.current_modes

    def notifications(self):
        self.calls.append("notifications")
        return self.current

    def history(self):
        self.calls.append("history")
        return self.archived


class NotificationStatusTests(unittest.TestCase):
    def test_normal_counts_current_and_history_using_read_only_calls(self):
        client = FakeMako([{"id": 1}, {"id": 2}], [{"id": 3}])
        output = status.render_status(client)
        self.assertEqual(output["text"], "N:3")
        self.assertIn("当前：2 · 历史：1", output["tooltip"])
        self.assertIn("非未读数", output["tooltip"])
        self.assertIn("勿扰：已关闭", output["tooltip"])
        self.assertIn("左键：开启勿扰 · 右键：恢复一条历史通知", output["tooltip"])
        self.assertIn("中键：清理菜单", output["tooltip"])
        self.assertNotIn("class", output)
        self.assertEqual(client.calls, ["modes", "notifications", "history"])
        self.assertEqual(json.loads(json.dumps(output)), output)

    def test_dnd_includes_archived_notifications_and_keeps_class(self):
        client = FakeMako(archived=[{"id": 4}, {"id": 5}], modes=["do-not-disturb"])
        output = status.render_status(client)
        self.assertEqual(output["text"], "Q:2")
        self.assertEqual(output["class"], "dnd")
        self.assertIn("当前：0 · 历史：2", output["tooltip"])
        self.assertIn("勿扰：已开启", output["tooltip"])
        self.assertIn("左键：关闭勿扰 · 右键：恢复一条历史通知", output["tooltip"])
        self.assertIn("中键：清理菜单", output["tooltip"])
        self.assertIn("手动查看不关闭勿扰", output["tooltip"])

    def test_empty_returns_zero(self):
        self.assertEqual(status.render_status(FakeMako())["text"], "N:0")

    def test_mode_change_updates_prefix_without_changing_count(self):
        client = FakeMako(current=[{"id": 1}], archived=[{"id": 2}])
        self.assertEqual(status.render_status(client)["text"], "N:2")
        client.current_modes = ["do-not-disturb"]
        self.assertEqual(status.render_status(client)["text"], "Q:2")
        client.current_modes = []
        self.assertEqual(status.render_status(client)["text"], "N:2")

    def test_duplicate_ids_within_and_between_lists_only_count_once(self):
        client = FakeMako([{"id": 1}, {"id": 1}, {"id": 2}], [{"id": 2}, {"id": 3}, {"id": 3}])
        output = status.render_status(client)
        self.assertEqual(output["text"], "N:3")
        self.assertIn("当前：2 · 历史：2", output["tooltip"])
        self.assertIn("含历史记录", output["tooltip"])

    def test_service_failure_and_connection_failure_return_placeholder(self):
        self.assertEqual(status.unavailable()["text"], "N:--")
        class BusError(Exception):
            pass

        for error in (BusError("unavailable"), ImportError("gi"), OSError("no session bus")):
            with self.subTest(error=error):
                def unavailable_client():
                    raise error
                self.assertEqual(status.read_status(unavailable_client, (BusError,)), status.unavailable())

        class FailingMako(FakeMako):
            def history(self):
                raise BusError("daemon stopped")

        self.assertEqual(status.read_status(FailingMako, (BusError,)), status.unavailable())

    def test_bad_ids_fail_closed(self):
        for ident in (True, 0, -1, "7", 0x100000000, None):
            with self.subTest(ident=ident):
                client = FakeMako(current=[{"id": ident}])
                self.assertEqual(status.read_status(lambda: client), status.unavailable())

    def test_status_shell_falls_back_quietly_without_desktop_access(self):
        with tempfile.TemporaryDirectory(prefix="waybar-notification-test-") as directory:
            python = Path(directory) / "python3"
            python.write_text("#!/bin/sh\nprintf 'simulated failure' >&2\nexit 17\n")
            python.chmod(0o755)
            result = subprocess.run(
                [str(SCRIPTS / "notification.sh"), "status"],
                env=dict(os.environ, PATH=f"{directory}:{os.environ['PATH']}"),
                capture_output=True, text=True, timeout=5,
            )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), status.unavailable())

    def test_dnd_and_history_hold_the_shared_history_lock(self):
        with tempfile.TemporaryDirectory(prefix="waybar-notification-lock-test-") as directory:
            runtime = Path(directory)
            helper = f"#!{sys.executable}\n" + '''
import fcntl, json, os, sys
from pathlib import Path
with (Path(os.environ["XDG_RUNTIME_DIR"]) / "waybar/history.lock").open("a") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = False
    except BlockingIOError:
        locked = True
with open(os.environ["WB_TEST_ACTION_LOG"], "a") as log:
    log.write(json.dumps({"command": Path(sys.argv[0]).name, "args": sys.argv[1:],
                          "locked": locked}) + "\\n")
'''
            for command in ("python3", "makoctl"):
                path = runtime / command
                path.write_text(helper)
                path.chmod(0o755)
            env = dict(os.environ, XDG_RUNTIME_DIR=directory,
                       PATH=f"{directory}:{os.environ['PATH']}",
                       WB_TEST_ACTION_LOG=str(runtime / "actions.log"))
            for action in ("dnd", "history"):
                result = subprocess.run([str(SCRIPTS / "notification.sh"), action], env=env,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
            calls = [json.loads(line) for line in (runtime / "actions.log").read_text().splitlines()]
        self.assertEqual([call["command"] for call in calls], ["makoctl", "python3"])
        self.assertEqual(calls[0]["args"], ["mode", "-t", "do-not-disturb"])
        self.assertEqual(calls[1]["args"], [str(SCRIPTS / "history.py")])
        self.assertTrue(all(call["locked"] for call in calls))
