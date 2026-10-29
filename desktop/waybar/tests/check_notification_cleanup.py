"""在独立 D-Bus 和 mako 中验证通知删除，绝不连接默认桌面通知服务。"""

import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from mako_client import (
    BUS_NAME, DND_MODE, MAKO_INTERFACE, MAKO_PATH, NOTIFICATION_INTERFACE,
    NOTIFICATION_PATH, MakoClient, notification_id,
)
from gi.repository import GLib

CLEANUP = ROOT / 'scripts/notification-cleanup.py'
CLEANUP_MODE = 'waybar-cleanup'


def ids(records):
    return {notification_id(record) for record in records}


def wait_for(predicate, description):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except GLib.Error:
            pass
        time.sleep(0.025)
    raise AssertionError(description)


def private_config():
    lines = (ROOT.parent / 'mako/config').read_text().splitlines()
    first_rule = next((i for i, line in enumerate(lines) if line.lstrip().startswith('[')), len(lines))
    lines[first_rule:first_rule] = ['# 隔离测试全局隐藏，不显示测试弹窗。', 'invisible=1', '']
    return '\n'.join(lines) + '\n'


@contextlib.contextmanager
def server():
    runtime = os.environ['XDG_RUNTIME_DIR']
    display = os.environ['WAYLAND_DISPLAY']
    if not display.startswith('/'):
        display = str(Path(runtime) / display)
    with tempfile.TemporaryDirectory(prefix='waybar-cleanup-check-') as directory:
        config = Path(directory) / 'mako.conf'
        config.write_text(private_config())
        env = dict(os.environ, XDG_RUNTIME_DIR=directory, WAYLAND_DISPLAY=display)
        daemon = subprocess.Popen(
            ['/usr/bin/mako', '--config', str(config)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            client = None

            def ready():
                nonlocal client
                if daemon.poll() is not None:
                    raise AssertionError('私有 mako 启动失败')
                candidate = MakoClient()
                pid = candidate.bus.call_sync(
                    'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                    'GetConnectionUnixProcessID', GLib.Variant('(s)', (candidate.owner,)),
                    None, candidate.gio.DBusCallFlags.NONE, 1000, None,
                ).unpack()[0]
                if pid != daemon.pid:
                    return False
                client = candidate
                return True

            # GetNameOwner 不会自动激活另一个通知守护进程。
            wait_for(ready, '私有通知服务未取得独立身份')
            assert client is not None
            yield client, env, Path(directory)
            assert daemon.poll() is None, '隔离 mako 意外退出'
        finally:
            if daemon.poll() is None:
                daemon.terminate()
            try:
                stdout, stderr = daemon.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                daemon.kill()
                stdout, stderr = daemon.communicate(timeout=2)
            if stderr.strip():
                print(stderr.strip(), file=sys.stderr)


def notify(client, label):
    parameters = GLib.Variant('(susssasa{sv}i)', (
        'Waybar Cleanup Isolated', 0, '', label, '仅用于隔离测试', [], {}, 0,
    ))
    return client.call(NOTIFICATION_PATH, NOTIFICATION_INTERFACE, 'Notify', parameters)[0]


def archive(client, ident):
    client.call(MAKO_PATH, MAKO_INTERFACE, 'DismissNotifications', GLib.Variant(
        '(a{sv})', ({'id': GLib.Variant('u', ident), 'history': GLib.Variant('b', True)},),
    ))


def snapshot(env, directory):
    path = directory / 'snapshot.json'
    path.touch(mode=0o600)
    result = subprocess.run(
        ['/usr/bin/python3', str(CLEANUP), 'snapshot', str(path)], env=env,
        capture_output=True, text=True, timeout=7, check=True,
    )
    assert len(result.stdout.strip().splitlines()) == 3
    record = json.loads(path.read_text())
    assert record['owner'].startswith(':')
    return path, record


def clear(env, scope, path, expected=0):
    result = subprocess.run(
        ['/usr/bin/python3', str(CLEANUP), 'clear', scope, str(path)], env=env,
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == expected, (scope, result.returncode, result.stdout, result.stderr)
    record = json.loads(result.stdout)
    assert record['complete'] is (expected == 0), record
    return record


def modes_preserved(client, expected):
    assert set(client.modes()) == set(expected), client.modes()
    assert CLEANUP_MODE not in client.modes()


def main():
    runtime = os.environ.get('XDG_RUNTIME_DIR', '')
    address = os.environ.get('DBUS_SESSION_BUS_ADDRESS', '')
    if (sys.argv[1:] != ['--isolated'] or not runtime or not address
            or f'unix:path={runtime}/bus' in address):
        raise SystemExit('必须使用 dbus-run-session -- python3 check_notification_cleanup.py --isolated')

    with server() as (client, env, directory):
        current, archived = notify(client, 'current'), notify(client, 'history')
        archive(client, archived)
        path, record = snapshot(env, directory)
        assert set(record['current']) == {current} and set(record['history']) == {archived}
        clear(env, 'current', path)
        assert not client.notifications() and ids(client.history()) == {archived}
        modes_preserved(client, ['default'])
        print('PASS current-only preserves history', flush=True)

    with server() as (client, env, directory):
        current = notify(client, 'current')
        archived = [notify(client, 'history-1'), notify(client, 'history-2')]
        for ident in archived:
            archive(client, ident)
        path, _ = snapshot(env, directory)
        clear(env, 'history', path)
        assert ids(client.notifications()) == {current} and not client.history()
        modes_preserved(client, ['default'])
        print('PASS history-only preserves current and removes private mode', flush=True)

    with server() as (client, env, directory):
        notify(client, 'current')
        archived = notify(client, 'history')
        archive(client, archived)
        client.set_modes(['fixture-mode', DND_MODE])
        path, _ = snapshot(env, directory)
        clear(env, 'all', path)
        assert not client.notifications() and not client.history()
        modes_preserved(client, ['fixture-mode', DND_MODE])
        print('PASS all clears snapshot while preserving DND and other modes', flush=True)

    with server() as (client, env, directory):
        path, _ = snapshot(env, directory)
        result = clear(env, 'all', path)
        assert result['deleted'] == 0
        modes_preserved(client, ['default'])
        print('PASS empty cleanup is a no-op', flush=True)

    with server() as (client, env, directory):
        notify(client, 'old')
        path, _ = snapshot(env, directory)
        incoming = notify(client, 'new after snapshot')
        clear(env, 'all', path)
        assert ids(client.notifications()) == {incoming} and not client.history()
        modes_preserved(client, ['default'])
        print('PASS new current notification survives cleanup', flush=True)

    with server() as (client, env, directory):
        old = notify(client, 'old history')
        archive(client, old)
        path, _ = snapshot(env, directory)
        incoming = notify(client, 'new history')
        archive(client, incoming)
        result = clear(env, 'history', path, expected=3)
        assert result['remaining'] >= 1
        assert ids(client.history()) == {old, incoming} and not client.notifications()
        modes_preserved(client, ['default'])
        print('PASS new history head stops cleanup without deleting it', flush=True)

    with server() as (client, env, directory):
        client.set_modes([DND_MODE, 'fixture-mode'])
        archived = notify(client, 'DND incoming')
        wait_for(lambda: archived in ids(client.history()), '勿扰通知未归档')
        path, _ = snapshot(env, directory)
        clear(env, 'history', path)
        assert not client.notifications() and not client.history()
        modes_preserved(client, [DND_MODE, 'fixture-mode'])
        print('PASS DND history cleanup keeps original mode', flush=True)

    with server() as (client, env, directory):
        current = notify(client, 'persistent current')
        archived = notify(client, 'reload history')
        archive(client, archived)
        subprocess.run(['/usr/bin/makoctl', 'reload'], env=env, check=True, timeout=5)
        assert ids(client.notifications()) == {current} and ids(client.history()) == {archived}
        modes_preserved(client, ['default'])
        print('PASS config reload preserves persistent current and history IDs', flush=True)

    print('真实 mako 隔离清理检查通过；未操作桌面通知。')


if __name__ == '__main__':
    main()
