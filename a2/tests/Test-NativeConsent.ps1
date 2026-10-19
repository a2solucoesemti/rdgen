#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Run only on isolated CI' }
$key = 'HKLM:\SOFTWARE\A2ConnectUnattendedConsentV1'
if (Get-Service Connect -ErrorAction SilentlyContinue) { throw 'Refusing to touch an existing Connect service' }
if (Test-Path $key) { throw 'Refusing to touch an existing consent policy' }
$fixture = Join-Path $env:RUNNER_TEMP 'a2-native-consent'
python "$PSScriptRoot/native_consent_fixture.py" $fixture
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare native fixture' }
try {
    cargo build --manifest-path "$fixture/Cargo.toml"
    if ($LASTEXITCODE -ne 0) { throw 'Native consent fixture did not compile' }
    $exe = Join-Path $fixture 'target/debug/a2-native-consent-test.exe'
    & $exe
    if ($LASTEXITCODE -ne 0) { throw 'Native consent fixture failed' }
    if ((Get-CimInstance Win32_Service -Filter "Name='Connect'").StartMode -ne 'Auto') { throw 'Service autostart not configured' }
    $acl = Get-Acl $key
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne 'S-1-5-32-544') { throw 'Consent owner is not Administrators' }
    if (-not $acl.AreAccessRulesProtected) { throw 'Consent DACL is not protected' }
    foreach ($rule in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Value -notin @('S-1-5-18', 'S-1-5-32-544')) {
            $write = [Security.AccessControl.RegistryRights]::SetValue -bor [Security.AccessControl.RegistryRights]::CreateSubKey -bor [Security.AccessControl.RegistryRights]::ChangePermissions -bor [Security.AccessControl.RegistryRights]::TakeOwnership
            if ($rule.RegistryRights -band $write) { throw 'Unprivileged write access to the machine grant' }
        }
    }
    $copy = Join-Path $fixture 'portable-copy.exe'
    Copy-Item $exe $copy
    & $copy --probe-portable
    if ($LASTEXITCODE -ne 0) { throw 'Portable process inherited installed authorization' }
    & $exe --revoke
    if ($LASTEXITCODE -ne 0) { throw 'Native revocation failed' }
    Write-Output 'Native administrative consent tests passed'
} finally {
    if (Get-Service Connect -ErrorAction SilentlyContinue) {
        Stop-Service Connect -Force -ErrorAction SilentlyContinue
        & "$env:SystemRoot/System32/sc.exe" delete Connect | Out-Null
    }
    if (Test-Path $key) { Remove-Item $key -Recurse -Force }
}
