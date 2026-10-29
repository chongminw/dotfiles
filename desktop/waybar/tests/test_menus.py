"""真实进程/互斥锁、假 launcher/电源命令；无需桌面，绝不执行系统操作。"""

import concurrent.futures
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("launcher", "power", "notification")
# Repository trees keep commenu/{bin,lib} beside Waybar. Installed tests use
# the invoking user's package; every test copies it into a private HOME.
MENU_ROOT = Path(os.environ.get("COMMENU_TEST_ROOT", (
    ROOT.parent / "commenu/lib"
    if (ROOT.parent / "commenu/lib/menu-common.sh").is_file()
    else Path.home() / ".local/lib/commenu"
)))
MENU_BIN = Path(os.environ.get("COMMENU_TEST_BIN", (
    ROOT.parent / "commenu/bin/commenu"
    if (ROOT.parent / "commenu/bin/commenu").is_file()
    else Path.home() / ".local/bin/commenu"
)))


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="waybar-menu-test-")
        self.runtime = Path(self.temp.name)
        self.home = self.runtime / "home"
        shutil.copytree(MENU_ROOT, self.home / ".local/lib/commenu")
        self.public_command = self.home / ".local/bin/commenu"
        self.public_command.parent.mkdir(parents=True)
        shutil.copy2(MENU_BIN, self.public_command)
        fake_bin = self.runtime / "bin"
        fake_bin.mkdir()
        self.fake_bin = fake_bin
        # 只替代清理核心；-c 仅用于解析模拟结果，绝不连接真实通知服务。
        fake_python = fake_bin / "python3"
        fake_python.write_text(f"#!{sys.executable}\n" + '''
import fcntl, json, os, sys, time
from pathlib import Path
args = sys.argv[1:]
if args[0] == "-c":
    os.execv(sys.executable, [sys.executable, *args])
if Path(args[0]).name != "notification-cleanup.py":
    raise SystemExit(99)
action = args[1]
snapshot = Path(args[-1])
with (snapshot.parent / "history.lock").open("a") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = False
    except BlockingIOError:
        locked = True
event = {"action": action, "locked": locked, "snapshot": str(snapshot), "pid": os.getpid()}
if action == "snapshot":
    snapshot.write_text('{"owner": ":1.2", "current": [1, 2, 3], "history": [4, 5]}')
else:
    event.update(scope=args[2], snapshot_exists=snapshot.is_file())
with open(os.environ["WB_TEST_CLEANUP_LOG"], "a") as log:
    log.write(json.dumps(event) + "\\n")
if action == "clear" and os.environ.get("WB_TEST_CLEAR_WAIT"):
    time.sleep(30)
if action == "snapshot":
    code = int(os.environ.get("WB_TEST_SNAPSHOT_STATUS", "0"))
    if not code:
        print("清除当前通知 · 3\\n清空历史记录 · 9\\n全部清空 · 12")
else:
    code = int(os.environ.get("WB_TEST_CLEAR_STATUS", "0"))
    print(json.dumps({"deleted": 3, "remaining": int(bool(code)), "complete": not code,
                      "message": "仍有通知未清理，请重试" if code else "已清理"}))
raise SystemExit(code)
''')
        fake_python.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), XDG_RUNTIME_DIR=str(self.runtime),
                        XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_DATA_HOME=str(self.home / ".local/share"),
                        XDG_STATE_HOME=str(self.home / ".local/state"),
                        XDG_CACHE_HOME=str(self.home / ".cache"),
                        DBUS_SESSION_BUS_ADDRESS=f"unix:path={self.runtime}/no-session-bus",
                        PATH=f"{fake_bin}:{ROOT / 'tests/fixtures'}:{os.environ['PATH']}",
                        WB_TEST_MENU_LOG=str(self.runtime / "menus.log"),
                        WB_TEST_CLEANUP_LOG=str(self.runtime / "cleanup.log"),
                        WB_TEST_ACTION_LOG=str(self.runtime / "actions.log"))
        for key in list(self.env):
            if key in ("BASH_ENV", "ENV") or key.startswith("BASH_FUNC_"):
                del self.env[key]

    def tearDown(self):
        for kind in KINDS:
            pid = self.active_pid(kind)
            if pid:
                try:
                    os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        self.wait_for(lambda: not any(self.active_pid(kind) for kind in KINDS))
        self.temp.cleanup()

    def toggle(self, kind):
        command = ([str(ROOT / "scripts/notification-menu.sh")] if kind == "notification"
                   else [str(self.public_command), kind])
        result = subprocess.run(command, env=self.env,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def public(self, *arguments):
        result = subprocess.run([str(self.public_command), *arguments], env=self.env,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def active_pid(self, kind):
        try:
            pid, token = (self.runtime / "waybar" / f"{kind}.state").read_text().split()
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
            if fields[0] != "Z" and fields[2] == pid and fields[3] == pid and fields[19] == token:
                return int(pid)
        except (OSError, ValueError, IndexError):
            pass
        return None

    def log(self, name="menus.log"):
        path = self.runtime / name
        return path.read_text() if path.exists() else ""

    def cleanup_calls(self):
        return [json.loads(line) for line in self.log("cleanup.log").splitlines()]

    def assert_notification_files_removed(self):
        self.assertEqual(list((self.runtime / "waybar").glob("notification-*")), [])

    def wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.02)
        self.fail("condition timed out")

    def test_launcher_toggle(self):
        self.toggle("launcher")
        self.wait_for(lambda: "waybar-launcher" in self.log())
        self.assertIsNotNone(self.active_pid("launcher"))
        self.toggle("launcher")
        self.assertIsNone(self.active_pid("launcher"))

    def test_public_launcher_is_independent_and_preserves_arguments(self):
        self.assertFalse((self.home / ".config/waybar").exists())
        # Record actual argv boundaries, then use the existing fake menu.
        argument_log = self.runtime / "launcher-argv.json"
        self.env["MENU_ARGV_LOG"] = str(argument_log)
        self.env["MENU_FUZZEL_FIXTURE"] = str(ROOT / "tests/fixtures/fuzzel")
        recorder = self.fake_bin / "fuzzel"
        recorder.write_text(f"#!{sys.executable}\n" + '''
import json, os, pathlib, sys
pathlib.Path(os.environ["MENU_ARGV_LOG"]).write_text(json.dumps(sys.argv[1:]))
fixture = os.environ["MENU_FUZZEL_FIXTURE"]
os.execv(fixture, [fixture, *sys.argv[1:]])
''')
        recorder.chmod(0o755)
        self.public("launcher", "--prompt", "Select an app")
        self.wait_for(lambda: "waybar-launcher" in self.log())
        self.assertEqual(json.loads(argument_log.read_text()), [
            "--namespace", "waybar-launcher", "--terminal", "ghostty -e",
            "--prompt", "Select an app",
        ])
        self.assertFalse((self.home / ".config/waybar").exists())
        self.public("launcher")
        self.assertIsNone(self.active_pid("launcher"))

    def test_public_launcher_power_and_notification_share_menu_sessions(self):
        self.public("launcher")
        self.toggle("launcher")
        self.assertIsNone(self.active_pid("launcher"))
        self.toggle("power")
        self.public("launcher")
        self.assertIsNone(self.active_pid("power"))
        self.assertIsNotNone(self.active_pid("launcher"))
        self.toggle("notification")
        self.wait_for(lambda: "waybar-notification-menu" in self.log())
        self.assertIsNone(self.active_pid("launcher"))
        self.public("power")
        self.assertIsNone(self.active_pid("notification"))
        self.assert_notification_files_removed()
        self.toggle("power")
        self.assertFalse(any(self.active_pid(kind) for kind in KINDS))
        self.assertEqual(self.log("actions.log"), "")

    def test_public_help_and_invalid_arguments_do_not_start_menus(self):
        for arguments in ((), ("help",), ("-h",), ("--help",)):
            with self.subTest(arguments=arguments):
                result = self.public(*arguments)
                self.assertIn("launcher", result.stdout)
                self.assertIn("power", result.stdout)
        for arguments in (("unknown",), ("power", "extra"), ("--help", "extra")):
            with self.subTest(arguments=arguments):
                result = subprocess.run([str(self.public_command), *arguments], env=self.env,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2)
        self.assertFalse((self.runtime / "waybar").exists())
        self.assertEqual(self.log(), "")
        self.assertEqual(self.log("actions.log"), "")

    def test_rapid_even_clicks_leave_no_menu(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda _: self.toggle("launcher"), range(10)))
        self.assertIsNone(self.active_pid("launcher"))

    def test_reusing_controller_process_toggles_each_click(self):
        library = self.home / ".local/lib/commenu"
        result = subprocess.run(
            ["bash", "-c", 'source "$1"; for click in 1 2 3 4; do '
             'wb_menu_toggle launcher "$2" || exit; done', "waybar-menu-test",
             str(library / "menu-common.sh"),
             str(library / "toggle-launcher.sh")],
            env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(self.active_pid("launcher"))

    def test_switching_menu_closes_only_owned_session(self):
        self.toggle("launcher")
        self.toggle("power")
        self.wait_for(lambda: "waybar-power-menu" in self.log())
        self.assertIsNone(self.active_pid("launcher"))
        self.assertIsNotNone(self.active_pid("power"))
        self.toggle("launcher")
        self.assertIsNone(self.active_pid("power"))
        self.assertIsNotNone(self.active_pid("launcher"))

    def test_unmanaged_fuzzel_is_not_killed(self):
        external = subprocess.Popen(["fuzzel", "--namespace", "external-test"], env=self.env,
                                    start_new_session=True, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        try:
            self.toggle("launcher")
            self.toggle("launcher")
            self.assertIsNone(external.poll())
        finally:
            os.killpg(external.pid, signal.SIGTERM)
            external.wait(timeout=3)

    def test_power_menu_toggles_off_without_action(self):
        self.toggle("power")
        self.wait_for(lambda: "waybar-power-menu" in self.log())
        self.toggle("power")
        self.assertIsNone(self.active_pid("power"))
        self.assertEqual(self.log("actions.log"), "")

    def test_power_cancellation_and_invalid_selection_are_safe(self):
        for choice in ("ESC", "", "Cancel", "取消", "anything", "Confirm Reboot"):
            with self.subTest(choice=choice):
                self.env["WB_TEST_CHOICE"] = choice
                self.toggle("power")
                self.wait_for(lambda: self.active_pid("power") is None)
                self.assertEqual(self.log("actions.log"), "")

    def test_notification_choices_use_only_snapshot_scopes(self):
        choices = (("清除当前通知 · 3", "current"),
                   ("清空历史记录 · 9", "history"), ("全部清空 · 12", "all"))
        for count, (choice, scope) in enumerate(choices, start=1):
            with self.subTest(scope=scope):
                self.env["WB_TEST_CHOICE"] = choice
                self.toggle("notification")
                self.wait_for(lambda: self.active_pid("notification") is None)
                snapshot, clear = self.cleanup_calls()[-2:]
                self.assertEqual(snapshot["action"], "snapshot")
                self.assertEqual(clear["action"], "clear")
                self.assertEqual(clear["scope"], scope)
                self.assertEqual(clear["snapshot"], snapshot["snapshot"])
                self.assertTrue(clear["snapshot_exists"])
                self.assertTrue(snapshot["locked"])
                self.assertTrue(clear["locked"])
                self.assertEqual(self.log().splitlines(),
                                 ["--dmenu --only-match --namespace waybar-notification-menu "
                                  "--lines 3"] * count)
                self.assert_notification_files_removed()

    def test_notification_cancellation_and_invalid_selection_do_not_clear(self):
        for choice in ("ESC", "", "anything", "清除当前通知 · 999", "清空历史记录 · 3"):
            with self.subTest(choice=choice):
                self.env["WB_TEST_CHOICE"] = choice
                self.toggle("notification")
                self.wait_for(lambda: self.active_pid("notification") is None)
                self.assertTrue(all(call["action"] == "snapshot" for call in self.cleanup_calls()))
                self.assert_notification_files_removed()

    def test_notification_menu_releases_history_lock_and_switches_other_menus(self):
        self.toggle("notification")
        self.wait_for(lambda: "waybar-notification-menu" in self.log())
        with (self.runtime / "waybar/history.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.toggle("power")
        self.assertIsNone(self.active_pid("notification"))
        self.assert_notification_files_removed()
        self.assertIsNotNone(self.active_pid("power"))
        self.toggle("notification")
        self.assertIsNone(self.active_pid("power"))
        self.assertIsNotNone(self.active_pid("notification"))
        self.toggle("launcher")
        self.assertIsNone(self.active_pid("notification"))
        self.assert_notification_files_removed()

    def test_notification_entrypoint_toggles_the_shared_menu(self):
        result = subprocess.run([str(ROOT / "scripts/notification.sh"), "menu"],
                                env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.wait_for(lambda: "waybar-notification-menu" in self.log())
        self.toggle("notification")
        self.assertIsNone(self.active_pid("notification"))
        self.assert_notification_files_removed()

    def test_switching_menu_cancels_clear_and_releases_history_lock(self):
        self.env.update(WB_TEST_CHOICE="DEFAULT", WB_TEST_CLEAR_WAIT="1")
        self.toggle("notification")
        self.wait_for(lambda: any(call["action"] == "clear" for call in self.cleanup_calls()))
        clear_pid = self.cleanup_calls()[-1]["pid"]
        self.toggle("launcher")
        self.assertIsNone(self.active_pid("notification"))
        with (self.runtime / "waybar/history.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            fields = Path(f"/proc/{clear_pid}/stat").read_text().rsplit(") ", 1)[1].split()
        except FileNotFoundError:
            pass
        else:
            self.assertEqual(fields[0], "Z", "清理核心在菜单取消后仍然运行")
        self.assert_notification_files_removed()

    def test_notification_partial_and_failed_clear_use_menu_result(self):
        self.env["WB_TEST_CHOICE"] = "DEFAULT"
        for code in (3, 1):
            with self.subTest(code=code):
                self.env["WB_TEST_CLEAR_STATUS"] = str(code)
                self.toggle("notification")
                self.wait_for(lambda: self.active_pid("notification") is None)
                self.assertEqual(self.log().splitlines()[-1],
                                 "--dmenu --only-match --namespace waybar-notification-menu --lines 1")
                self.assertEqual(self.log("menus.log.items").splitlines()[-1], "仍有通知未清理，请重试")
                self.assert_notification_files_removed()

    def test_notification_snapshot_failure_never_clears(self):
        self.env.update(WB_TEST_CHOICE="DEFAULT", WB_TEST_SNAPSHOT_STATUS="1")
        self.toggle("notification")
        self.wait_for(lambda: self.active_pid("notification") is None)
        self.assertEqual([call["action"] for call in self.cleanup_calls()], ["snapshot"])
        self.assertEqual(self.log("menus.log.items"), "暂时无法读取通知，请稍后重试\n")
        self.assert_notification_files_removed()

    def test_single_menu_actions_reach_mock_commands(self):
        previous = ""
        actions = (("Reboot", "systemctl reboot"),
                   ("Shutdown", "systemctl poweroff"),
                   ("Logout", "niri msg action quit --skip-confirmation"),
                   ("DEFAULT", "niri msg action quit --skip-confirmation"))
        for count, (action, command) in enumerate(actions, start=1):
            with self.subTest(action=action):
                self.env["WB_TEST_CHOICE"] = action
                self.toggle("power")
                self.wait_for(lambda: self.active_pid("power") is None)
                previous += command + "\n"
                self.assertEqual(self.log("actions.log"), previous)
                # 仅缩小高度，宽度、留白、字体和提示符继续沿用原生配置。
                self.assertEqual(self.log().splitlines(),
                                 ["--dmenu --only-match --namespace waybar-power-menu "
                                  "--lines 3"] * count)
                self.assertEqual(self.log("menus.log.items"),
                                 "Logout\nReboot\nShutdown\n" * count)

    def test_stale_state_cannot_target_external_process(self):
        directory = self.runtime / "waybar"
        directory.mkdir()
        # 即便 PID 指向测试进程本身，错误的 starttime/会话身份也必须拒绝。
        (directory / "launcher.state").write_text(f"{os.getpid()} 0\n")
        self.toggle("launcher")
        self.assertIsNotNone(self.active_pid("launcher"))

    def test_worker_rejects_registration_with_wrong_start_time(self):
        directory = self.runtime / "waybar"
        directory.mkdir()
        worker = subprocess.Popen(
            [str(self.home / ".local/lib/commenu/toggle-launcher.sh"), "--run"], env=self.env,
            start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            (directory / "launcher.state").write_text(f"{worker.pid} 0\n")
            self.assertEqual(worker.wait(timeout=3), 1)
            self.assertEqual(self.log(), "")
        finally:
            if worker.poll() is None:
                os.killpg(worker.pid, signal.SIGTERM)
                worker.wait(timeout=3)
