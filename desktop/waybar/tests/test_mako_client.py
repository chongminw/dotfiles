"""D-Bus 协议边界测试：全部使用替身总线，不连接真实桌面。"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    import mako_client
finally:
    sys.path.pop(0)


class Variant:
    def __init__(self, signature, value):
        self.signature, self.value = signature, value

    def unpack(self):
        return self.value


class MakoClientTests(unittest.TestCase):
    def setUp(self):
        self.bus = Mock()
        self.bus.call_sync.return_value = Variant("(s)", (":1.42",))
        gio = SimpleNamespace(
            BusType=SimpleNamespace(SESSION=2), DBusCallFlags=SimpleNamespace(NONE=0),
            bus_get_sync=Mock(return_value=self.bus),
        )
        glib = SimpleNamespace(Variant=Variant, VariantType=SimpleNamespace(new=lambda value: value))
        modules = {
            "gi": SimpleNamespace(require_version=Mock()),
            "gi.repository": SimpleNamespace(Gio=gio, GLib=glib),
        }
        with patch.dict(sys.modules, modules):
            self.client = mako_client.MakoClient()

    def test_queries_and_restore_are_pinned_to_original_owner_with_timeouts(self):
        owner_call = self.bus.call_sync.call_args.args
        self.assertEqual(owner_call[3], "GetNameOwner")
        self.assertEqual(owner_call[4].value, ("org.freedesktop.Notifications",))
        self.bus.call_sync.side_effect = [
            Variant("(as)", (["do-not-disturb"],)),
            Variant("(aa{sv})", ([{"id": 1}],)),
            Variant("(aa{sv})", ([{"id": 2}],)),
            Variant("()", ()),
        ]
        self.assertEqual(self.client.modes(), ["do-not-disturb"])
        self.assertEqual(self.client.history(), [{"id": 1}])
        self.assertEqual(self.client.notifications(), [{"id": 2}])
        self.client.restore()
        calls = self.bus.call_sync.call_args_list
        self.assertEqual([call.args[3] for call in calls[1:]],
                         ["ListModes", "ListHistory", "ListNotifications", "RestoreNotification"])
        for call in calls[1:]:
            self.assertEqual(call.args[:3], (":1.42", "/fr/emersion/Mako", "fr.emersion.Mako"))
        for call in calls:
            self.assertEqual(call.args[7], 1000)

    def test_show_preserves_id_actions_and_typed_hints(self):
        self.bus.call_sync.return_value = Variant("(u)", (7,))
        fields = ("Example", 7, "", "标题", "正文", ["default", "打开"],
                  {"category": "waybar.manual-history", "desktop-entry": "example", "urgency": 2}, 0)
        self.assertEqual(self.client.show(fields), 7)
        call = self.bus.call_sync.call_args.args
        self.assertEqual(call[:4], (":1.42", "/org/freedesktop/Notifications",
                                   "org.freedesktop.Notifications", "Notify"))
        parameters = call[4]
        self.assertEqual(parameters.signature, "(susssasa{sv}i)")
        self.assertEqual(parameters.value[:6], fields[:6])
        self.assertEqual(parameters.value[6]["urgency"].signature, "y")
        self.assertEqual(parameters.value[6]["urgency"].value, 2)
        self.assertEqual(parameters.value[6]["category"].signature, "s")
        self.assertEqual(parameters.value[6]["category"].value, "waybar.manual-history")
        self.assertEqual(parameters.value[7], 0)

    def test_set_modes_and_dismiss_use_typed_single_id_without_archiving(self):
        self.bus.call_sync.return_value = Variant("()", ())
        self.client.set_modes(["do-not-disturb", "waybar-cleanup"])
        parameters = self.bus.call_sync.call_args.args[4]
        self.assertEqual(parameters.signature, "(as)")
        self.assertEqual(parameters.value, (["do-not-disturb", "waybar-cleanup"],))
        self.client.dismiss(7)
        call = self.bus.call_sync.call_args.args
        self.assertEqual(call[:4], (":1.42", "/fr/emersion/Mako", "fr.emersion.Mako", "DismissNotifications"))
        self.assertEqual(call[4].signature, "(a{sv})")
        options = call[4].value[0]
        self.assertEqual(set(options), {"id", "history"})
        self.assertEqual((options["id"].signature, options["id"].value), ("u", 7))
        self.assertEqual((options["history"].signature, options["history"].value), ("b", False))
        with self.assertRaises(ValueError):
            self.client.dismiss(True)

    def test_owner_change_is_rejected_without_rebinding_client(self):
        self.bus.call_sync.return_value = Variant("(s)", (":1.43",))
        with self.assertRaises(mako_client.MakoOwnerChanged):
            self.client.assert_owner()
        self.assertEqual(self.client.owner, ":1.42")
