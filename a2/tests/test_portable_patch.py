"""Check the portable patch on the pinned upstream files when available."""
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('portable_patch', ROOT / '.github/patches/a2_portable.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


@unittest.skipUnless(os.environ.get('A2_PORTABLE_FIXTURE'), 'Pristine upstream fixture required')
class PortablePatchTests(unittest.TestCase):
    def test_pinned_upstream_and_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'client'
            shutil.copytree(os.environ['A2_PORTABLE_FIXTURE'], root)
            patch.apply(root)
            home = (root / 'flutter/lib/desktop/pages/desktop_home_page.dart').read_text()
            self.assertIn('if (!isWindows || bind.mainIsInstalled()) return;', home)
            self.assertEqual(home.count('Future.microtask(a2StartPortableSupport)'), 1)
            self.assertNotIn('install_service(', home)
            files = list(root.rglob('*'))
            before = {p: p.read_bytes() for p in files if p.is_file()}
            with self.assertRaises(ValueError):
                patch.apply(root)
            self.assertEqual(before, {p: p.read_bytes() for p in before})
