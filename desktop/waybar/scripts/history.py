#!/usr/bin/env python3
"""mako 勿扰兼容层：原生恢复一条，再按原 ID 显示，绝不切换全局勿扰。"""

# 保留协议常量和 MakoClient 导出，兼容已有隔离桌面检查入口。
from mako_client import (
    BUS_NAME, MAKO_PATH, MAKO_INTERFACE, NOTIFICATION_PATH, NOTIFICATION_INTERFACE,
    DND_MODE, MakoClient, RECOVERABLE_ERRORS, notification_id,
)

HISTORY_CATEGORY = "waybar.manual-history"


def replacement_fields(record):
    """复制公开历史字段，不把通知文本解释为 Shell，也不添加同步 tag。"""
    ident = notification_id(record)
    values = [record.get(key, "") for key in ("app-name", "app-icon", "summary", "body", "desktop-entry")]
    if not all(isinstance(value, str) for value in values):
        raise ValueError("invalid text")
    actions = record.get("actions", {})
    if not isinstance(actions, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in actions.items()
    ):
        raise ValueError("invalid actions")
    urgency = record.get("urgency", 1)
    if isinstance(urgency, bool) or not isinstance(urgency, int) or urgency not in (0, 1, 2):
        urgency = 1
    app_name, app_icon, summary, body, desktop_entry = values
    return (app_name, ident, app_icon, summary, body,
            [field for pair in actions.items() for field in pair],
            {"category": HISTORY_CATEGORY, "desktop-entry": desktop_entry, "urgency": urgency}, 0)


def restore_one(client):
    """业务层只依赖窄接口，便于替换为离线测试替身。"""
    if DND_MODE not in client.modes():
        client.restore()
        return
    history = client.history()
    if not history:
        return
    record = history[0]
    # 在改变历史前先校验，避免坏数据被移出历史却不能显示。
    replacement_fields(record)
    client.restore()
    active = next((item for item in client.notifications() if item["id"] == record["id"]), None)
    if active is not None:
        client.show(replacement_fields(active))


def main():
    try:
        from gi.repository import GLib
    except ImportError:
        return
    try:
        restore_one(MakoClient())
    except (GLib.Error, *RECOVERABLE_ERRORS):
        # 连接失败与异常数据安静降级；不捕获无关的编程错误。
        return


if __name__ == "__main__":
    main()
