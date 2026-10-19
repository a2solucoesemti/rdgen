// Isolated Windows CI harness. It never runs RustDesk or connects to an A2 server.
extern crate self as hbb_common;
pub use anyhow;
use anyhow::bail;
use std::{ffi::OsString, sync::atomic::{AtomicBool, Ordering}, time::Duration};
use winreg::{enums::*, RegKey};
use windows_service::{
    define_windows_service, service::{ServiceAccess, ServiceControl, ServiceControlAccept,
        ServiceErrorControl, ServiceExitCode, ServiceInfo, ServiceStartType, ServiceState,
        ServiceStatus, ServiceType}, service_control_handler::{self, ServiceControlHandlerResult},
    service_dispatcher, service_manager::{ServiceManager, ServiceManagerAccess},
};
type ResultType<T> = anyhow::Result<T>;
static ADMIN: AtomicBool = AtomicBool::new(true);
static CREDENTIAL: AtomicBool = AtomicBool::new(true);
fn is_elevated(_: Option<u32>) -> ResultType<bool> { Ok(ADMIN.load(Ordering::SeqCst)) }
fn is_installed() -> bool { true }
fn is_cur_exe_the_installed() -> bool { true }
pub mod ipc {
    pub fn get_config(name: &str) -> crate::ResultType<Option<String>> {
        Ok(match name {
            "a2-consent-policy-version" => Some("1".to_owned()),
            "permanent-password-storage-and-salt" => Some("ci-hash\nci-salt".to_owned()),
            _ => None,
        })
    }
}
pub mod config {
    pub fn local_permanent_password_storage_is_usable_for_auth(_: &str, _: &str) -> bool {
        crate::CREDENTIAL.load(std::sync::atomic::Ordering::SeqCst)
    }
}
include!(concat!(env!("CARGO_MANIFEST_DIR"), "/a2_auth_policy.rs"));
include!(concat!(env!("CARGO_MANIFEST_DIR"), "/a2_consent_windows.rs"));

define_windows_service!(fixture_service_entry, fixture_service);
fn fixture_service(_: Vec<OsString>) {
    let (sender, receiver) = std::sync::mpsc::channel();
    let handle = service_control_handler::register("Connect", move |control| {
        match control {
            ServiceControl::Stop => { let _ = sender.send(()); ServiceControlHandlerResult::NoError }
            ServiceControl::Interrogate => ServiceControlHandlerResult::NoError,
            _ => ServiceControlHandlerResult::NotImplemented,
        }
    }).unwrap();
    let status = |state, accepted| ServiceStatus {
        service_type: ServiceType::OWN_PROCESS, current_state: state,
        controls_accepted: accepted, exit_code: ServiceExitCode::Win32(0),
        checkpoint: 0, wait_hint: Duration::from_secs(0), process_id: None,
    };
    handle.set_service_status(status(ServiceState::Running, ServiceControlAccept::STOP)).unwrap();
    let _ = receiver.recv();
    handle.set_service_status(status(ServiceState::Stopped, ServiceControlAccept::empty())).unwrap();
}

fn main() -> ResultType<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|arg| arg == "--service") {
        service_dispatcher::start("Connect", fixture_service_entry)?;
        return Ok(());
    }
    if std::env::var("GITHUB_ACTIONS").as_deref() != Ok("true") {
        bail!("This harness may run only in isolated CI");
    }
    if args.iter().any(|arg| arg == "--probe-portable") {
        assert!(a2_unattended_consent_exists());
        assert!(!a2_unattended_authorized());
        println!("Portable executable rejected despite an existing machine grant");
        return Ok(());
    }
    if args.iter().any(|arg| arg == "--revoke") {
        a2_set_unattended_consent(false)?;
        assert!(!a2_unattended_consent_exists());
        assert!(!a2_unattended_authorized());
        return Ok(());
    }
    let manager = ServiceManager::local_computer(None::<&str>,
        ServiceManagerAccess::CONNECT | ServiceManagerAccess::CREATE_SERVICE)?;
    let info = ServiceInfo {
        name: "Connect".into(), display_name: "A2 CI fixture - no network".into(),
        service_type: ServiceType::OWN_PROCESS, start_type: ServiceStartType::OnDemand,
        error_control: ServiceErrorControl::Normal, executable_path: std::env::current_exe()?,
        launch_arguments: vec!["--service".into()], dependencies: vec![],
        account_name: None, account_password: None,
    };
    let service = manager.create_service(&info, ServiceAccess::START | ServiceAccess::STOP | ServiceAccess::QUERY_STATUS | ServiceAccess::CHANGE_CONFIG | ServiceAccess::DELETE)?;
    service.start(&[] as &[&str])?;
    let mut running = false;
    for _ in 0..100 {
        if service.query_status()?.current_state == ServiceState::Running { running = true; break; }
        std::thread::sleep(Duration::from_millis(100));
    }
    assert!(running);
    a2_set_unattended_consent(false)?;
    assert!(!a2_unattended_authorized());
    ADMIN.store(false, Ordering::SeqCst);
    assert!(a2_set_unattended_consent(true).is_err());
    assert!(!a2_unattended_consent_exists());
    ADMIN.store(true, Ordering::SeqCst);
    CREDENTIAL.store(false, Ordering::SeqCst);
    assert!(a2_set_unattended_consent(true).is_err());
    assert!(!a2_unattended_consent_exists());
    CREDENTIAL.store(true, Ordering::SeqCst);
    a2_set_unattended_consent(true)?;
    assert!(a2_unattended_consent_exists());
    assert!(a2_unattended_authorized());
    let key = RegKey::predef(HKEY_LOCAL_MACHINE).open_subkey_with_flags(A2_CONSENT_KEY, KEY_ALL_ACCESS | KEY_WOW64_64KEY)?;
    key.set_value("MachineGuid", &"another-machine")?;
    assert!(!a2_unattended_authorized());
    a2_set_unattended_consent(true)?;
    assert!(a2_unattended_authorized());
    println!("Native consent registry, machine binding and service autostart tests passed");
    Ok(())
}
