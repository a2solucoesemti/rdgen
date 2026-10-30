[CmdletBinding()]
param([string]$BuildRoot = 'C:\A2ConnectBuild', [switch]$Install)
. "$PSScriptRoot\Common.ps1"
Assert-A2Windows
if ($BuildRoot -match '\s' -or -not [IO.Path]::IsPathRooted($BuildRoot)) { throw 'Use an absolute build path without spaces' }
New-Item -ItemType Directory -Force $BuildRoot, "$BuildRoot\tools", "$BuildRoot\downloads", "$BuildRoot\logs" | Out-Null
$log = Join-Path $BuildRoot ('logs\setup-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
Start-Transcript -Path $log | Out-Null
try {
    Enable-A2Tools $BuildRoot
    $packages = @(
        @{Command='git'; Id='Git.Git'; Extra=@()},
        @{Command='py'; Id='Python.Python.3.11'; Extra=@()},
        @{Command='rustup'; Id='Rustlang.Rustup'; Extra=@()},
        @{Command='clang'; Id='LLVM.LLVM'; Extra=@('--version','15.0.6')},
        @{Command='nasm'; Id='NASM.NASM'; Extra=@()},
        @{Command='dotnet'; Id='Microsoft.DotNet.SDK.8'; Extra=@()}
    )
    $python311Present = $false
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $previous = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & py -3.11 --version *> $null
            $python311Present = ($LASTEXITCODE -eq 0)
        } finally { $ErrorActionPreference = $previous }
    }
    $missing = @($packages | Where-Object {
        if ($_.Id -eq 'Python.Python.3.11') { -not $python311Present }
        elseif ($_.Id -eq 'LLVM.LLVM') { -not (Test-Path "$env:ProgramFiles\LLVM\bin\libclang.dll") }
        else { -not (Get-Command $_.Command -ErrorAction SilentlyContinue) }
    })
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    $hasCpp = $false
    if (Test-Path $vswhere) {
        $vs = & $vswhere -latest -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
        $hasCpp = [bool]$vs
    }
    Write-Host 'A2 local build: Windows x64, preview only; no Connect services will be changed.'
    if (-not $Install) {
        $missing | ForEach-Object { Write-Host ('Missing: ' + $_.Id) }
        if (-not $hasCpp) { Write-Host 'Missing: Visual Studio 2022 C++ workload, ATL/MFC and Windows SDK' }
        Write-Host 'Run again with -Install to install prerequisites and download pinned SDKs.'
        return
    }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Install Microsoft App Installer (winget) from Microsoft Store, then rerun' }
    foreach ($package in $missing) {
        $arguments = @('install','--exact','--id',$package.Id,'--source','winget','--accept-source-agreements','--accept-package-agreements','--disable-interactivity') + $package.Extra
        Invoke-A2Native 'winget' $arguments
    }
    if (-not $hasCpp) {
        $override = '--wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --add Microsoft.VisualStudio.Component.VC.ATLMFC --add Microsoft.VisualStudio.Component.VC.v142.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.22621'
        Invoke-A2Native 'winget' @('install','--exact','--id','Microsoft.VisualStudio.2022.BuildTools','--source','winget','--override',$override,'--accept-source-agreements','--accept-package-agreements','--disable-interactivity')
    }
    if ($hasCpp) {
        $complete = & $vswhere -latest -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 Microsoft.VisualStudio.Component.VC.ATLMFC Microsoft.VisualStudio.Component.VC.v142.x86.x64 Microsoft.VisualStudio.Component.Windows11SDK.22621 -property installationPath
        if (-not $complete) {
            $installer = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vs_installer.exe"
            Invoke-A2Native $installer @('modify','--installPath',$vs,'--passive','--norestart','--add','Microsoft.VisualStudio.Component.VC.ATLMFC','--add','Microsoft.VisualStudio.Component.VC.v142.x86.x64','--add','Microsoft.VisualStudio.Component.Windows11SDK.22621')
        }
    }
    $env:PATH = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
    Enable-A2Tools $BuildRoot
    foreach ($command in @('git','py','rustup','clang','nasm','dotnet')) {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Missing $command after installation. Reopen PowerShell and rerun." }
    }
    Invoke-A2Native 'rustup' @('toolchain','install',$A2Versions.rustToolchain,'--profile','minimal','--component','rustfmt')
    # Verify this Python version explicitly, rather than silently using Python 3.14.
    Invoke-A2Native 'py' @('-3.11','--version')
    if (-not (Test-Path "$BuildRoot\tools\flutter\bin\flutter.bat")) {
        $releases = Invoke-RestMethod 'https://storage.googleapis.com/flutter_infra_release/releases/releases_windows.json'
        $release = @($releases.releases | Where-Object { $_.version -eq $A2Versions.flutterVersion -and $_.channel -eq 'stable' }) | Select-Object -First 1
        if (-not $release -or -not $release.sha256) { throw 'Pinned Flutter release/checksum not found' }
        $zip = "$BuildRoot\downloads\flutter-$($A2Versions.flutterVersion).zip"
        Receive-A2BuildFile ("https://storage.googleapis.com/flutter_infra_release/" + $release.archive) $zip $release.sha256
        Expand-Archive -LiteralPath $zip -DestinationPath "$BuildRoot\tools" -Force
    }
    $cmakeName = "cmake-$($A2Versions.cmakeVersion)-windows-x86_64.zip"
    $cmakeUrl = "https://github.com/Kitware/CMake/releases/download/v$($A2Versions.cmakeVersion)"
    $sumPath = "$BuildRoot\downloads\cmake-$($A2Versions.cmakeVersion)-SHA-256.txt"
    Receive-A2BuildFile "$cmakeUrl/cmake-$($A2Versions.cmakeVersion)-SHA-256.txt" $sumPath
    $line = @(Get-Content $sumPath | Where-Object { $_ -match ([regex]::Escape($cmakeName) + '$') })
    if ($line.Count -ne 1) { throw 'Expected one CMake archive checksum' }
    $sum = ($line[0] -split '\s+')[0]
    $cmakeZip = "$BuildRoot\downloads\$cmakeName"
    Receive-A2BuildFile "$cmakeUrl/$cmakeName" $cmakeZip $sum
    if (-not (Test-Path "$BuildRoot\tools\cmake-$($A2Versions.cmakeVersion)-windows-x86_64\bin\cmake.exe")) {
        Expand-Archive $cmakeZip "$BuildRoot\tools" -Force
    }
    Receive-A2BuildFile 'https://dist.nuget.org/win-x86-commandline/v6.11.1/nuget.exe' "$BuildRoot\tools\nuget.exe"
    $null = Enable-A2VisualStudio
    Enable-A2Tools $BuildRoot
    Invoke-A2Native 'flutter' @('--version')
    Invoke-A2Native 'flutter' @('config','--enable-windows-desktop')
    Invoke-A2Native 'flutter' @('precache','--windows')
    Invoke-A2Native 'cmake' @('--version')
    Write-Host "Prerequisites prepared. Next: .\Build-Connect.ps1 -BuildRoot $BuildRoot"
    Write-Host 'If an installer requested a reboot, do it manually before compiling.'
} finally { Stop-Transcript | Out-Null }
