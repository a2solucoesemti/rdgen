from pathlib import Path
import os
import re


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label}, found {count}")
    return source.replace(old, new)


# Use the a2 product name inside the Flutter UI and the Rust core, not only in
# the macOS bundle metadata.
app_name = os.environ.get("appname", "ConnectAdmin")
config_path = Path("libs/hbb_common/src/config.rs")
config_source = config_path.read_text(encoding="utf-8")
config_source, app_name_count = re.subn(
    r'pub static ref APP_NAME: RwLock<String> = RwLock::new\("[^"]+"\.to_owned\(\)\);',
    f'pub static ref APP_NAME: RwLock<String> = RwLock::new("{app_name}".to_owned());',
    config_source,
)
if app_name_count != 1:
    raise SystemExit(f"Expected exactly one default application name, found {app_name_count}")
config_source, account_count = re.subn(
    r"pub fn is_disable_account\(\) -> bool \{\s*is_some_hard_opton\(\"disable-account\"\)\s*\}",
    'pub fn is_disable_account() -> bool {\n    true\n}',
    config_source,
)
if account_count != 1:
    raise SystemExit(f"Expected one account feature switch, found {account_count}")
config_path.write_text(config_source, encoding="utf-8")

tabbar_path = Path("flutter/lib/desktop/widgets/tabbar_widget.dart")
tabbar_source = tabbar_path.read_text(encoding="utf-8")
tabbar_source, title_count = re.subn(
    rf'const Text\(\s*"(?:RustDesk|{re.escape(app_name)})",',
    'Text(bind.mainGetAppNameSync(),',
    tabbar_source,
)
if title_count != 1:
    raise SystemExit(f"Expected one RustDesk title label, found {title_count}")
tabbar_path.write_text(tabbar_source, encoding="utf-8")

# The shared install-card patch is also used by Windows. On macOS, restyle its
# permission card with a neutral grey background and black foreground.
home_path = Path("flutter/lib/desktop/pages/desktop_home_page.dart")
home_source = home_path.read_text(encoding="utf-8")
password_board = "      if (!isOutgoingOnly) buildPasswordBoard(context),\n"
if home_source.count(password_board) != 1:
    raise SystemExit("Expected exactly one one-time-password board")
home_source = home_source.replace(password_board, "")
start = home_source.index("  Widget buildInstallCard(")
end = home_source.index("\n  void initState()", start)
card = home_source[start:end]
white_card = "color: const Color.fromARGB(255, 255, 255, 255)"
gray_card = "color: const Color.fromARGB(255, 229, 231, 235)"
if card.count(white_card) == 1:
    card = card.replace(white_card, gray_card)
elif card.count(gray_card) != 1:
    raise SystemExit("Expected exactly one white or grey macOS card background")
card = card.replace("Colors.white", "const Color.fromARGB(255, 17, 24, 39)")
card = card.replace(
    "const Color.fromARGB(255, 34, 197, 94)",
    "const Color.fromARGB(255, 17, 24, 39)",
)
home_source = home_source[:start] + card + home_source[end:]
home_path.write_text(home_source, encoding="utf-8")

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

print(f"Applied macOS branding: {app_name}, grey card, hidden account/password")
