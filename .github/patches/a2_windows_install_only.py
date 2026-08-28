from pathlib import Path
import os


path = Path("flutter/lib/desktop/pages/desktop_home_page.dart")
source = path.read_text(encoding="utf-8")
profile = os.environ.get("A2_PROFILE", "client")

if profile != "client":
    print("Skipped client-only Windows light/install styling")
    raise SystemExit(0)

install_tip = '"", bind.isOutgoingOnly() ? "" : "install_tip", "Install"'
if source.count(install_tip) != 1:
    raise SystemExit("Expected exactly one Windows install-tip card")
source = source.replace(install_tip, '"", "", "Install"')

start = source.index("  Widget buildInstallCard(")
end = source.index("\n  void initState()", start)
card = source[start:end]

gradient = """decoration: BoxDecoration(
                  gradient: LinearGradient(
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
                colors: [
                  Color.fromARGB(255, 226, 66, 188),
                  Color.fromARGB(255, 244, 114, 124),
                ],
              )),"""
transparent_background = """decoration: const BoxDecoration(
                color: Colors.transparent,
              ),"""
if card.count(gradient) != 1:
    raise SystemExit("Expected exactly one install-card gradient")
card = card.replace(gradient, transparent_background)
card = card.replace("Colors.white", "const Color.fromARGB(255, 17, 24, 39)")

source = source[:start] + card + source[end:]
path.write_text(source, encoding="utf-8")

main_path = Path("flutter/lib/main.dart")
main_source = main_path.read_text(encoding="utf-8")
theme_mode = "MyTheme.currentThemeMode()"
preference = "MyTheme.getThemeModePreference()"
if main_source.count(theme_mode) < 1:
    raise SystemExit("Expected at least one current theme mode reference")
if main_source.count(preference) != 1:
    raise SystemExit("Expected exactly one theme preference reference")
main_source = main_source.replace(theme_mode, "ThemeMode.light")
main_source = main_source.replace(preference, "ThemeMode.light")
main_path.write_text(main_source, encoding="utf-8")

print("Applied Connect Windows UI: always light and transparent button-only install area")
