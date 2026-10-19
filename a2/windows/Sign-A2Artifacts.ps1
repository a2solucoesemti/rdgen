[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$Path,
    [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{40}$')][string]$CertificateThumbprint,
    [Parameter(Mandatory)][string]$CertificateSha256,
    [Parameter(Mandatory)][string]$PublisherSubject,
    [Parameter(Mandatory)][uri]$TimestampUrl,
    [string]$SignTool = 'signtool.exe'
)
$ErrorActionPreference = 'Stop'
if ($TimestampUrl.Scheme -ne 'https') { throw 'Use the HTTPS RFC3161 endpoint supplied by the certificate provider' }
foreach ($file in $Path) {
    $resolved = (Resolve-Path -LiteralPath $file).Path
    if ([IO.Path]::GetExtension($resolved) -notin '.exe', '.msi') { throw 'Expected EXE or MSI' }
    # Uses the certificate store and hardware/cloud KSP. No PFX password in repo or argv.
    & $SignTool sign /sha1 $CertificateThumbprint /fd SHA256 /tr $TimestampUrl.AbsoluteUri /td SHA256 $resolved
    if ($LASTEXITCODE -ne 0) { throw 'Code signing failed' }
}
& "$PSScriptRoot/Test-A2Signature.ps1" -Path $Path -CertificateSha256 $CertificateSha256 -PublisherSubject $PublisherSubject
