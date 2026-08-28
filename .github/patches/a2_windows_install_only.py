from pathlib import Path


path = Path("flutter/lib/desktop/pages/desktop_home_page.dart")
source = path.read_text(encoding="utf-8")

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
gray_background = """decoration: const BoxDecoration(
                color: Color.fromARGB(255, 229, 231, 235),
              ),"""
if card.count(gradient) != 1:
    raise SystemExit("Expected exactly one install-card gradient")
card = card.replace(gradient, gray_background)
card = card.replace("Colors.white", "const Color.fromARGB(255, 17, 24, 39)")

source = source[:start] + card + source[end:]
path.write_text(source, encoding="utf-8")

print("Applied Windows install card: grey, black and button-only")
