#Requires -RunAsAdministrator
#Requires -PSEdition Desktop
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Connect', 'ConnectAdmin')][string]$Product,
    [Parameter(Mandatory)][ValidateSet('stable', 'beta', 'server')][string]$Channel,
    [Parameter(Mandatory)][ValidateSet('x86_64', 'aarch64')][string]$Architecture,
    [Parameter(Mandatory)][version]$InstalledVersion,
    # Pins come from the administrator's trusted deployment, never the manifest.
    [Parameter(Mandatory)][string]$ManifestSignerSha256,
    [Parameter(Mandatory)][string]$ArtifactSignerSha256,
    [Parameter(Mandatory)][string]$PublisherSubject
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/Update-Trust.ps1"
$nativeArchitecture = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment').PROCESSOR_ARCHITECTURE
$expected = switch ($nativeArchitecture) { 'AMD64' { 'x86_64' }; 'ARM64' { 'aarch64' }; default { throw 'Unsupported Windows architecture' } }
if ($Architecture -cne $expected) { throw 'Wrong native architecture' }
$root = Join-Path $env:ProgramData 'A2ConnectUpdates'
Initialize-A2ProtectedDirectory $root
$slot = Join-Path $root "$Product-$Channel-$Architecture"
Initialize-A2ProtectedDirectory $slot
$lockPath = Join-Path $slot 'staging.lock'
$lock = [IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None')
$work = Join-Path $slot ([Guid]::NewGuid().ToString('N'))
try {
    $null = New-Item -ItemType Directory -Path $work
    $base = "https://connect.a2ti.com.br/updates/$Product/$Channel/windows/$Architecture"
    # Redirects are disabled, including HTTPS-to-HTTPS cross-origin redirects.
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $manifestFile = Join-Path $work 'manifest.json'
    $signatureFile = Join-Path $work 'manifest.json.p7s'
    Invoke-WebRequest -UseBasicParsing -MaximumRedirection 0 -Uri "$base/manifest.json" -OutFile $manifestFile
    Invoke-WebRequest -UseBasicParsing -MaximumRedirection 0 -Uri "$base/manifest.json.p7s" -OutFile $signatureFile
    if ((Get-Item $manifestFile).Length -gt 64KB -or (Get-Item $signatureFile).Length -gt 64KB) { throw 'Oversized manifest or signature' }
    Test-A2ManifestSignature ([IO.File]::ReadAllBytes($manifestFile)) ([IO.File]::ReadAllBytes($signatureFile)) $ManifestSignerSha256
    $manifest = Get-Content -Raw -LiteralPath $manifestFile | ConvertFrom-Json
    $stateFile = Join-Path $slot 'highest-sequence.txt'
    [long]$previous = 0
    if (Test-Path $stateFile) { $previous = [long](Get-Content -Raw $stateFile) }
    Assert-A2Manifest $manifest $Product $Channel $Architecture $previous
    if ([version]$manifest.version -le $InstalledVersion) { throw 'Update must be newer than installed version' }
    $build = [Environment]::OSVersion.Version.Build
    if ($build -lt $manifest.minWindowsBuild) { throw 'Windows build is incompatible' }
    $artifact = Join-Path $work 'package.msi'
    $url = Assert-A2Url $manifest.url
    Invoke-WebRequest -UseBasicParsing -MaximumRedirection 0 -Uri $url -OutFile $artifact
    if ((Get-Item $artifact).Length -ne $manifest.size) { throw 'Artifact size mismatch' }
    if ((Get-FileHash $artifact -Algorithm SHA256).Hash -cne $manifest.sha256.ToUpperInvariant()) { throw 'Artifact SHA-256 mismatch' }
    & "$PSScriptRoot/Test-A2Signature.ps1" -Path $artifact -CertificateSha256 $ArtifactSignerSha256 -PublisherSubject $PublisherSubject
    Test-A2MsiIdentity $artifact $Product ([version]$manifest.version) $Architecture
    # Record anti-replay state only after full verification; do not mark installed.
    $nextState = Join-Path $slot 'sequence.next'
    [IO.File]::WriteAllText($nextState, [string]$manifest.sequence)
    Move-Item -Force $nextState $stateFile
    $entry = '{0} staged product={1} channel={2} version={3} sequence={4}' -f [DateTimeOffset]::UtcNow.ToString('o'), $Product, $Channel, $manifest.version, $manifest.sequence
    Add-Content -LiteralPath (Join-Path $slot 'updates.log') -Value $entry
    Write-Output "Pacote validado e preparado em $work. Nenhuma instalação ou reinicialização foi executada."
} catch {
    if (Test-Path $work) { Remove-Item -LiteralPath $work -Recurse -Force }
    throw
} finally { $lock.Dispose() }
