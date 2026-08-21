from pathlib import Path

path = Path("flutter/lib/desktop/pages/desktop_home_page.dart")
source = path.read_text(encoding="utf-8")

replacements = (
    ('''        return buildInstallCard(
            "", bind.isOutgoingOnly() ? "" : "install_tip", "Install",
            () async {
          await rustDeskWinManager.closeAllSubWindows();
          bind.mainGotoInstall();
        });''', '''        return buildInstallCard("", "", "Install", () async {
          await rustDeskWinManager.closeAllSubWindows();
          bind.mainGotoInstall();
        }, a2Install: true);'''),
    ('''      bool? closeButton,
      String? closeOption}) {''', '''      bool? closeButton,
      String? closeOption,
      bool a2Install = false}) {'''),
    ('''              decoration: BoxDecoration(
                  gradient: LinearGradient(
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
                colors: [
                  Color.fromARGB(255, 226, 66, 188),
                  Color.fromARGB(255, 244, 114, 124),
                ],
              )),
              padding: EdgeInsets.all(20),''', '''              decoration: a2Install
                  ? null
                  : BoxDecoration(
                      gradient: LinearGradient(
                      begin: Alignment.centerLeft,
                      end: Alignment.centerRight,
                      colors: [
                        Color.fromARGB(255, 226, 66, 188),
                        Color.fromARGB(255, 244, 114, 124),
                      ],
                    )),
              padding: EdgeInsets.all(a2Install ? 0 : 20),'''),
    ('''                                      isOutline: true,
                                      text: translate(btnText),
                                      textColor: Colors.white,
                                      borderColor: Colors.white,''', '''                                      isOutline: true,
                                      text: translate(btnText),
                                      textColor: a2Install ? Colors.black : Colors.white,
                                      borderColor: a2Install ? Colors.transparent : Colors.white,'''),
)

for original, branded in replacements:
    if branded in source:
        continue
    if original not in source:
        raise SystemExit(f"Expected install-card block was not found: {original.splitlines()[0]!r}")
    source = source.replace(original, branded, 1)

path.write_text(source, encoding="utf-8")
