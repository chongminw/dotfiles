#!/usr/bin/env python3
"""按打开菜单时的 ID 快照删除通知，不追赶新通知，不切换勿扰。"""

import json
import os
import signal
import stat
import sys
import time

from mako_client import MakoClient, MakoOwnerChanged, RECOVERABLE_ERRORS, notification_id

CLEANUP_MODE = "waybar-cleanup"
CLEANUP_BUDGET_SECONDS = 8
MAX_SNAPSHOT_BYTES = 1024 * 1024


class CleanupStopped(Exception):
    """预算或并发状态要求停止；保留尚未确认的通知。"""


def record_ids(records):
    if not isinstance(records, (list, tuple)):
        raise ValueError("invalid notifications")
    return [notification_id(record) for record in records]


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        raise ValueError("invalid snapshot")
    owner = snapshot.get("owner")
    if not isinstance(owner, str) or not owner.startswith(":"):
        raise ValueError("invalid owner")
    for name in ("current", "history"):
        values = snapshot.get(name)
        if not isinstance(values, list):
            raise ValueError("invalid notification IDs")
        for ident in values:
            notification_id({"id": ident})
    return snapshot


def make_snapshot(client):
    client.assert_owner()
    snapshot = {
        "owner": client.owner,
        "current": sorted(set(record_ids(client.notifications()))),
        "history": sorted(set(record_ids(client.history()))),
    }
    client.assert_owner()
    return snapshot


def menu_lines(snapshot):
    current, history = set(snapshot["current"]), set(snapshot["history"])
    return [f"清除当前通知 · {len(current)}", f"清空历史记录 · {len(history)}",
            f"全部清空 · {len(current | history)}"]


def modes(client):
    values = client.modes()
    if not isinstance(values, (list, tuple)) or not all(isinstance(value, str) for value in values):
        raise ValueError("invalid modes")
    return list(values)


def clear_snapshot(client, snapshot, scope, *, budget=CLEANUP_BUDGET_SECONDS,
                   clock=time.monotonic, cancelled=lambda: False, service_errors=()):
    """返回 (JSON 结果, 退出码)；调用者须持有与历史恢复共用的锁。"""
    validate_snapshot(snapshot)
    if scope not in ("current", "history", "all"):
        raise ValueError("invalid scope")
    targets = set(snapshot["current"] if scope == "current" else snapshot["history"])
    if scope == "all":
        targets |= set(snapshot["current"])
    expected_owner = snapshot["owner"]
    deadline = clock() + budget
    errors = (*RECOVERABLE_ERRORS, *service_errors)
    pending, initially_present = set(targets), set(targets)
    dismissed = set()
    mode_owned = False
    started = False
    reason = ""
    exit_code = 0
    verified = False

    def assert_owner():
        if client.owner != expected_owner:
            raise MakoOwnerChanged("snapshot owner changed")
        client.assert_owner()

    def checkpoint():
        if cancelled():
            raise CleanupStopped("清理已取消。")
        if clock() >= deadline:
            raise CleanupStopped("处理超时，请重新打开菜单重试。")
        assert_owner()

    try:
        checkpoint()
        current = set(record_ids(client.notifications()))
        archived = record_ids(client.history())
        initially_present = targets & (current | set(archived))
        pending = set(initially_present)
        # 每轮最多处理一个 ID，反复状态变化也不会形成无限循环。
        for _ in range(3 * len(initially_present) + 1):
            checkpoint()
            current = set(record_ids(client.notifications()))
            archived = record_ids(client.history())
            pending = initially_present & (current | set(archived))
            if not pending:
                verified = True
                break
            active_targets = current & pending
            if active_targets:
                checkpoint()
                started = True
                ident = min(active_targets)
                client.dismiss(ident)
                dismissed.add(ident)
                continue
            if not archived or archived[0] not in pending:
                raise CleanupStopped("新的历史通知位于前方，已保留它；请重新打开菜单重试。")
            if not mode_owned:
                checkpoint()
                existing_modes = modes(client)
                if CLEANUP_MODE not in existing_modes:
                    # 先登记清理责任：调用超时也可能已经成功添加 mode。
                    mode_owned = True
                    started = True
                    client.set_modes([*existing_modes, CLEANUP_MODE])
            checkpoint()
            archived = record_ids(client.history())
            if not archived or archived[0] not in pending:
                raise CleanupStopped("历史顺序发生变化，已停止并保留未确认的通知。")
            ident = archived[0]
            before_history = set(archived)
            before_current = set(record_ids(client.notifications()))
            if ident in before_current:
                raise CleanupStopped("通知已经被其他操作恢复，已停止并保留未确认的通知。")
            started = True
            client.restore()
            current = set(record_ids(client.notifications()))
            archived = set(record_ids(client.history()))
            if (current - before_current != {ident} or before_history - archived != {ident}
                    or ident in archived):
                raise CleanupStopped("恢复结果发生变化，已停止并保留未确认的通知。")
            # 完成已经开始的一次恢复；仍须核对服务身份，但不在中途丢弃该 ID。
            assert_owner()
            client.dismiss(ident)
            dismissed.add(ident)
        else:
            raise CleanupStopped("通知状态持续变化，请重新打开菜单重试。")
    except CleanupStopped as error:
        reason, exit_code = str(error), 3
    except MakoOwnerChanged:
        reason = "通知服务已重启，请重新打开菜单。"
        exit_code = 3 if started else 1
    except errors:
        reason = "通知服务不可用或数据异常。"
        exit_code = 3 if started else 1
    finally:
        if mode_owned:
            try:
                # 始终访问原 owner；重读后只移除本次添加的 mode，保留其余模式。
                if client.owner != expected_owner:
                    raise MakoOwnerChanged("client owner changed")
                existing_modes = modes(client)
                if CLEANUP_MODE in existing_modes:
                    client.set_modes([value for value in existing_modes if value != CLEANUP_MODE])
            except errors:
                reason += " 清理模式撤销失败，通知可能仍被隐藏；请运行 makoctl mode -r waybar-cleanup。"
                exit_code = 3 if started else 1
                verified = False

    # 用最后的只读状态核验结果；失败时使用保守的最后已知剩余数量。
    try:
        assert_owner()
        remaining = initially_present & (set(record_ids(client.notifications())) | set(record_ids(client.history())))
        pending = remaining
        if not remaining and not reason:
            verified = True
    except errors:
        verified = False
        if not reason:
            reason = "无法核验清理结果，请重新打开菜单。"
            exit_code = 3 if started else 1
    deleted = len(dismissed - pending)
    complete = verified and not pending and not reason
    if complete:
        message = f"已删除 {deleted} 条通知。" if deleted else "没有需要清理的通知。"
        exit_code = 0
    else:
        message = f"已删除 {deleted} 条，仍有 {len(pending)} 条未清理。{reason}"
        exit_code = exit_code or 3
    return {"deleted": deleted, "remaining": len(pending), "complete": complete, "message": message}, exit_code


def write_snapshot(path, snapshot):
    # 菜单传入已由 mktemp 创建的文件；拒绝符号链接和非当前用户文件。
    descriptor = os.open(path, os.O_WRONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("invalid snapshot file")
        os.fchmod(stream.fileno(), 0o600)
        stream.truncate(0)
        json.dump(snapshot, stream, ensure_ascii=False)
        stream.write("\n")


def read_snapshot(path):
    with open(path, encoding="utf-8") as stream:
        data = stream.read(MAX_SNAPSHOT_BYTES + 1)
    if len(data.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        raise ValueError("snapshot too large")
    return validate_snapshot(json.loads(data))


def main(arguments=None):
    arguments = sys.argv[1:] if arguments is None else arguments
    is_clear = len(arguments) == 3 and arguments[0] == "clear"
    is_snapshot = len(arguments) == 2 and arguments[0] == "snapshot"
    if not (is_clear or is_snapshot):
        return 1
    service_errors = ()
    try:
        from gi.repository import GLib
        service_errors = (GLib.Error,)
        client = MakoClient()
        if is_snapshot:
            snapshot = make_snapshot(client)
            write_snapshot(arguments[1], snapshot)
            print("\n".join(menu_lines(snapshot)))
            return 0
        snapshot = read_snapshot(arguments[2])
        interrupted = [False]

        def stop(_signum, _frame):
            interrupted[0] = True

        old_handlers = {number: signal.signal(number, stop) for number in (signal.SIGTERM, signal.SIGINT)}
        try:
            result, exit_code = clear_snapshot(client, snapshot, arguments[1],
                                               cancelled=lambda: interrupted[0], service_errors=service_errors)
        finally:
            for number, handler in old_handlers.items():
                signal.signal(number, handler)
        print(json.dumps(result, ensure_ascii=False))
        return exit_code
    except (*RECOVERABLE_ERRORS, *service_errors):
        if is_clear:
            print(json.dumps({"deleted": 0, "remaining": 0, "complete": False,
                              "message": "通知服务不可用或快照无效，请重新打开菜单。"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
