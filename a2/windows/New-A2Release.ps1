[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Artifact,
    [Parameter(Mandatory)][ValidateSet('Connect', 'ConnectAdmin')][string]$Product,
    [Parameter(Mandatory)][ValidateSet('stable', 'beta', 'server')][string]$Channel,
    [Parameter(Mandatory)][ValidateSet('x86_64', 'aarch64')][string]$Architecture,
    [Parameter(Mandatory)][version]$Version,
    [Parameter(Mandatory)][long]$Sequence,
    [Parameter(Mandatory)][string]$ArtifactSignerSha256,
    [Parameter(Mandatory)][string]$PublisherSubject,
    [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{40}$')][string]$ManifestCertificateThumbprint,
    [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ManifestSignerSha256,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [ValidateRange(10240, 999999)][int]$MinWindowsBuild = 10240
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/Update-Trust.ps1"
if ($Sequence -le 0 -or $Version.ToString() -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid version or sequence' }
$file = Get-Item -LiteralPath $Artifact
if ($file.Extension -cne '.msi') { throw 'Only MSI releases are supported at this stage' }
& "$PSScriptRoot/Test-A2Signature.ps1" -Path $file.FullName -CertificateSha256 $ArtifactSignerSha256 -PublisherSubject $PublisherSubject
Test-A2MsiIdentity $file.FullName $Product $Version $Architecture
$certificate = Get-Item "Cert:\CurrentUser\My\$ManifestCertificateThumbprint"
if (-not $certificate.HasPrivateKey -or (Get-A2CertificateHash $certificate) -cne $ManifestSignerSha256.ToUpperInvariant()) {
    throw 'Manifest signing key missing or untrusted'
}
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Use a new release directory; never overwrite a release' }
$null = New-Item -ItemType Directory -Path $OutputDirectory
$name = "$Product-$Version-$Architecture.msi"
$manifest = [ordered]@{
    schema = 1; product = $Product; channel = $Channel; platform = 'windows'
    architecture = $Architecture; version = $Version.ToString(); sequence = $Sequence
    createdAt = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    expiresAt = [DateTimeOffset]::UtcNow.AddDays(14).ToString("yyyy-MM-ddTHH:mm:ssZ")
    format = 'msi'; minWindowsBuild = $MinWindowsBuild
    url = "https://connect.a2ti.com.br/updates/$Product/$Channel/windows/$Architecture/$name"
    sha256 = (Get-FileHash $file.FullName -Algorithm SHA256).Hash
    size = $file.Length
}
$content = [Text.UTF8Encoding]::new($false).GetBytes(($manifest | ConvertTo-Json -Compress))
$info = [Security.Cryptography.Pkcs.ContentInfo]::new($content)
$cms = [Security.Cryptography.Pkcs.SignedCms]::new($info, $true)
$signer = [Security.Cryptography.Pkcs.CmsSigner]::new($certificate)
$signer.DigestAlgorithm = [Security.Cryptography.Oid]::new('2.16.840.1.101.3.4.2.1')
$cms.ComputeSignature($signer)
$signature = $cms.Encode()
Test-A2ManifestSignature $content $signature $ManifestSignerSha256
[IO.File]::WriteAllBytes((Join-Path $OutputDirectory 'manifest.json'), $content)
[IO.File]::WriteAllBytes((Join-Path $OutputDirectory 'manifest.json.p7s'), $signature)
Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $OutputDirectory $name)
Write-Output 'Release preparada localmente. Publicar o diretório de forma atômica após homologação.'
