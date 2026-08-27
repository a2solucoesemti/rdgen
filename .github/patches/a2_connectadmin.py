from pathlib import Path
import os
import re


app_name = os.environ.get("A2_APP_NAME", "ConnectAdmin")
config_path = Path("libs/hbb_common/src/config.rs")
source = config_path.read_text(encoding="utf-8")

source, app_name_count = re.subn(
    r'pub static ref APP_NAME: RwLock<String> = RwLock::new\("RustDesk"\.to_owned\(\)\);',
    f'pub static ref APP_NAME: RwLock<String> = RwLock::new("{app_name}".to_owned());',
    source,
)
if app_name_count != 1:
    raise SystemExit(f"Expected one RustDesk APP_NAME, found {app_name_count}")

source, account_count = re.subn(
    r'pub fn is_disable_account\(\) -> bool \{\s*is_some_hard_opton\("disable-account"\)\s*\}',
    'pub fn is_disable_account() -> bool {\n    true\n}',
    source,
)
if account_count != 1:
    raise SystemExit(f"Expected one account feature switch, found {account_count}")

config_path.write_text(source, encoding="utf-8")

tabbar_path = Path("flutter/lib/desktop/widgets/tabbar_widget.dart")
tabbar = tabbar_path.read_text(encoding="utf-8")
tabbar, title_count = re.subn(
    r'const Text\(\s*"RustDesk",',
    'Text(bind.mainGetAppNameSync(),',
    tabbar,
)
if title_count != 1:
    raise SystemExit(f"Expected one RustDesk title label, found {title_count}")
tabbar_path.write_text(tabbar, encoding="utf-8")

for lang_file in (Path("src/lang/en.rs"), Path("src/lang/ptbr.rs")):
    lang_source = lang_file.read_text(encoding="utf-8")
    lang_source, powered_count = re.subn(
        r'\("powered_by_me",\s*"[^"]*"\)',
        '("powered_by_me", "Desenvolvido por a2")',
        lang_source,
    )
    if powered_count != 1:
        raise SystemExit(f"Expected one powered-by label in {lang_file}, found {powered_count}")
    lang_file.write_text(lang_source, encoding="utf-8")

home_path = Path("flutter/lib/desktop/pages/desktop_home_page.dart")
home = home_path.read_text(encoding="utf-8")
password_board = "      if (!isOutgoingOnly) buildPasswordBoard(context),\n"
if home.count(password_board) != 1:
    raise SystemExit("Expected exactly one one-time-password board")
home = home.replace(password_board, "")

incoming_quit = """    if (bind.isIncomingOnly()) {
      return Align(
        alignment: Alignment.centerRight,
        child: OutlinedButton(
          onPressed: () {
            SystemNavigator.pop(); // Close the application
            // https://github.com/flutter/flutter/issues/66631
            if (isWindows) {
              exit(0);
            }
          },
          child: Text(translate('Quit')),
        ),
      ).marginAll(14);
    }
"""
centered_quit = incoming_quit.replace(
    "alignment: Alignment.centerRight,", "alignment: Alignment.center,"
)
if home.count(incoming_quit) != 1:
    raise SystemExit("Expected exactly one incoming-only Quit button")
home = home.replace(incoming_quit, centered_quit)
home_path.write_text(home, encoding="utf-8")

window_path = Path("flutter/windows/runner/win32_window.cpp")
window_source = window_path.read_text(encoding="utf-8")
window_source, window_icon_count = re.subn(
    r'icon_path \+= L"data\\\\flutter_assets\\\\assets\\\\icon\.ico";',
    lambda _: r'icon_path += L"data\\flutter_assets\\assets\\window-icon.ico";',
    window_source,
)
if window_icon_count != 1:
    raise SystemExit(f"Expected one custom window icon path, found {window_icon_count}")
window_path.write_text(window_source, encoding="utf-8")

print(f"Applied {app_name} branding, centered Quit and separated small window icon")
