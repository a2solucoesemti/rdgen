from pathlib import Path
import re


config_path = Path("libs/hbb_common/src/config.rs")
source = config_path.read_text(encoding="utf-8")

source, app_name_count = re.subn(
    r'pub static ref APP_NAME: RwLock<String> = RwLock::new\("RustDesk"\.to_owned\(\)\);',
    'pub static ref APP_NAME: RwLock<String> = RwLock::new("ConnectAdmin".to_owned());',
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
home_path.write_text(home, encoding="utf-8")

print("Applied ConnectAdmin branding, disabled account features and hid password board")
