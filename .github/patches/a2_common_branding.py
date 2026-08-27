from pathlib import Path
import re


lang_path = Path("src/lang.rs")
lang_source = lang_path.read_text(encoding="utf-8")
lang_lookup = '&hbb_common::config::LocalConfig::get_option("lang"),'
if lang_source.count(lang_lookup) != 1:
    raise SystemExit("Expected exactly one saved-language lookup")
lang_source = lang_source.replace(lang_lookup, '"ptbr",')
lang_path.write_text(lang_source, encoding="utf-8")

ptbr_path = Path("src/lang/ptbr.rs")
ptbr_source = ptbr_path.read_text(encoding="utf-8")
ptbr_source, powered_count = re.subn(
    r'\("powered_by_me",\s*"[^"]*"\)',
    '("powered_by_me", "Desenvolvido por a2")',
    ptbr_source,
)
if powered_count != 1:
    raise SystemExit("Expected exactly one Portuguese powered-by translation")
ptbr_source, tip_count = re.subn(
    r'\("desk_tip",\s*"[^"]*"\)',
    '("desk_tip", "Seu computador pode ser acessado com este ID após você aceitar a conexão.")',
    ptbr_source,
)
if tip_count != 1:
    raise SystemExit("Expected exactly one Portuguese desktop tip")
ptbr_path.write_text(ptbr_source, encoding="utf-8")

common_path = Path("flutter/lib/common.dart")
common_source = common_path.read_text(encoding="utf-8")
start = common_source.index("Widget loadPowered(BuildContext context) {")
end = common_source.index("\n\nconst _kDefaultLogoAsset", start)
clean_footer = '''Widget loadPowered(BuildContext context) {
  return Text(
    "Desenvolvido por a2",
    style: Theme.of(context).textTheme.bodySmall,
  );
}'''
common_source = common_source[:start] + clean_footer + common_source[end:]
common_path.write_text(common_source, encoding="utf-8")

print("Applied a2 branding: Portuguese, a2 developer caption, contextual desktop text")
