"""Apply the checked-in RDGen customizations to a dedicated pristine 1.4.9 tree."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from a2.profiles import configure


def fingerprint(unattended=False):
    digest = hashlib.sha256()
    files = [p for directory in ['a2/local', '.github/patches', '.github/assets/connect']
             for p in (REPO / directory).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts]
    files.append(REPO / 'a2/profiles.py')
    for path in sorted(files):
        digest.update(str(path.relative_to(REPO)).replace('\\', '/').encode())
        digest.update(path.read_bytes())
    digest.update(str(unattended).encode())
    return digest.hexdigest()[:16]


def replace(path, before, after, required=True):
    source = path.read_text(encoding='utf-8-sig')
    if required and before not in source:
        raise ValueError(f'Upstream hook missing in {path.name}: {before[:50]}')
    path.write_text(source.replace(before, after), encoding='utf-8')


def apply(source, unattended):
    marker = source / '.a2-prepared.json'
    expected = fingerprint(unattended)
    if marker.exists():
        data = json.loads(marker.read_text())
        if data['fingerprint'] != expected:
            raise ValueError('Source was prepared with a different recipe; use a new build folder')
        print('A2 source already prepared with this recipe')
        return
    changes = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True)
    if changes.strip():
        raise ValueError('Refusing to patch a dirty upstream tree; use a new build folder')
    versions = json.loads((REPO / 'a2/local/versions.json').read_text())
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != versions['rustdeskCommit']:
        raise ValueError('Unexpected RustDesk commit')
    config = configure(json.loads((REPO / 'a2/local/client-config.json').read_text()), 'client', unattended)
    if config.get('permanentPassword'):
        raise ValueError('A shared password must never be embedded in a local build')
    # Same built-in policy as the preview, with settings disabled for the attended client.
    custom = json.loads(base64.b64decode(config['custom']))
    if not unattended:
        custom['disable-settings'] = 'Y'
    config['custom'] = base64.b64encode(json.dumps(custom, separators=(',', ':')).encode()).decode()
    for relative in ['Cargo.toml', 'libs/portable/Cargo.toml', 'flutter/windows/runner/Runner.rc']:
        path = source / relative
        for old in ['RustDesk Remote Desktop', 'Purslane Tech Pte. Ltd.', 'Purslane Ltd']:
            replace(path, old, 'Connect' if old == 'RustDesk Remote Desktop' else config['compname'], False)
        if relative.endswith('Cargo.toml'):
            replace(path, 'ProductName = "RustDesk"', 'ProductName = "Connect"', False)
            replace(path, 'OriginalFilename = "rustdesk.exe"', 'OriginalFilename = "Connect.exe"', False)
        else:
            replace(path, '"RustDesk"', '"Connect"', False)
            replace(path, '"rustdesk.exe"', '"Connect.exe"', False)
    replace(source / 'libs/portable/src/main.rs', 'const APP_PREFIX: &str = "rustdesk";', 'const APP_PREFIX: &str = "Connect";')
    replace(source / 'libs/hbb_common/src/config.rs', 'rs-ny.rustdesk.com', config['serverIP'])
    replace(source / 'libs/hbb_common/src/config.rs', 'OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=', config['key'])
    replace(source / 'src/common.rs', 'https://admin.rustdesk.com', config.get('apiServer', ''), False)
    for relative in ['flutter/pubspec.yaml', 'flutter/pubspec.lock']:
        replace(source / relative, '2ded7f146437a761ffe6981e2f742038f85ca68d', '08a471bb8ceccdd50483c81cdfa8b81b07b14b87', False)
        if '08a471bb8ceccdd50483c81cdfa8b81b07b14b87' not in (source / relative).read_text():
            raise ValueError('Unexpected Flutter texture renderer revision')
    # Retain the existing RDGen custom_.txt mechanism; these builds are lab previews.
    common = source / 'src/common.rs'
    vendor_key = 'const KEY: &str = "5Qbwsde3unUcJBtrx9ZkvUmwFNoExHzpryHuPUdqlWM=";'
    if common.read_text().count(vendor_key) != 1:
        raise ValueError('Unsupported RDGen custom-client hook')
    patches = REPO / '.github/patches'
    previous = Path.cwd()
    try:
        os.chdir(source)
        os.environ.update(A2_PROFILE='client', A2_APP_NAME='Connect', A2_UNATTENDED_CONTROLS=str(unattended).lower())
        for name in ['allowCustom.py', 'a2_windows_install_only.py', 'a2_portable.py', 'a2_connectadmin.py', 'a2_consent.py', 'a2_unattended.py']:
            runpy.run_path(str(patches / name), run_name='__main__')
        runpy.run_path(str(patches / 'a2_aom_nasm.py'), run_name='a2_overlay_module')['apply'](source, patches / 'a2_aom_nasm.diff')
        subprocess.run(['git', 'apply', '--check', str(patches / 'removeSetupServerTip.diff')], check=True)
        subprocess.run(['git', 'apply', str(patches / 'removeSetupServerTip.diff')], check=True)
    finally:
        os.chdir(previous)
    assets = REPO / '.github/assets/connect/windows'
    for file in assets.iterdir():
        if file.suffix in {'.png', '.ico', '.svg'}:
            shutil.copyfile(file, source / 'flutter/assets' / file.name)
            if file.suffix != '.svg':
                shutil.copyfile(file, source / 'res' / file.name)
    shutil.copyfile(assets / 'icon.ico', source / 'flutter/windows/runner/resources/app_icon.ico')
    shutil.copyfile(REPO / '.github/assets/connect/official/logo-original.png', source / 'flutter/assets/logo.png')
    # Embed the raster exactly; do not recreate the supplied lettering as SVG paths.
    (source / 'a2-custom.txt').write_text(config['custom'], encoding='ascii')
    marker.write_text(json.dumps({'fingerprint': expected, 'upstreamCommit': commit,
                                 'unattendedControls': unattended}, indent=2), encoding='utf-8')
    print('A2 source prepared; no password embedded')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path)
    parser.add_argument('--unattended', action='store_true')
    parser.add_argument('--fingerprint', action='store_true')
    args = parser.parse_args()
    if args.fingerprint:
        print(fingerprint(args.unattended))
    elif args.source:
        apply(args.source.resolve(), args.unattended)
    else:
        parser.error('--source or --fingerprint is required')
