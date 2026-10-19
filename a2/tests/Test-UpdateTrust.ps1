$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/../windows/Update-Trust.ps1"
$script:count = 0
function Reject([scriptblock]$Action) {
    $failed = $false
    try { & $Action } catch { $failed = $true }
    if (-not $failed) { throw "Unsafe input unexpectedly accepted at negative case $script:count : $Action" }
    $script:count++
}
$valid = @{
    schema=1; product='Connect'; channel='beta'; platform='windows'; architecture='x86_64'
    format='msi'; version='1.4.10'; sequence=12; sha256=('A' * 64); size=1024
    createdAt=[DateTimeOffset]::UtcNow.AddMinutes(-1).ToString('yyyy-MM-ddTHH:mm:ssZ')
    expiresAt=[DateTimeOffset]::UtcNow.AddDays(1).ToString('yyyy-MM-ddTHH:mm:ssZ')
    minWindowsBuild=10240; url='https://connect.a2ti.com.br/updates/Connect/beta/windows/x86_64/Connect.msi'
}
Assert-A2Manifest ([pscustomobject]$valid) 'Connect' 'beta' 'x86_64' 11
Reject { Assert-A2Manifest ([pscustomobject]$valid) 'ConnectAdmin' 'beta' 'x86_64' 11 }
Reject { Assert-A2Manifest ([pscustomobject]$valid) 'Connect' 'stable' 'x86_64' 11 }
Reject { Assert-A2Manifest ([pscustomobject]$valid) 'Connect' 'beta' 'aarch64' 11 }
Reject { Assert-A2Manifest ([pscustomobject]$valid) 'Connect' 'beta' 'x86_64' 12 }
foreach ($url in @('http://connect.a2ti.com.br/updates/a.msi',
    'https://evil.example/updates/a.msi', 'https://connect.a2ti.com.br.evil.example/updates/a.msi',
    'https://user@connect.a2ti.com.br/updates/a.msi', 'https://connect.a2ti.com.br:444/updates/a.msi',
    'https://connect.a2ti.com.br/updates/%2e%2e/a.msi', 'https://connect.a2ti.com.br/updates/../a.msi',
    'https://connect.a2ti.com.br/updates/a.msi?redirect=evil')) {
    Reject { $null = Assert-A2Url $url }
}
$expired = $valid.Clone(); $expired.expiresAt = [DateTimeOffset]::UtcNow.AddDays(-1).ToString('yyyy-MM-ddTHH:mm:ssZ')
Reject { Assert-A2Manifest ([pscustomobject]$expired) 'Connect' 'beta' 'x86_64' 11 }
$badHash = $valid.Clone(); $badHash.sha256 = 'bad'
Reject { Assert-A2Manifest ([pscustomobject]$badHash) 'Connect' 'beta' 'x86_64' 11 }
$badSize = $valid.Clone(); $badSize.size = '1024'
Reject { Assert-A2Manifest ([pscustomobject]$badSize) 'Connect' 'beta' 'x86_64' 11 }
Reject { Test-A2ManifestSignature ([byte[]]@(1,2)) ([byte[]]@(3,4)) ('A' * 64) }
# Exercise a valid detached CMS signature using an ephemeral CI-only certificate.
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Run CMS integration tests only on isolated CI' }
$cert = New-SelfSignedCertificate -Subject 'CN=A2 CI Test Only' -Type CodeSigningCert -CertStoreLocation 'Cert:\CurrentUser\My'
$store = [Security.Cryptography.X509Certificates.X509Store]::new('Root', 'LocalMachine')
try {
    $store.Open('ReadWrite'); $store.Add($cert)
    $content = [Text.Encoding]::UTF8.GetBytes('signed A2 test content')
    $cms = [Security.Cryptography.Pkcs.SignedCms]::new([Security.Cryptography.Pkcs.ContentInfo]::new($content), $true)
    $signer = [Security.Cryptography.Pkcs.CmsSigner]::new($cert)
    $signer.DigestAlgorithm = [Security.Cryptography.Oid]::new('2.16.840.1.101.3.4.2.1')
    $cms.ComputeSignature($signer)
    $signature = $cms.Encode()
    $pin = Get-A2CertificateHash $cert
    Test-A2ManifestSignature $content $signature $pin
    Reject { Test-A2ManifestSignature ([Text.Encoding]::UTF8.GetBytes('tampered')) $signature $pin }
    Reject { Test-A2ManifestSignature $content $signature ('0' * 64) }
} finally {
    $store.Remove($cert); $store.Close()
    Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -ErrorAction SilentlyContinue
}
Write-Output "Update trust negative tests passed: $script:count"
