"""Build a disposable Windows CI harness from the exact native production snippets."""
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[2]
output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)
(output / "src").mkdir()
for name in ("a2_auth_policy.rs", "a2_consent_windows.rs"):
    shutil.copyfile(root / ".github/patches" / name, output / name)
shutil.copyfile(root / "a2/tests/consent_fixture.rs", output / "src/main.rs")
(output / "Cargo.toml").write_text('''[package]
name = "a2-native-consent-test"
version = "0.1.0"
edition = "2021"
[dependencies]
anyhow = "1"
log = "0.4"
winreg = "0.11"
windows-service = "0.6"
winapi = { version = "0.3", features = ["winreg", "winnt", "sddl", "winbase", "winsvc", "minwinbase", "shellapi", "processthreadsapi", "handleapi", "synchapi", "winuser"] }
''')
