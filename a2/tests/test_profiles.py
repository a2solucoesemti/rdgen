import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from a2.profiles import configure


ROOT = Path(__file__).resolve().parents[2]


class ProfileTests(unittest.TestCase):
    def options(self, profile="client", enabled=False):
        return json.loads(base64.b64decode(configure({}, profile, enabled)["custom"]))

    def test_portable_cannot_accept_a_password(self):
        self.assertEqual(self.options()["override-settings"]["approve-mode"], "click")

    def test_admin_compatibility(self):
        self.assertEqual(self.options("admin", True), {"override-settings": {"view-style": "adaptive", "allow-auto-update": "N"}})

    def test_opt_in_remains_attended_until_local_authorization(self):
        options = self.options(enabled=True)
        self.assertEqual(options["default-settings"]["approve-mode"], "click")
        self.assertNotIn("approve-mode", options["override-settings"])
        self.assertEqual(options["default-settings"]["verification-method"], "use-permanent-password")
        self.assertNotIn("password", options)

    def test_restrictions_survive_opt_in(self):
        for enabled in (False, True):
            policy = self.options(enabled=enabled)["override-settings"]
            for key in ("enable-file-transfer", "enable-terminal", "enable-tunnel",
                        "enable-remote-restart", "allow-remote-config-modification", "allow-auto-update"):
                self.assertEqual(policy[key], "N", key)
            for key in ("enable-keyboard", "enable-clipboard", "enable-audio"):
                self.assertEqual(policy[key], "Y", key)

    def test_identity_and_source_config_preserved(self):
        config = {"serverIP": "connect.a2ti.com.br", "key": "test", "custom": "old"}
        output = configure(config, "client", True)
        self.assertEqual(output["serverIP"], config["serverIP"])
        self.assertEqual(output["key"], config["key"])
        self.assertEqual(config["custom"], "old")
        with self.assertRaises(ValueError):
            configure(config, "typo")


class PatchCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("a2_unattended", ROOT / ".github/patches/a2_unattended.py")
        cls.patch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.patch)

    def test_upstream_drift_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "flutter/lib/desktop/pages/desktop_setting_page.dart"
            path.parent.mkdir(parents=True)
            path.write_text("changed upstream layout")
            with self.assertRaises(ValueError):
                self.patch.apply(root)
            self.assertEqual(path.read_text(), "changed upstream layout")

    def test_patch_on_fetched_upstream_when_available(self):
        # Optional integration fixture: provided explicitly by the maintainer.
        import os
        fixture = os.environ.get("A2_UPSTREAM_SETTINGS")
        if not fixture:
            self.skipTest("Set A2_UPSTREAM_SETTINGS to upstream 1.4.9 settings source")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "flutter/lib/desktop/pages/desktop_setting_page.dart"
            path.parent.mkdir(parents=True)
            path.write_text(Path(fixture).read_text())
            self.patch.apply(root)
            self.assertEqual(path.read_text().count("Widget a2Unattended("), 1)
            with self.assertRaises(ValueError):
                self.patch.apply(root)


if __name__ == "__main__":
    unittest.main()
