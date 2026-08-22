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
    ('''    return Stack(
      children: [''', '''    if (a2Install) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 12),
        child: Center(
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: onPressed,
            child: Container(
              width: double.infinity,
              height: 44,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: const Color(0xFFF1F1F1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                translate(btnText),
                style: const TextStyle(
                  color: Colors.black,
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ),
        ),
      );
    }

    return Stack(
      children: ['''),
    ('''decoration: const BoxDecoration(color: MyTheme.accent),''',
     '''decoration: const BoxDecoration(color: Color(0xFF22C55E)),'''),
    ('''        ).marginOnly(bottom: 6, right: 6)
      ]);''', '''        ).marginOnly(bottom: 6, right: 6),
        const Padding(
          padding: EdgeInsets.only(top: 10, bottom: 12),
          child: Center(
            child: Text(
              "Desenvolvido por a2",
              style: TextStyle(color: Color(0xFF888888), fontSize: 12),
            ),
          ),
        )
      ]);'''),
)

for original, branded in replacements:
    if branded in source:
        continue
    if original not in source:
        raise SystemExit(f"Expected Windows install-card block was not found: {original.splitlines()[0]!r}")
    source = source.replace(original, branded, 1)

password_accent = '''decoration: BoxDecoration(color: MyTheme.accent),'''
green_password_accent = '''decoration: const BoxDecoration(color: Color(0xFF22C55E)),'''
if password_accent in source:
    source = source.replace(password_accent, green_password_accent, 1)
elif source.count(green_password_accent) < 2:
    raise SystemExit("Expected Windows password accent block was not found")

path.write_text(source, encoding="utf-8")
