Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$A2Versions = Get-Content (Join-Path $PSScriptRoot 'versions.json') -Raw | ConvertFrom-Json
function Assert-A2Windows {
    if ($env:OS -ne 'Windows_NT' -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
        throw 'This local recipe supports native Windows x64 only. Use 64-bit PowerShell on an AMD64 notebook.'
    }
}
function Invoke-A2Native {
    param([string]$File, [string[]]$Arguments)
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $File" }
}
function Receive-A2BuildFile {
    param([string]$Uri, [string]$Destination, [string]$Sha256 = '')
    if (-not $Uri.StartsWith('https://')) { throw 'HTTPS is required for build downloads' }
    if (-not (Test-Path $Destination)) {
        Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile "$Destination.partial"
        Move-Item "$Destination.partial" $Destination
    }
    if ($Sha256 -and (Get-FileHash $Destination -Algorithm SHA256).Hash -ne $Sha256) {
        throw "Download hash mismatch: $Destination. Remove only this cached download and retry."
    }
}
function Enable-A2Tools {
    param([string]$BuildRoot)
    $toolPaths = @(
        (Join-Path $BuildRoot 'tools\flutter\bin'),
        (Join-Path $BuildRoot "tools\cmake-$($A2Versions.cmakeVersion)-windows-x86_64\bin"),
        (Join-Path $BuildRoot 'tools'),
        (Join-Path $env:USERPROFILE '.cargo\bin'),
        "$env:ProgramFiles\Git\cmd", "$env:ProgramFiles\Git\bin",
        "$env:ProgramFiles\LLVM\bin", "$env:ProgramFiles\NASM"
    )
    $env:PATH = ($toolPaths -join ';') + ';' + $env:PATH
    $env:RUSTUP_TOOLCHAIN = $A2Versions.rustToolchain
    $env:LIBCLANG_PATH = "$env:ProgramFiles\LLVM\bin"
    $env:VCPKG_ROOT = Join-Path $BuildRoot 'vcpkg'
    $env:VCPKG_DEFAULT_TRIPLET = 'x64-windows-static'
    $env:VCPKG_DEFAULT_HOST_TRIPLET = 'x64-windows-static'
    $cache = Join-Path $BuildRoot 'vcpkg-cache'
    New-Item -ItemType Directory -Force $cache | Out-Null
    $env:VCPKG_BINARY_SOURCES = "clear;files,$cache,readwrite"
    # Old Rust/Flutter tools need the archive format supported by their pinned recipes.
    $env:CARGO_NET_GIT_FETCH_WITH_CLI = 'true'
}
function Enable-A2VisualStudio {
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vswhere)) { throw 'Visual Studio Build Tools 2022 not found; run Setup-LocalBuild.ps1 -Install' }
    $installation = & $vswhere -latest -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if (-not $installation) { throw 'Visual Studio 2022 C++ workload not found' }
    Import-Module (Join-Path $installation 'Common7\Tools\Microsoft.VisualStudio.DevShell.dll')
    Enter-VsDevShell -VsInstallPath $installation -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64' | Out-Null
    return $installation
}

function Test-A2ReversePatch {
    param([string]$Repository, [string]$Patch)
    $previous = $ErrorActionPreference
    try {
        # A negative check is expected for a pristine SDK, including in Windows PowerShell 5.1.
        $ErrorActionPreference = 'Continue'
        & git -C $Repository apply --reverse --check $Patch *> $null
        return ($LASTEXITCODE -eq 0)
    } finally { $ErrorActionPreference = $previous }
}
