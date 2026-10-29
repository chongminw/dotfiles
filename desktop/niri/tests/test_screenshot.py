"""Offline screenshot workflow checks; all desktop commands are stand-ins."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/screenshot.sh"
IMAGE = b"test image\x00bytes\n"
STAND_IN = r'''#!/usr/bin/python3
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
record = {"name": name, "args": sys.argv[1:]}
status = 0
if name == "slurp":
    status = int(os.environ.get("SLURP_STATUS", "0"))
    sys.stdout.write(os.environ.get("REGION", "10,20 300x200\n") if status == 0 else "")
    sys.stderr.write(os.environ.get("SLURP_ERROR", ""))
elif name == "grim":
    image = pathlib.Path(sys.argv[-1])
    image.write_bytes(b"" if os.environ.get("EMPTY_IMAGE") else b"test image\x00bytes\n")
    record["mode"] = image.stat().st_mode & 0o777
    status = int(os.environ.get("GRIM_STATUS", "0"))
elif name == "wl-copy":
    pathlib.Path(os.environ["CLIPBOARD"]).write_bytes(sys.stdin.buffer.read())
    status = int(os.environ.get("CONSUMER_STATUS", "0"))
elif name == "satty":
    image = pathlib.Path(sys.argv[sys.argv.index("--filename") + 1])
    record["image_exists"] = image.is_file()
    record["image_hex"] = image.read_bytes().hex()
    status = int(os.environ.get("CONSUMER_STATUS", "0"))
with open(os.environ["CALLS"], "a") as output:
    output.write(json.dumps(record) + "\n")
sys.exit(status)
'''


class ScreenshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="niri-screenshot-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.runtime = self.root / "runtime with spaces"
        self.runtime.mkdir()
        self.calls = self.root / "calls.jsonl"
        self.clipboard = self.root / "clipboard"
        self.clipboard.write_bytes(b"existing clipboard")
        # A closed PATH prevents accidental calls to real desktop tools.
        for command in ("slurp", "grim", "satty", "wl-copy"):
            path = self.bin / command
            path.write_text(STAND_IN)
            path.chmod(0o755)
        for command in ("mktemp", "cat", "rm", "rmdir"):
            (self.bin / command).symlink_to(Path("/usr/bin") / command)
        self.env = {
            "PATH": str(self.bin), "HOME": str(self.root),
            "XDG_RUNTIME_DIR": str(self.runtime),
            "CALLS": str(self.calls), "CLIPBOARD": str(self.clipboard),
        }

    def run_script(self, *args, **env):
        result = subprocess.run(
            ["/usr/bin/bash", str(SCRIPT), *args],
            env={**self.env, **env}, capture_output=True, timeout=10,
        )
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []
        self.assertEqual(list(self.runtime.iterdir()), [], "temporary capture was not cleaned up")
        return result, calls

    def test_cancel_does_not_capture_or_touch_clipboard(self):
        for mode in ("copy", "annotate"):
            with self.subTest(mode=mode):
                self.calls.unlink(missing_ok=True)
                result, calls = self.run_script(mode, SLURP_STATUS="1", SLURP_ERROR="selection cancelled\n")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([call["name"] for call in calls], ["slurp"])
                self.assertEqual(self.clipboard.read_bytes(), b"existing clipboard")

    def test_selection_error_is_not_treated_as_cancellation(self):
        result, calls = self.run_script("copy", SLURP_STATUS="1", SLURP_ERROR="failed to create display\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"failed to create display", result.stderr)
        self.assertEqual([call["name"] for call in calls], ["slurp"])
        self.assertEqual(self.clipboard.read_bytes(), b"existing clipboard")

    def test_missing_selection_command_is_an_error(self):
        (self.bin / "slurp").unlink()
        result, calls = self.run_script("copy")
        self.assertEqual(result.returncode, 127)
        self.assertEqual(calls, [])
        self.assertEqual(self.clipboard.read_bytes(), b"existing clipboard")

    def test_empty_selection_does_not_capture(self):
        result, calls = self.run_script("copy", REGION="")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([call["name"] for call in calls], ["slurp"])
        self.assertEqual(self.clipboard.read_bytes(), b"existing clipboard")

    def test_failed_capture_does_not_start_either_consumer(self):
        for mode in ("copy", "annotate"):
            with self.subTest(mode=mode):
                self.calls.unlink(missing_ok=True)
                result, calls = self.run_script(mode, GRIM_STATUS="23")
                self.assertEqual(result.returncode, 23)
                self.assertEqual([call["name"] for call in calls], ["slurp", "grim"])
                self.assertEqual(self.clipboard.read_bytes(), b"existing clipboard")

    def test_empty_capture_does_not_replace_clipboard(self):
        result, calls = self.run_script("copy", EMPTY_IMAGE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([call["name"] for call in calls], ["slurp", "grim"])
        self.assertEqual(self.clipboard.read_bytes(), b"existing clipboard")

    def test_successful_copy_uses_complete_image_and_png_type(self):
        result, calls = self.run_script("copy")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call["name"] for call in calls], ["slurp", "grim", "wl-copy"])
        self.assertEqual(calls[1]["args"][:2], ["-g", "10,20 300x200"])
        self.assertEqual(calls[1]["mode"], 0o600)
        self.assertEqual(calls[2]["args"], ["--type", "image/png"])
        self.assertEqual(self.clipboard.read_bytes(), IMAGE)
        self.assertFalse(Path(calls[1]["args"][2]).exists())

    def test_annotation_preserves_existing_actions(self):
        result, calls = self.run_script("annotate")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call["name"] for call in calls], ["slurp", "grim", "satty"])
        self.assertTrue(calls[2]["image_exists"])
        self.assertEqual(calls[2]["image_hex"], IMAGE.hex())
        self.assertEqual(calls[2]["args"], [
            "--filename", calls[1]["args"][2], "--copy-command", "wl-copy",
            "--actions-on-enter", "save-to-clipboard,exit",
        ])
        self.assertFalse(Path(calls[1]["args"][2]).exists())

    def test_consumer_failure_is_returned_and_capture_is_cleaned(self):
        for mode in ("copy", "annotate"):
            with self.subTest(mode=mode):
                self.calls.unlink(missing_ok=True)
                result, calls = self.run_script(mode, CONSUMER_STATUS="19")
                self.assertEqual(result.returncode, 19)
                self.assertEqual(len(calls), 3)
                self.assertFalse(Path(calls[1]["args"][2]).exists())

    def test_invalid_arguments_do_not_run_commands(self):
        for arguments in ((), ("unknown",), ("copy", "extra")):
            with self.subTest(arguments=arguments):
                result, calls = self.run_script(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(calls, [])
                self.assertEqual(self.clipboard.read_bytes(), b"existing clipboard")


if __name__ == "__main__":
    unittest.main()
