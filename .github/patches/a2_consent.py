"""Opt-in native machine authorization. Existing FFI signatures stay unchanged."""
import os
from pathlib import Path


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f"Unsupported upstream consent hook: {before[:60]}")
    return source.replace(before, after, 1)


def apply(root, assets):
    config = root / "libs/hbb_common/src/config.rs"
    source = config.read_text()
    policy = (assets / "a2_auth_policy.rs").read_text()
    source = replace_once(source, "impl Config {", policy + "\nimpl Config {")
    before = '''    pub fn get_option(k: &str) -> String {
        get_or(
            &OVERWRITE_SETTINGS,
            &CONFIG2.read().unwrap().options,'''
    after = '''    pub fn get_option(k: &str) -> String {
        if k == "approve-mode" || k == "verification-method" {
            if let Some(value) = a2_auth_override(k, a2_unattended_authorized()) {
                return value.to_owned();
            }
        }
        get_or(
            &OVERWRITE_SETTINGS,
            &CONFIG2.read().unwrap().options,'''
    source = replace_once(source, before, after)
    before = '''    pub fn get_option(k: &str) -> String {
        get_or('''
    after = '''    pub fn get_option(k: &str) -> String {
        if k == "approve-mode" || k == "verification-method" {
            if let Some(value) = a2_auth_override(k, a2_unattended_authorized()) {
                return value.to_owned();
            }
        }
        get_or('''
    source = replace_once(source, before, after)

    cargo = root / "libs/hbb_common/Cargo.toml"
    cargo_source = cargo.read_text()
    anchor = '[target.\'cfg(target_os = "windows")\'.dependencies]\nwinapi = { version = "0.3", features = ['
    cargo_source = replace_once(cargo_source, anchor, anchor + '\n    "winreg", "winnt", "sddl", "winbase", "winsvc", "minwinbase", "shellapi", "processthreadsapi", "handleapi",')

    core = root / "src/core_main.rs"
    core_source = core.read_text()
    anchor = '            if args[0] == "--uninstall" {'
    dispatch = '''            if args[0] == "--a2-allow-unattended" || args[0] == "--a2-revoke-unattended" {
                let result = platform::a2_set_unattended_consent(args[0] == "--a2-allow-unattended");
                if let Err(error) = &result {
                    log::error!("A2 unattended authorization failed: {}", error);
                }
                log::logger().flush();
                std::process::exit(if result.is_ok() { 0 } else { 1 });
            }
'''
    core_source = replace_once(core_source, anchor, dispatch + anchor)

    ffi = root / "src/flutter_ffi.rs"
    ffi_source = ffi.read_text()
    anchor = 'pub fn main_get_common(key: String) -> String {\n'
    hook = '''    #[cfg(windows)]
    if key == "a2-unattended-consent" {
        return hbb_common::config::a2_unattended_consent_exists().to_string();
    } else if key == "a2-is-installed-exe" {
        return crate::platform::is_cur_exe_the_installed().to_string();
    } else if key == "a2-service-policy-version" {
        return crate::ipc::get_config("a2-consent-policy-version").ok().flatten().unwrap_or_default();
    } else if key == "a2-consent-enable" || key == "a2-consent-disable" {
        return match crate::platform::a2_request_unattended_consent(key == "a2-consent-enable") {
            Ok(true) => "requested".to_owned(),
            Ok(false) => "cancelled".to_owned(),
            Err(_) => "error".to_owned(),
        };
    }
'''
    ffi_source = replace_once(ffi_source, anchor, anchor + hook)
    ipc = root / "src/ipc.rs"
    ipc_source = ipc.read_text()
    anchor = '''                if name == "id" {
                    value = Some(Config::get_id());'''
    ipc_source = replace_once(ipc_source, anchor, '''                if name == "a2-consent-policy-version" {
                    value = Some("1".to_owned());
                } else if name == "id" {
                    value = Some(Config::get_id());''')
    windows = root / "src/platform/windows.rs"
    windows_source = windows.read_text()
    if "fn a2_set_unattended_consent" in windows_source:
        raise ValueError("Consent patch already present")
    # Validate every anchor before writing any source file.
    config.write_text(source)
    cargo.write_text(cargo_source)
    core.write_text(core_source)
    ffi.write_text(ffi_source)
    ipc.write_text(ipc_source)
    windows.write_text(windows_source + "\n" + (assets / "a2_consent_windows.rs").read_text())


if __name__ == "__main__":
    if os.environ.get("A2_PROFILE") == "client" and os.environ.get("A2_UNATTENDED_CONTROLS") == "true":
        apply(Path("."), Path(__file__).parent)
        print("Applied administrative machine consent guard")
    else:
        print("Skipped administrative machine consent guard")
