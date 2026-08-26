from pathlib import Path


path = Path("flutter/lib/desktop/pages/desktop_home_page.dart")
source = path.read_text(encoding="utf-8")

install_tip = '"", bind.isOutgoingOnly() ? "" : "install_tip", "Install"'
if source.count(install_tip) != 1:
    raise SystemExit("Expected exactly one Windows install-tip card")
source = source.replace(install_tip, '"", "", "Install"')

gradient = """decoration: BoxDecoration(
                  gradient: LinearGradient(
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
                colors: [
                  Color.fromARGB(255, 226, 66, 188),
                  Color.fromARGB(255, 244, 114, 124),
                ],
              )),"""
white_background = """decoration: const BoxDecoration(
                color: Color.fromARGB(255, 255, 255, 255),
              ),"""
if source.count(gradient) != 1:
    raise SystemExit("Expected exactly one install-card gradient")
source = source.replace(gradient, white_background)

button_colors = """textColor: Colors.white,
                                      borderColor: Colors.white,"""
green_button = """textColor: const Color.fromARGB(255, 34, 197, 94),
                                      borderColor: const Color.fromARGB(255, 34, 197, 94),"""
if source.count(button_colors) != 1:
    raise SystemExit("Expected exactly one install-card button color block")
source = source.replace(button_colors, green_button)

path.write_text(source, encoding="utf-8")
print("Applied a2 Windows install card: button only, white background")
