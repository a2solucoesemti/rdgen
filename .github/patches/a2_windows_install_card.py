from pathlib import Path


path = Path("flutter/lib/desktop/pages/desktop_home_page.dart")
source = path.read_text(encoding="utf-8")

password_board = "      if (!isOutgoingOnly) buildPasswordBoard(context),\n"
if source.count(password_board) != 1:
    raise SystemExit("Expected exactly one one-time-password board")
source = source.replace(password_board, "")

# Remove the powered-by widget itself so it cannot leave spacing or show a
# cached/default RustDesk translation.
powered_widget = """      if (bind.isCustomClient())
        Align(
          alignment: Alignment.center,
          child: loadPowered(context),
        ),
"""
if source.count(powered_widget) != 1:
    raise SystemExit("Expected exactly one powered-by widget")
source = source.replace(powered_widget, "")

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

quit_alignment = """    if (bind.isIncomingOnly()) {
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
centered_quit = """    if (bind.isIncomingOnly()) {
      return Align(
        alignment: Alignment.center,
        child: SizedBox(
          width: 150,
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
        ),
      ).marginAll(14);
    }
"""
if source.count(quit_alignment) != 1:
    raise SystemExit("Expected exactly one incoming-only Quit button")
source = source.replace(quit_alignment, centered_quit)

path.write_text(source, encoding="utf-8")

window_path = Path("flutter/windows/runner/win32_window.cpp")
window_source = window_path.read_text(encoding="utf-8")

# WS_EX_DLGMODALFRAME suppresses the small title-bar icon without clearing the
# class icon. Windows can therefore keep the branded icon for the taskbar,
# executable and installed shortcut.
window_created = """  if (!window) {
    return false;
  }

"""
hide_title_icon = """  if (!window) {
    return false;
  }

  const LONG_PTR extended_style = GetWindowLongPtr(window, GWL_EXSTYLE);
  SetWindowLongPtr(window, GWL_EXSTYLE,
                   extended_style | WS_EX_DLGMODALFRAME);
  SetWindowPos(window, nullptr, 0, 0, 0, 0,
               SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED);

"""
if window_source.count(window_created) != 1:
    raise SystemExit("Expected exactly one Win32 window creation guard")
window_source = window_source.replace(window_created, hide_title_icon)
window_path.write_text(window_source, encoding="utf-8")

print("Applied a2 Windows UI: no OTP/vendor caption/title icon, centered Quit, branded taskbar icon")
