[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$Path,
    [Parameter(Mandatory)][ValidatePattern('^[A-Fa-f0-9]{64}$')][string]$CertificateSha256,
    [Parameter(Mandatory)][string]$PublisherSubject
)
$ErrorActionPreference = 'Stop'
foreach ($item in $Path) {
    $file = Get-Item -LiteralPath $item -ErrorAction Stop
    if ($file.Extension -notin '.exe', '.msi') { throw 'Expected EXE or MSI' }
    $signature = Get-AuthenticodeSignature -LiteralPath $file.FullName
    if ($signature.Status -ne 'Valid') { throw "Invalid Authenticode signature: $($file.Name)" }
    if (-not $signature.TimeStamperCertificate) { throw "Missing timestamp: $($file.Name)" }
    $cert = $signature.SignerCertificate
    $hash = [Security.Cryptography.SHA256]::Create()
    try { $fingerprint = ([BitConverter]::ToString($hash.ComputeHash($cert.RawData))).Replace('-', '') }
    finally { $hash.Dispose() }
    if ($fingerprint -cne $CertificateSha256.ToUpperInvariant()) { throw 'Untrusted signing certificate' }
    if ($cert.Subject -cne $PublisherSubject) { throw 'Unexpected publisher subject' }
    if (-not ($cert.Extensions | Where-Object {
        $_ -is [Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension] -and
        ($_.EnhancedKeyUsages.Value -contains '1.3.6.1.5.5.7.3.3')
    })) { throw 'Certificate is not enabled for code signing' }
    Write-Output "Verified signed A2 artifact: $($file.Name)"
}
