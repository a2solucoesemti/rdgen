// Included only in the opt-in Connect Windows profile. No credentials in this key.
const A2_CONSENT_KEY: &str = r"SOFTWARE\A2ConnectUnattendedConsentV1";

fn a2_auth_override(key: &str, authorized: bool) -> Option<&'static str> {
    match key {
        "verification-method" => Some("use-permanent-password"),
        "approve-mode" => Some(if authorized { "password-click" } else { "click" }),
        _ => None,
    }
}

#[cfg(windows)]
fn a2_machine_string(path: &str, name: &str) -> Option<String> {
    use std::os::windows::ffi::OsStrExt;
    use winapi::um::winreg::*;
    let path: Vec<u16> = std::ffi::OsStr::new(path).encode_wide().chain(Some(0)).collect();
    let name: Vec<u16> = std::ffi::OsStr::new(name).encode_wide().chain(Some(0)).collect();
    let mut data = [0u16; 256];
    let mut size = std::mem::size_of_val(&data) as u32;
    let result = unsafe {
        RegGetValueW(HKEY_LOCAL_MACHINE, path.as_ptr(), name.as_ptr(),
        RRF_RT_REG_SZ | RRF_RT_REG_EXPAND_SZ | RRF_NOEXPAND | RRF_SUBKEY_WOW6464KEY, std::ptr::null_mut(),
            data.as_mut_ptr() as *mut _, &mut size)
    };
    if result != 0 { return None; }
    let length = data.iter().position(|value| *value == 0)?;
    if length == 0 { return None; }
    String::from_utf16(&data[..length]).ok()
}

/// Machine authorization lives in protected HKLM, never in imported user TOML.
pub fn a2_unattended_consent_exists() -> bool {
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        use winapi::um::winreg::*;
        let path: Vec<u16> = std::ffi::OsStr::new(A2_CONSENT_KEY).encode_wide().chain(Some(0)).collect();
        let name: Vec<u16> = "Enabled".encode_utf16().chain(Some(0)).collect();
        let mut enabled = 0u32;
        let mut size = std::mem::size_of_val(&enabled) as u32;
        let result = unsafe {
            RegGetValueW(HKEY_LOCAL_MACHINE, path.as_ptr(), name.as_ptr(),
                RRF_RT_REG_DWORD | RRF_SUBKEY_WOW6464KEY, std::ptr::null_mut(),
                &mut enabled as *mut _ as *mut _, &mut size)
        };
        result == 0 && enabled == 1
    }
    #[cfg(not(windows))]
    { false }
}

fn a2_service_path_matches(image: &str, current: &str) -> bool {
    let image = image.trim();
    let executable = if let Some(quoted) = image.strip_prefix('"') {
        match quoted.find('"') { Some(end) => &quoted[..end], None => return false }
    } else {
        image.split_whitespace().next().unwrap_or("")
    };
    let normalize = |path: &str| path.trim_start_matches(r"\\?\").replace('/', "\\").to_lowercase();
    !executable.is_empty() && normalize(executable) == normalize(current)
}

#[cfg(windows)]
fn a2_installed_service_active() -> bool {
    use winapi::um::winsvc::*;
    let image = match a2_machine_string(r"SYSTEM\CurrentControlSet\Services\Connect", "ImagePath") {
        Some(image) => image,
        None => return false,
    };
    let current = match std::env::current_exe() { Ok(path) => path, Err(_) => return false };
    if !a2_service_path_matches(&image, &current.to_string_lossy()) { return false; }
    unsafe {
        let manager = OpenSCManagerW(std::ptr::null(), std::ptr::null(), SC_MANAGER_CONNECT);
        if manager.is_null() { return false; }
        let name: Vec<u16> = "Connect".encode_utf16().chain(Some(0)).collect();
        let service = OpenServiceW(manager, name.as_ptr(), SERVICE_QUERY_STATUS);
        if service.is_null() { CloseServiceHandle(manager); return false; }
        let mut status: SERVICE_STATUS = std::mem::zeroed();
        let running = QueryServiceStatus(service, &mut status) != 0 && status.dwCurrentState == SERVICE_RUNNING;
        CloseServiceHandle(service);
        CloseServiceHandle(manager);
        running
    }
}

pub fn a2_unattended_authorized() -> bool {
    #[cfg(windows)]
    {
        if !a2_unattended_consent_exists() || !a2_installed_service_active() { return false; }
        match (
            a2_machine_string(A2_CONSENT_KEY, "MachineGuid"),
            a2_machine_string(r"SOFTWARE\Microsoft\Cryptography", "MachineGuid"),
        ) {
            (Some(granted), Some(current)) => granted == current,
            _ => false,
        }
    }
    #[cfg(not(windows))]
    { false }
}

#[cfg(test)]
mod a2_auth_tests {
    use super::*;

    #[test]
    fn no_grant_requires_local_click_even_with_old_preferences() {
        assert_eq!(a2_auth_override("approve-mode", false), Some("click"));
        assert_eq!(a2_auth_override("verification-method", false), Some("use-permanent-password"));
    }

    #[test]
    fn approved_machine_keeps_password_and_local_click_paths() {
        assert_eq!(a2_auth_override("approve-mode", true), Some("password-click"));
        assert_eq!(a2_auth_override("verification-method", true), Some("use-permanent-password"));
    }

    #[test]
    fn authentication_guard_does_not_change_identity_or_permissions() {
        for key in ["id", "key", "custom-rendezvous-server", "enable-file-transfer", "enable-terminal"] {
            assert_eq!(a2_auth_override(key, false), None);
            assert_eq!(a2_auth_override(key, true), None);
        }
    }

    #[test]
    fn portable_copy_cannot_inherit_installed_service_authorization() {
        assert!(a2_service_path_matches(r#""C:\Program Files\Connect\Connect.exe" --service"#, r"c:\program files\connect\connect.exe"));
        assert!(!a2_service_path_matches(r#""C:\Program Files\Connect\Connect.exe" --service"#, r"C:\Downloads\Connect.exe"));
        assert!(!a2_service_path_matches(r"C:\Program Files\Connect\Connect.exe --service", r"C:\Program Files\Connect\Connect.exe"));
    }
}
