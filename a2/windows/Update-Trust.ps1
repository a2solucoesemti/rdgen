# Shared validation for release preparation and download staging. No installation.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security

function Initialize-A2ProtectedDirectory([string]$Path) {
    $trusted = @('S-1-5-18', 'S-1-5-32-544')
    if (Test-Path -LiteralPath $Path) {
        $item = Get-Item -Force -LiteralPath $Path
        if (-not $item.PSIsContainer -or $item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Unsafe update directory' }
        $acl = Get-Acl -LiteralPath $Path
        if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $trusted) { throw 'Untrusted update directory owner' }
        foreach ($rule in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
            if ($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Value -notin $trusted) {
                throw 'Update directory grants access to an untrusted principal'
            }
        }
        return
    }
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
    foreach ($sid in $trusted) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            [Security.Principal.SecurityIdentifier]::new($sid), 'FullControl',
            'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    # Windows PowerShell / .NET Framework: creates with the protected ACL atomically.
    $null = [IO.Directory]::CreateDirectory($Path, $acl)
    Initialize-A2ProtectedDirectory $Path
}

function Assert-A2Url([string]$Value) {
    $url = [Uri]$Value
    if (-not $url.IsAbsoluteUri -or $url.Scheme -cne 'https' -or
        $url.Host -cne 'connect.a2ti.com.br' -or $url.Port -ne 443 -or
        $url.UserInfo -or $url.Query -or $url.Fragment -or
        -not $url.AbsolutePath.StartsWith('/updates/', [StringComparison]::Ordinal) -or
        $Value -match '%|\\|/\.\.?(/|$)') {
        throw 'Only direct A2 HTTPS update URLs are allowed'
    }
    return $url
}

function Receive-A2File([string]$Url, [string]$Destination, [long]$MaxBytes) {
    $uri = Assert-A2Url $Url
    if ($MaxBytes -le 0 -or $MaxBytes -gt 2GB) { throw 'Invalid download limit' }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $request = [Net.HttpWebRequest]::Create($uri)
    $request.AllowAutoRedirect = $false
    $request.Timeout = 30000
    $request.ReadWriteTimeout = 30000
    $request.MaximumResponseHeadersLength = 64
    $request.UserAgent = 'A2Connect-Staging/1'
    $response = $null; $inputStream = $null; $outputStream = $null
    $created = $false; $complete = $false
    try {
        $response = $request.GetResponse()
        if ([int]$response.StatusCode -ne 200) { throw 'A2 update download requires HTTP 200 without redirects' }
        if ($response.ContentLength -gt $MaxBytes) { throw 'Download exceeds declared limit' }
        $inputStream = $response.GetResponseStream()
        $outputStream = [IO.File]::Open($Destination, 'CreateNew', 'Write', 'None')
        $created = $true
        $buffer = New-Object byte[] 65536
        [long]$total = 0
        $timer = [Diagnostics.Stopwatch]::StartNew()
        while ($true) {
            if ($timer.Elapsed.TotalMinutes -gt 10) { throw 'Download time limit exceeded' }
            $read = $inputStream.Read($buffer, 0, $buffer.Length)
            if ($read -eq 0) { break }
            $total += $read
            if ($total -gt $MaxBytes) { throw 'Download exceeds declared limit' }
            $outputStream.Write($buffer, 0, $read)
        }
        $outputStream.Flush($true)
        $complete = $true
    } finally {
        if ($outputStream) { $outputStream.Dispose() }
        if ($inputStream) { $inputStream.Dispose() }
        if ($response) { $response.Dispose() }
        $request.Abort()
        if ($created -and -not $complete) { Remove-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue }
    }
}

function Get-A2CertificateHash($Certificate) {
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($Certificate.RawData))).Replace('-', '') }
    finally { $hash.Dispose() }
}

function Test-A2ManifestSignature([byte[]]$Content, [byte[]]$Signature, [string]$PinnedSha256) {
    if ($PinnedSha256 -notmatch '^[a-fA-F0-9]{64}$') { throw 'Missing release trust pin' }
    $info = [Security.Cryptography.Pkcs.ContentInfo]::new($Content)
    $cms = [Security.Cryptography.Pkcs.SignedCms]::new($info, $true)
    $cms.Decode($Signature)
    if (-not $cms.Detached -or $cms.ContentInfo.ContentType.Value -ne '1.2.840.113549.1.7.1' -or
        [Convert]::ToBase64String($cms.ContentInfo.Content) -cne [Convert]::ToBase64String($Content)) {
        throw 'CMS must authenticate the exact external manifest bytes'
    }
    if ($cms.SignerInfos.Count -ne 1) { throw 'Expected exactly one release signer' }
    $signer = $cms.SignerInfos[0]
    if ($signer.DigestAlgorithm.Value -ne '2.16.840.1.101.3.4.2.1') { throw 'Release signature must use SHA-256' }
    if (-not $signer.Certificate -or
        (Get-A2CertificateHash $signer.Certificate) -cne $PinnedSha256.ToUpperInvariant()) {
        throw 'Untrusted release signer'
    }
    # Reject unpinned certificates before chain validation can fetch AIA/CRL URLs.
    # false verifies the detached signature and the trusted signer's chain.
    $cms.CheckSignature($false)
}

function Test-A2MsiIdentity([string]$Path, [string]$Product, [version]$Version, [string]$Architecture) {
    $installer = New-Object -ComObject WindowsInstaller.Installer
    $database = $installer.OpenDatabase($Path, 0)
    function Read-MsiProperty([string]$Name) {
        $view = $database.OpenView("SELECT ``Value`` FROM ``Property`` WHERE ``Property``='$Name'")
        $view.Execute(); $row = $view.Fetch()
        if (-not $row) { throw 'MSI property missing' }
        return $row.StringData(1)
    }
    if ((Read-MsiProperty 'ProductName') -cne $Product -or
        [version](Read-MsiProperty 'ProductVersion') -ne $Version) { throw 'MSI product/version mismatch' }
    $template = $database.SummaryInformation(0).Property(7).Split(';')[0]
    $expectedTemplate = if ($Architecture -eq 'aarch64') { 'Arm64' } else { 'x64' }
    if ($template -ine $expectedTemplate) { throw 'MSI architecture mismatch' }
}

function Assert-A2Manifest($Manifest, [string]$Product, [string]$Channel, [string]$Architecture, [long]$LastSequence) {
    if ($Manifest.schema -ne 1 -or $Manifest.product -cne $Product -or
        $Manifest.channel -cne $Channel -or $Manifest.platform -cne 'windows' -or
        $Manifest.architecture -cne $Architecture -or $Manifest.format -cne 'msi') {
        throw 'Incompatible update manifest'
    }
    if ($Manifest.version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid update version' }
    if ($Manifest.sequence -isnot [long] -and $Manifest.sequence -isnot [int]) { throw 'Invalid sequence type' }
    if ($Manifest.sequence -le $LastSequence) { throw 'Stale or replayed release sequence' }
    $now = [DateTimeOffset]::UtcNow
    if ($Manifest.createdAt -notmatch 'Z$' -or $Manifest.expiresAt -notmatch 'Z$') { throw 'UTC dates required' }
    $created = [DateTimeOffset]::Parse($Manifest.createdAt)
    $expires = [DateTimeOffset]::Parse($Manifest.expiresAt)
    if ($created -gt $now.AddMinutes(5) -or $expires -le $now -or
        $expires -le $created -or ($expires - $created).TotalDays -gt 31) { throw 'Invalid release lifetime' }
    if ($Manifest.sha256 -notmatch '^[a-fA-F0-9]{64}$' -or
        ($Manifest.size -isnot [long] -and $Manifest.size -isnot [int])) { throw 'Invalid artifact integrity fields' }
    if ($Manifest.size -le 0 -or $Manifest.size -gt 2GB) { throw 'Invalid artifact size' }
    if ($Manifest.minWindowsBuild -isnot [int] -and $Manifest.minWindowsBuild -isnot [long]) { throw 'Invalid Windows build' }
    if ($Manifest.minWindowsBuild -lt 10240) { throw 'Unsupported Windows minimum' }
    $null = Assert-A2Url $Manifest.url
    if (-not $Manifest.url.EndsWith('.msi', [StringComparison]::Ordinal)) { throw 'Only MSI staging is supported' }
}
