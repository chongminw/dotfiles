"""mako 的 D-Bus 边界与通知 ID 校验；导入时不连接桌面。"""

BUS_NAME = "org.freedesktop.Notifications"
MAKO_PATH = "/fr/emersion/Mako"
MAKO_INTERFACE = "fr.emersion.Mako"
NOTIFICATION_PATH = "/org/freedesktop/Notifications"
NOTIFICATION_INTERFACE = "org.freedesktop.Notifications"
DND_MODE = "do-not-disturb"
DBUS_TIMEOUT_MS = 1000
RECOVERABLE_ERRORS = (ImportError, OSError, ValueError, KeyError, TypeError)


class MakoOwnerChanged(ValueError):
    """通知服务已切换，旧快照不能用于新服务。"""


def notification_id(record):
    """通知 ID 是非零 uint32，Python 的 bool 不视为有效 ID。"""
    ident = record["id"]
    if isinstance(ident, bool) or not isinstance(ident, int) or not 0 < ident <= 0xFFFFFFFF:
        raise ValueError("invalid notification ID")
    return ident


class MakoClient:
    """仅负责 D-Bus 协议；锁定守护进程身份，避免重启后误用旧 ID。"""

    def __init__(self):
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib
        self.gio, self.glib = Gio, GLib
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.owner = self.current_owner()

    def current_owner(self):
        return self.bus.call_sync(
            "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "GetNameOwner",
            self.glib.Variant("(s)", (BUS_NAME,)), self.glib.VariantType.new("(s)"),
            self.gio.DBusCallFlags.NONE, DBUS_TIMEOUT_MS, None,
        ).unpack()[0]

    def assert_owner(self):
        if self.current_owner() != self.owner:
            raise MakoOwnerChanged("notification service changed")

    def call(self, path, interface, method, parameters=None):
        return self.bus.call_sync(self.owner, path, interface, method, parameters, None,
                                  self.gio.DBusCallFlags.NONE, DBUS_TIMEOUT_MS, None).unpack()

    def modes(self):
        return self.call(MAKO_PATH, MAKO_INTERFACE, "ListModes")[0]

    def history(self):
        return self.call(MAKO_PATH, MAKO_INTERFACE, "ListHistory")[0]

    def notifications(self):
        return self.call(MAKO_PATH, MAKO_INTERFACE, "ListNotifications")[0]

    def restore(self):
        self.call(MAKO_PATH, MAKO_INTERFACE, "RestoreNotification")

    def set_modes(self, modes):
        self.call(MAKO_PATH, MAKO_INTERFACE, "SetModes", self.glib.Variant("(as)", (list(modes),)))

    def dismiss(self, ident):
        ident = notification_id({"id": ident})
        parameters = self.glib.Variant("(a{sv})", ({
            "id": self.glib.Variant("u", ident),
            "history": self.glib.Variant("b", False),
        },))
        self.call(MAKO_PATH, MAKO_INTERFACE, "DismissNotifications", parameters)

    def show(self, fields):
        hints = {key: self.glib.Variant("y" if key == "urgency" else "s", value)
                 for key, value in fields[6].items()}
        parameters = self.glib.Variant("(susssasa{sv}i)", (*fields[:6], hints, fields[7]))
        return self.call(NOTIFICATION_PATH, NOTIFICATION_INTERFACE, "Notify", parameters)[0]
