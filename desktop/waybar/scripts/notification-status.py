#!/usr/bin/env python3
"""只读统计 mako 通知；普通状态显示 N:，勿扰状态显示 Q:。"""

import json

from mako_client import DND_MODE, MakoClient, RECOVERABLE_ERRORS, notification_id


def unavailable():
    return {"text": "N:--", "tooltip": "mako · 服务不可用"}


def notification_ids(records):
    if not isinstance(records, (list, tuple)):
        raise ValueError("invalid notifications")
    return {notification_id(record) for record in records}


def quiet_enabled(client):
    modes = client.modes()
    if not isinstance(modes, (list, tuple)) or not all(isinstance(mode, str) for mode in modes):
        raise ValueError("invalid modes")
    return DND_MODE in modes


def render_status(client):
    """当前和历史按 ID 去重，勿扰自动归档后仍计入可查看总数。"""
    dnd = quiet_enabled(client)
    current = notification_ids(client.notifications())
    archived = notification_ids(client.history())
    total = len(current | archived)
    output = {
        "text": f"{'Q' if dnd else 'N'}:{total}",
        "tooltip": (
            f"可查看通知：{total}（含历史记录，非未读数量）\n"
            f"当前：{len(current)} · 历史：{len(archived)}\n"
            f"勿扰：{'已开启' if dnd else '已关闭'}\n"
            f"左键：{'关闭' if dnd else '开启'}勿扰 · 右键：恢复一条历史通知\n"
            "中键：清理菜单"
        ),
    }
    if dnd:
        output["class"] = "dnd"
        output["tooltip"] += "\n手动查看不关闭勿扰"
    return output


def read_status(client_factory, service_errors=()):
    try:
        return render_status(client_factory())
    except (*RECOVERABLE_ERRORS, *service_errors):
        return unavailable()


def main():
    try:
        from gi.repository import GLib
    except ImportError:
        output = unavailable()
    else:
        output = read_status(MakoClient, (GLib.Error,))
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
