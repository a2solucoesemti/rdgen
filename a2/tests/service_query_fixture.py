"""Extract the actual preview Win32 helper for a read-only Windows runtime test."""
import ast
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
tree = ast.parse((root / ".github/patches/a2_unattended.py").read_text())
widget = next(
    node.value.value for node in ast.walk(tree)
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "widget" for target in node.targets)
)
helper = widget[widget.index("  bool a2ServiceRunning()") : widget.index("  Widget a2Unattended(")]
running = helper.replace("a2ServiceRunning()", "testRunningService()").replace("'Connect'", "'RpcSs'")
missing = helper.replace("a2ServiceRunning()", "testMissingService()").replace("'Connect'", "'A2-CI-Nonexistent-Service'")
output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)
(output / "pubspec.yaml").write_text("""name: a2_service_query_test
environment:
  sdk: '>=3.5.0 <4.0.0'
dependencies:
  ffi: ^2.1.0
  win32: any
""")
(output / "service_query.dart").write_text("""import 'dart:io';
import 'dart:ffi' as a2ffi;
import 'package:ffi/ffi.dart' show calloc, StringUtf16Pointer;
import 'package:win32/win32.dart' as a2win32;
bool get isWindows => Platform.isWindows;
""" + running + missing + """
void main() {
  if (!Platform.isWindows) throw StateError('Windows runtime required');
  if (!testRunningService()) throw StateError('Could not query the running RPC service');
  if (testMissingService()) throw StateError('Nonexistent service incorrectly reported running');
  print('Native Windows service query passed: running and nonexistent service');
}
""")
