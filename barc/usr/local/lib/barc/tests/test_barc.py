"""Core editing regression checks, isolated from real shell configuration.

Run: python3 -B -m unittest discover -s tests -v
Set BARC_TEST_ROOT to check an installed copy instead of this source tree.
"""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(os.environ.get("BARC_TEST_ROOT", Path(__file__).resolve().parents[1])).resolve()


class CoreEditingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="barc-core-test-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.config = self.home / "config/barc"
        self.editor_log = self.home / "editor.log"
        editor = self.home / "fake editor"
        editor.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$@" >> "$EDITOR_LOG"\n'
            'exit "${EDITOR_EXIT:-0}"\n', encoding="utf-8",
        )
        editor.chmod(0o755)
        self.env = {
            "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / "config"),
            "HISTFILE": "/dev/null", "TERM": "dumb", "NO_COLOR": "1",
            "PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
            "EDITOR": str(editor), "EDITOR_LOG": str(self.editor_log),
            "TEST_ROOT": str(ROOT), "TEST_CONFIG": str(self.config),
        }

    def config_file(self, name, content):
        self.config.mkdir(parents=True, exist_ok=True)
        (self.config / name).write_text(content, encoding="utf-8")

    def shell(self, code, **environment):
        result = subprocess.run(
            ["/usr/bin/bash", "--noprofile", "--norc", "-ic",
             'source "$TEST_ROOT/loader.bash"\n' + code],
            env={**self.env, **environment}, cwd=self.home,
            text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_default_modules_and_core_commands_load(self):
        result = self.shell('''
[[ $_BARC_STATE == loaded && $_BARC_ERRORS == 0 ]] || exit 10
[[ ${#_BARC_MODULE_ORDER[@]} == 9 ]] || exit 11
for name in "${_BARC_MODULE_ORDER[@]}"; do
    [[ ${_BARC_MODULE_STATUS[$name]} == loaded ]] || exit 12
done
declare -F ebrc barc barc_status >/dev/null || exit 13
barc status
''')
        self.assertIn("loaded (0 errors)", result.stdout)

    def test_editing_remains_available_with_aliases_disabled_or_empty_list(self):
        for selection in ("environment\n", ""):
            with self.subTest(selection=selection):
                self.config_file("modules.conf", selection)
                self.editor_log.unlink(missing_ok=True)
                self.shell('''
[[ ! ${_BARC_MODULE_STATUS[aliases]+present} ]] || exit 10
ebrc --help >/dev/null || exit 11
ebrc settings || exit 12
ebrc local || exit 13
ebrc modules || exit 14
''')
                self.assertEqual(self.editor_log.read_text().splitlines(), [
                    str(self.config / name)
                    for name in ("settings.bash", "local.bash", "modules.conf")
                ])
                self.assertEqual((self.config / "modules.conf").read_text(), selection)
                self.assertEqual(
                    (self.config / "settings.bash").read_bytes(),
                    (ROOT / "examples/settings.bash").read_bytes(),
                )

    def test_list_errors_do_not_remove_the_editing_command(self):
        for selection in ("../invalid\n", "missing-module\n"):
            with self.subTest(selection=selection):
                self.config_file("modules.conf", selection)
                self.editor_log.unlink(missing_ok=True)
                self.shell('''
[[ $_BARC_STATE == loaded_with_errors && $_BARC_ERRORS == 1 ]] || exit 10
ebrc modules || exit 11
''')
                self.assertEqual(self.editor_log.read_text().splitlines(),
                                 [str(self.config / "modules.conf")])
                self.assertEqual((self.config / "modules.conf").read_text(), selection)

    def test_first_module_edit_copies_defaults_and_preserves_later_edits(self):
        self.shell("ebrc modules || exit 10\n")
        self.assertEqual((self.config / "modules.conf").read_bytes(),
                         (ROOT / "defaults/modules.conf").read_bytes())
        chosen = "# my selection\nenvironment\n"
        self.config_file("modules.conf", chosen)
        self.shell("ebrc modules || exit 10\n")
        self.assertEqual((self.config / "modules.conf").read_text(), chosen)

    def test_help_and_invalid_arguments_do_not_create_configuration(self):
        self.shell('''
ebrc --help >/dev/null || exit 10
ebrc -h >/dev/null || exit 11
ebrc invalid >/dev/null 2>&1
[[ $? == 2 ]] || exit 12
ebrc settings extra >/dev/null 2>&1
[[ $? == 2 ]] || exit 13
''')
        self.assertFalse(self.config.exists())
        self.assertFalse(self.editor_log.exists())

    def test_default_target_and_editor_failure_are_preserved(self):
        self.config_file("modules.conf", "")
        result = self.shell('''
ebrc
[[ $? == 17 ]] || exit 10
''', EDITOR_EXIT="17")
        self.assertEqual(self.editor_log.read_text().splitlines(),
                         [str(self.config / "local.bash")])
        self.assertNotIn("open a new shell", result.stdout)

    def test_local_configuration_can_still_override_the_editing_command(self):
        self.config_file("modules.conf", "")
        self.config_file("local.bash", "ebrc() { printf 'personal editor\\n'; }\n")
        result = self.shell("ebrc\n")
        self.assertEqual(result.stdout, "personal editor\n")
        self.assertFalse(self.editor_log.exists())


if __name__ == "__main__":
    unittest.main()
