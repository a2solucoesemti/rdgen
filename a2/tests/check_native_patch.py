"""Apply native hooks to pristine pinned upstream and reject partial/drifted writes."""
from pathlib import Path
import importlib.util
import shutil
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('consent_patch', root / '.github/patches/a2_consent.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)
source = Path(sys.argv[1])
with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / 'source'
    shutil.copytree(source, target)
    paths = ['libs/hbb_common/src/config.rs', 'libs/hbb_common/Cargo.toml',
             'src/core_main.rs', 'src/flutter_ffi.rs', 'src/ipc.rs', 'src/platform/windows.rs']
    original = {name: (target / name).read_text() for name in paths}
    patch.apply(target, root / '.github/patches')
    config = (target / paths[0]).read_text()
    assert config.split('impl LocalConfig {', 1)[1] == original[paths[0]].split('impl LocalConfig {', 1)[1]
    options = config.split('pub fn get_options()', 1)[1].split('#[inline]', 1)[0]
    assert 'a2_unattended_authorized()' in options
    one = config.split('pub fn get_option(k: &str)', 1)[1].split('pub fn get_bool_option', 1)[0]
    assert 'a2_unattended_authorized()' in one
    # A changed late anchor must leave every earlier source untouched.
    for name, value in original.items():
        (target / name).write_text(value)
    changed = target / 'src/ipc.rs'
    changed.write_text(original['src/ipc.rs'].replace('if name == "id" {', 'if name == "changed-upstream-id" {'))
    before = {name: (target / name).read_bytes() for name in paths}
    try:
        patch.apply(target, root / '.github/patches')
    except ValueError:
        pass
    else:
        raise AssertionError('Upstream drift was not rejected')
    assert before == {name: (target / name).read_bytes() for name in paths}
print('Native upstream patch compatibility and atomic drift rejection passed')
