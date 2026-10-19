[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Customer,
    [ValidateSet('Connect', 'ConnectAdmin')][string]$Product = 'Connect'
)
$ErrorActionPreference = 'Stop'
# No credentials, TOML contents or remote transmission. This command is read-only.
$exe = Join-Path $env:ProgramFiles "$Product/$Product.exe"
if (-not (Test-Path -LiteralPath $exe)) { throw 'Installed A2 executable not found' }
$os = Get-CimInstance Win32_OperatingSystem
$service = Get-CimInstance Win32_Service -Filter "Name='$Product'"
$idOutput = & $exe --get-id
if ($LASTEXITCODE -ne 0) { throw 'Could not read device ID' }
$id = ($idOutput | Out-String).Trim()
if ($id -notmatch '^[A-Za-z0-9_-]{1,64}$') { throw 'Unexpected device ID response' }
[ordered]@{
    schema = 1; customer = $Customer; computerName = $env:COMPUTERNAME
    product = $Product; rustdeskId = $id
    operatingSystem = $os.Caption; windowsBuild = $os.BuildNumber
    version = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
    deviceType = $(if ($os.ProductType -eq 1) { 'workstation' } else { 'server' })
    serviceState = $(if ($service) { $service.State } else { 'NotInstalled' })
    serviceStartMode = $(if ($service) { $service.StartMode } else { 'NotInstalled' })
    updateState = 'not-managed'
    collectedAt = [DateTimeOffset]::UtcNow.ToString('o')
} | ConvertTo-Json
