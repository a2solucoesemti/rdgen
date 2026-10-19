"""Backport the upstream libaom NASM-3 help check, without changing codecs.

Source: AOMediaCodec/libavif@d99de1c55349f4f2cc6f4011957b3cb06c2730fd
Upstream libaom fix: 6d2b7f71b98bfa28e372b1f2d85f137280bdb3de
"""
from pathlib import Path
import shutil
import sys


def apply(root, patch):
    port = root / "res/vcpkg/aom/portfile.cmake"
    source = port.read_text(encoding="utf-8")
    anchor = "            aom-install.diff\n"
    if source.count(anchor) != 2 or "a2-nasm.diff" in source:
        raise ValueError("Unsupported or already patched AOM overlay")
    shutil.copyfile(patch, port.parent / "a2-nasm.diff")
    port.write_text(source.replace(anchor, anchor + "            a2-nasm.diff\n"), encoding="utf-8")


if __name__ == "__main__":
    apply(Path("."), Path(sys.argv[1]))
