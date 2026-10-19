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
# Verify the protected directory primitive and reject a broadened DACL.
$directory = Join-Path $env:TEMP ([Guid]::NewGuid().ToString('N'))
$unsigned = Join-Path $env:TEMP (([Guid]::NewGuid().ToString('N')) + '.exe')
try {
    Initialize-A2ProtectedDirectory $directory
    Initialize-A2ProtectedDirectory $directory
    $acl = Get-Acl $directory
    $rule = [Security.AccessControl.FileSystemAccessRule]::new(
        [Security.Principal.SecurityIdentifier]::new('S-1-1-0'), 'ReadAndExecute', 'Allow')
    $acl.AddAccessRule($rule); Set-Acl $directory $acl
    Reject { Initialize-A2ProtectedDirectory $directory }
    [IO.File]::WriteAllText($unsigned, 'Unsigned test fixture')
    Reject { & "$PSScriptRoot/../windows/Test-A2Signature.ps1" -Path $unsigned -CertificateSha256 ('0' * 64) -PublisherSubject 'CN=A2 CI' }
} finally {
    Remove-Item -LiteralPath $directory -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $unsigned -Force -ErrorAction SilentlyContinue
}
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
# Test bounded streaming/redirect handling against a disposable loopback fixture.
# Origin/TLS policy is tested separately above; only this fixture replaces the URL guard.
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$listener.Start(); $port = $listener.LocalEndpoint.Port; $listener.Stop()
$ready = Join-Path $env:TEMP ([Guid]::NewGuid().ToString('N'))
$download = Join-Path $env:TEMP ([Guid]::NewGuid().ToString('N'))
$server = Start-Job -ArgumentList $port, $ready -ScriptBlock {
    param($Port, $Ready)
    $http = [Net.HttpListener]::new()
    $http.Prefixes.Add("http://127.0.0.1:$Port/")
    try {
        $http.Start(); [IO.File]::WriteAllText($Ready, 'ready')
        for ($i = 0; $i -lt 4; $i++) {
            $context = $http.GetContext()
            $response = $context.Response
            try {
                if ($context.Request.Url.AbsolutePath -eq '/redirect') {
                    $response.StatusCode = 302
                    $response.RedirectLocation = 'https://invalid.example/'
                    $response.ContentLength64 = 0
                } else {
                    $text = if ($context.Request.Url.AbsolutePath -eq '/ok') { 'okay' } else { 'TOOLARGE' }
                    $bytes = [Text.Encoding]::ASCII.GetBytes($text)
                    if ($context.Request.Url.AbsolutePath -eq '/chunked') { $response.SendChunked = $true }
                    else { $response.ContentLength64 = $bytes.Length }
                    $response.OutputStream.Write($bytes, 0, $bytes.Length)
                }
            } finally { $response.Close() }
        }
    } finally { $http.Close() }
}
$urlGuard = ${function:Assert-A2Url}
try {
    $deadline = [DateTime]::UtcNow.AddSeconds(15)
    while (-not (Test-Path $ready)) {
        if ([DateTime]::UtcNow -gt $deadline) { throw 'Loopback test server did not start' }
        Start-Sleep -Milliseconds 100
    }
    function Assert-A2Url([string]$Value) { return [Uri]$Value }
    Receive-A2File "http://127.0.0.1:$port/ok" $download 4
    if ([IO.File]::ReadAllText($download) -cne 'okay') { throw 'Download content mismatch' }
    Remove-Item -LiteralPath $download -Force
    foreach ($case in @('large', 'chunked', 'redirect')) {
        Reject { Receive-A2File "http://127.0.0.1:$port/$case" $download 4 }
        if (Test-Path $download) { throw 'Incomplete or oversized download was not removed' }
    }
} finally {
    Set-Item Function:Assert-A2Url -Value $urlGuard
    Stop-Job $server -ErrorAction SilentlyContinue
    Remove-Job $server -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ready, $download -Force -ErrorAction SilentlyContinue
}
Write-Output "Update trust negative tests passed: $script:count"
