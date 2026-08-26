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

print("Applied clean ConnectAdmin branding and disabled account features")
