from pathlib import Path
import re


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label}, found {count}")
    return source.replace(old, new)


# Use the a2 product name inside the Flutter UI and the Rust core, not only in
# the macOS bundle metadata.
config_path = Path("libs/hbb_common/src/config.rs")
config_source = config_path.read_text(encoding="utf-8")
config_source = replace_once(
    config_source,
    'pub static ref APP_NAME: RwLock<String> = RwLock::new("RustDesk".to_owned());',
    'pub static ref APP_NAME: RwLock<String> = RwLock::new("Connect Admin".to_owned());',
    "default application name",
)
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
    r'const Text\(\s*"RustDesk",',
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
start = home_source.index("  Widget buildInstallCard(")
end = home_source.index("\n  void initState()", start)
card = home_source[start:end]
card = replace_once(
    card,
    "color: const Color.fromARGB(255, 255, 255, 255)",
    "color: const Color.fromARGB(255, 229, 231, 235)",
    "macOS card background",
)
card = card.replace("Colors.white", "const Color.fromARGB(255, 17, 24, 39)")
card = card.replace(
    "const Color.fromARGB(255, 34, 197, 94)",
    "const Color.fromARGB(255, 17, 24, 39)",
)
home_source = home_source[:start] + card + home_source[end:]
home_path.write_text(home_source, encoding="utf-8")

print("Applied macOS branding: grey permission card, hidden account, Connect Admin title")
