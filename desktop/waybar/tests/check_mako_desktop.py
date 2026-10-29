"""只允许在隔离 D-Bus 中验证真实 mako；普通单元测试不会执行此文件。"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import history
from gi.repository import GLib


def run(*args, env=None):
    return subprocess.check_output(args, text=True, timeout=4, env=env).strip()


def wait_for(predicate):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("isolated desktop state timed out")


def main():
    runtime = os.environ["XDG_RUNTIME_DIR"]
    # 明确拒绝默认用户总线，避免测试通知或失败影响真实历史。
    if sys.argv[1:] != ["--isolated"] or f"unix:path={runtime}/bus" in os.environ.get("DBUS_SESSION_BUS_ADDRESS", ""):
        raise SystemExit("请使用 dbus-run-session -- python3 check_mako_desktop.py --isolated")
    with tempfile.TemporaryDirectory(prefix="waybar-mako-test-") as directory:
        wayland = os.environ["WAYLAND_DISPLAY"]
        if not wayland.startswith("/"):
            wayland = f"{runtime}/{wayland}"
        env = dict(os.environ, XDG_RUNTIME_DIR=directory, WAYLAND_DISPLAY=wayland)
        daemon = subprocess.Popen(["mako", "--config", str(ROOT.parent / "mako/config")],
                                  env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            client = None
            def ready():
                nonlocal client
                try:
                    client = history.MakoClient()
                    return True
                except GLib.Error:
                    return False
            # 不能用 makoctl 轮询启动，否则 D-Bus 自动激活会抢先启动另一个 daemon。
            wait_for(ready)
            owner_pid = client.bus.call_sync(
                "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
                "GetConnectionUnixProcessID", client.glib.Variant("(s)", (client.owner,)),
                None, client.gio.DBusCallFlags.NONE, 1000, None,
            ).unpack()[0]
            assert owner_pid == daemon.pid, "私有会话的服务进程身份不匹配"
            baseline = {item["namespace"] for item in json.loads(run("niri", "msg", "--json", "layers"))}
            run("makoctl", "mode", "-a", "do-not-disturb", env=env)
            def notify(label):
                parameters = client.glib.Variant("(susssasa{sv}i)", (
                    f"Waybar 隔离验证 {label}", 0, "", f"Waybar 勿扰验证 {label}",
                    "隔离会话测试，不影响现有通知历史。", [], {}, 10000))
                return client.call(history.NOTIFICATION_PATH, history.NOTIFICATION_INTERFACE, "Notify", parameters)[0]
            first, second = notify("A"), notify("B")
            wait_for(lambda: {first, second} <= {item["id"] for item in client.history()})
            assert not client.notifications(), "新通知没有被归档"
            run(str(ROOT / "scripts/notification.sh"), "history", env=env)
            assert {item["id"] for item in client.notifications()} == {second}
            assert client.notifications()[0]["category"] == history.HISTORY_CATEGORY
            wait_for(lambda: {item["namespace"] for item in json.loads(run("niri", "msg", "--json", "layers"))} != baseline)
            run(str(ROOT / "scripts/notification.sh"), "history", env=env)
            assert {item["id"] for item in client.notifications()} == {first, second}
            third = notify("C")
            wait_for(lambda: third in {item["id"] for item in client.history()})
            assert {item["id"] for item in client.notifications()} == {first, second}
            assert "do-not-disturb" in client.modes()
            assert daemon.poll() is None, "mako 意外退出"
            status = json.loads(run(str(ROOT / "scripts/notification.sh"), "status", env=env))
            assert status["class"] == "dnd"
            print("真实 mako 隔离测试通过：原生弹窗可见、逐条恢复、相同 ID、勿扰保持、新通知屏蔽、无崩溃")
        finally:
            daemon.terminate()
            stdout, stderr = daemon.communicate(timeout=4)
            if stderr.strip():
                print(stderr.strip(), file=sys.stderr)


if __name__ == "__main__":
    main()
