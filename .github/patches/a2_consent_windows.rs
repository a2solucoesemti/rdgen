/// Called only by the elevated, installed Connect executable. Never receives a password.
pub fn a2_set_unattended_consent(enabled: bool) -> ResultType<()> {
    use std::os::windows::ffi::OsStrExt;
    use winapi::um::{sddl::ConvertStringSecurityDescriptorToSecurityDescriptorW, winnt::*};
    if !is_elevated(None).unwrap_or(false) {
        bail!("Administrative consent is required");
    }
    if enabled && (!is_installed() || !is_cur_exe_the_installed()) {
        bail!("Install Connect before authorizing unattended access");
    }
    if enabled {
        if crate::ipc::get_config("a2-consent-policy-version")?.as_deref() != Some("1") {
            bail!("Install the complete A2 consent-capable service first");
        }
        let payload = crate::ipc::get_config("permanent-password-storage-and-salt")?
            .ok_or_else(|| hbb_common::anyhow::anyhow!("Service did not confirm a local credential"))?;
        let (storage, salt) = payload.split_once('\n')
            .ok_or_else(|| hbb_common::anyhow::anyhow!("Invalid credential state response"))?;
        if !hbb_common::config::local_permanent_password_storage_is_usable_for_auth(storage, salt) {
            bail!("A local permanent credential must be stored by the service first");
        }
        a2_prepare_unattended_service()?;
    }
    let hklm = RegKey::predef(HKEY_LOCAL_MACHINE);
    let machine = hklm.open_subkey_with_flags(r"SOFTWARE\Microsoft\Cryptography", KEY_READ | KEY_WOW64_64KEY)?;
    let machine_guid: String = machine.get_value("MachineGuid")?;
    if machine_guid.is_empty() { bail!("Machine identity unavailable"); }
    // Administrators own the key; a non-elevated original user cannot rewrite its DACL.
    // SYSTEM/Admin: full control; authenticated users: read only; no inherited ACEs.
    let security: Vec<u16> = std::ffi::OsStr::new("O:BAG:BAD:P(A;;KA;;;SY)(A;;KA;;;BA)(A;;KR;;;AU)")
        .encode_wide().chain(Some(0)).collect();
    let mut descriptor = std::ptr::null_mut();
    let converted = unsafe {
        ConvertStringSecurityDescriptorToSecurityDescriptorW(
            security.as_ptr(), 1, &mut descriptor, std::ptr::null_mut())
    };
    if converted == 0 { return Err(std::io::Error::last_os_error().into()); }
    let path: Vec<u16> = std::ffi::OsStr::new(r"SOFTWARE\A2ConnectUnattendedConsentV1")
        .encode_wide().chain(Some(0)).collect();
    let mut attributes = winapi::um::minwinbase::SECURITY_ATTRIBUTES {
        nLength: std::mem::size_of::<winapi::um::minwinbase::SECURITY_ATTRIBUTES>() as u32,
        lpSecurityDescriptor: descriptor,
        bInheritHandle: 0,
    };
    let mut raw_key = std::ptr::null_mut();
    let created = unsafe {
        winapi::um::winreg::RegCreateKeyExW(winapi::um::winreg::HKEY_LOCAL_MACHINE,
            path.as_ptr(), 0, std::ptr::null_mut(), REG_OPTION_NON_VOLATILE,
            KEY_ALL_ACCESS | KEY_WOW64_64KEY, &mut attributes, &mut raw_key, std::ptr::null_mut())
    };
    if created != 0 {
        unsafe { winapi::um::winbase::LocalFree(descriptor as _); }
        return Err(std::io::Error::from_raw_os_error(created).into());
    }
    let key = unsafe { RegKey::from_raw_hkey(raw_key as _) };
    // Apply the same protected policy to an existing key, without a permissive creation window.
    let result = unsafe {
        winapi::um::winreg::RegSetKeySecurity(key.raw_handle() as _,
            OWNER_SECURITY_INFORMATION | GROUP_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION |
            PROTECTED_DACL_SECURITY_INFORMATION, descriptor)
    };
    unsafe { winapi::um::winbase::LocalFree(descriptor as _); }
    if result != 0 { return Err(std::io::Error::from_raw_os_error(result).into()); }
    key.set_value("Enabled", &0u32)?;
    key.set_value("MachineGuid", &machine_guid)?;
    if enabled { key.set_value("Enabled", &1u32)?; }
    log::info!("A2 administrative unattended policy changed: enabled={}", enabled);
    Ok(())
}

fn a2_prepare_unattended_service() -> ResultType<()> {
    use winapi::um::winsvc::*;
    unsafe {
        let manager = OpenSCManagerW(std::ptr::null(), std::ptr::null(), SC_MANAGER_CONNECT);
        if manager.is_null() { return Err(std::io::Error::last_os_error().into()); }
        let name: Vec<u16> = "Connect".encode_utf16().chain(Some(0)).collect();
        let service = OpenServiceW(manager, name.as_ptr(), SERVICE_QUERY_STATUS | SERVICE_CHANGE_CONFIG);
        if service.is_null() {
            let error = std::io::Error::last_os_error();
            CloseServiceHandle(manager);
            return Err(error.into());
        }
        let mut status: SERVICE_STATUS = std::mem::zeroed();
        let running = QueryServiceStatus(service, &mut status) != 0 && status.dwCurrentState == SERVICE_RUNNING;
        let changed = running && ChangeServiceConfigW(service, SERVICE_NO_CHANGE, SERVICE_AUTO_START,
            SERVICE_NO_CHANGE, std::ptr::null(), std::ptr::null(), std::ptr::null_mut(),
            std::ptr::null(), std::ptr::null(), std::ptr::null(), std::ptr::null()) != 0;
        let error = std::io::Error::last_os_error();
        CloseServiceHandle(service);
        CloseServiceHandle(manager);
        if !running { bail!("Connect service must already be running"); }
        if !changed { return Err(error.into()); }
    }
    Ok(())
}
