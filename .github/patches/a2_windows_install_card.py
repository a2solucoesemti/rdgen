from pathlib import Path


path = Path("flutter/lib/desktop/pages/desktop_home_page.dart")
source = path.read_text(encoding="utf-8")

password_board = "      if (!isOutgoingOnly) buildPasswordBoard(context),\n"
if source.count(password_board) != 1:
    raise SystemExit("Expected exactly one one-time-password board")
source = source.replace(password_board, "")

popup_menu = "                        buildPopupMenu(context)\n"
if source.count(popup_menu) != 1:
    raise SystemExit("Expected exactly one settings popup menu")
source = source.replace(
    popup_menu,
    "                        if (!bind.isDisableSettings()) buildPopupMenu(context)\n",
)

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
gray_background = """decoration: const BoxDecoration(
                color: Color.fromARGB(255, 229, 231, 235),
              ),"""
if source.count(gradient) != 1:
    raise SystemExit("Expected exactly one install-card gradient")
source = source.replace(gradient, gray_background)

button_colors = """textColor: Colors.white,
                                      borderColor: Colors.white,"""
black_button = """textColor: const Color.fromARGB(255, 0, 0, 0),
                                      borderColor: const Color.fromARGB(255, 0, 0, 0),"""
if source.count(button_colors) != 1:
    raise SystemExit("Expected exactly one install-card button color block")
source = source.replace(button_colors, black_button)

path.write_text(source, encoding="utf-8")

window_path = Path("flutter/windows/runner/win32_window.cpp")
window_source = window_path.read_text(encoding="utf-8")
icon_start = window_source.index("    // Try to load icon from data\\flutter_assets\\assets\\icon.ico")
icon_end = window_source.index("    window_class.hbrBackground = 0;", icon_start)
window_source = (
    window_source[:icon_start]
    + "    // Keep the title bar clean; the executable and shortcuts retain the app icon.\n"
    + "    window_class.hIcon = nullptr;\n\n"
    + window_source[icon_end:]
)
window_path.write_text(window_source, encoding="utf-8")

print("Applied a2 Windows UI: no OTP, no title icon, gray card, black install button")
