"""Windows Connect: start portable support on launch; keep native installation explicit."""
import os
from pathlib import Path


def once(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f'Unsupported portable hook: {before[:70]}')
    return source.replace(before, after, 1)


def apply(root):
    home_path = root / 'flutter/lib/desktop/pages/desktop_home_page.dart'
    status_path = root / 'flutter/lib/desktop/pages/connection_page.dart'
    tray_path = root / 'src/tray.rs'
    home = home_path.read_text(encoding='utf-8')
    status = status_path.read_text(encoding='utf-8')
    tray = tray_path.read_text(encoding='utf-8')
    anchor = '  @override\n  void initState() {\n    super.initState();\n'
    home = once(home, anchor, '''  // Opening the portable client authorizes attended support for this run.
  // Never call this for an installed client: upstream would reinstall its service.
  Future<void> a2StartPortableSupport() async {
    if (!isWindows || bind.mainIsInstalled()) return;
    try {
      await start_service(true);
    } catch (_) {
      debugPrint('A2 portable support could not be started');
    }
  }

''' + anchor + '    Future.microtask(a2StartPortableSupport);\n')
    status = once(status, 'offstage: !_svcStopped.value,',
                  'offstage: !_svcStopped.value || (isWindows && !bind.mainIsInstalled()),')
    status = once(status, '? translate("Service is not running")', '''? (isWindows && !bind.mainIsInstalled()
              ? 'Atendimento indisponível. Feche e abra o Connect.'
              : translate("Service is not running"))''')
    # Windows used the large application icon.png before the dedicated tray ICO.
    # Keep macOS/Linux and all technician builds unchanged.
    tray = once(tray, r'let path = path.join(r"data\flutter_assets\assets\icon.png");',
                r'let path = path.join(r"data\flutter_assets\assets\tray-icon.ico");')
    # Validate all hooks before writing any source file.
    home_path.write_text(home, encoding='utf-8')
    status_path.write_text(status, encoding='utf-8')
    tray_path.write_text(tray, encoding='utf-8')


if __name__ == '__main__':
    if os.environ.get('A2_PROFILE', 'client') == 'client':
        apply(Path('.'))
        print('Applied Connect portable startup and dedicated Windows tray icon')
    else:
        print('Skipped client-only portable startup and tray icon')
