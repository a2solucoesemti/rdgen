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
        });'''),
    ('''              decoration: BoxDecoration(
                  gradient: LinearGradient(
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
                colors: [
                  Color.fromARGB(255, 226, 66, 188),
                  Color.fromARGB(255, 244, 114, 124),
                ],
              )),
              padding: EdgeInsets.all(20),''', '''              decoration: const BoxDecoration(color: MyTheme.button),
              padding: EdgeInsets.all(20),'''),
    ('''                                      isOutline: true,
                                      text: translate(btnText),
                                      textColor: Colors.white,
                                      borderColor: Colors.white,''', '''                                      isOutline: true,
                                      text: translate(btnText),
                                      textColor: Colors.black,
                                      borderColor: Colors.black,'''),
    ('''                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,''', '''                                    color: Colors.black,
                                    fontWeight: FontWeight.bold,'''),
    ('''                                color: Colors.white,
                                fontWeight: FontWeight.normal,''', '''                                color: Colors.black,
                                fontWeight: FontWeight.normal,'''),
    ('''                                            color: Colors.white,
                                            fontSize: 12),''', '''                                            color: Colors.black,
                                            fontSize: 12),'''),
)

for original, branded in replacements:
    if branded in source:
        continue
    if original not in source:
        raise SystemExit(f"Expected install-card block was not found: {original.splitlines()[0]!r}")
    source = source.replace(original, branded, 1)

path.write_text(source, encoding="utf-8")
