[CmdletBinding()]
param(
    [string]$BuildRoot = 'C:\A2ConnectBuild',
    [switch]$SkipMsi,
    [switch]$UnattendedControls
)
. "$PSScriptRoot\Common.ps1"
Assert-A2Windows
if ($BuildRoot -match '\s' -or -not [IO.Path]::IsPathRooted($BuildRoot)) { throw 'Use an absolute build path without spaces' }
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
New-Item -ItemType Directory -Force "$BuildRoot\logs", "$BuildRoot\downloads", "$BuildRoot\work", "$BuildRoot\output" | Out-Null
$lock = [IO.File]::Open("$BuildRoot\build.lock", 'OpenOrCreate', 'ReadWrite', 'None')
$stamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,6)
$log = "$BuildRoot\logs\build-$stamp.log"
$originalLocation = Get-Location
Start-Transcript -Path $log | Out-Null
try {
    Enable-A2Tools $BuildRoot
    $null = Enable-A2VisualStudio
    Enable-A2Tools $BuildRoot
    foreach ($command in @('git','py','cargo','rustup','flutter','cmake','clang','nasm','msbuild')) {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Missing $command. Run Setup-LocalBuild.ps1 -Install first." }
    }
    if (-not (Test-Path "$env:LIBCLANG_PATH\libclang.dll")) { throw 'libclang.dll not found; check the LLVM installation' }
    $venv = "$BuildRoot\python311"
    if (-not (Test-Path "$venv\Scripts\python.exe")) { Invoke-A2Native 'py' @('-3.11','-m','venv',$venv) }
    $python = "$venv\Scripts\python.exe"
    $env:PATH = "$venv\Scripts;" + $env:PATH
    # Some pinned upstream helpers use the Unix executable spelling on Windows.
    if (-not (Test-Path "$venv\Scripts\python3.exe")) { Copy-Item $python "$venv\Scripts\python3.exe" }
    $options = @()
    if ($UnattendedControls) { $options += '--unattended' }
    $fingerprint = & $python "$PSScriptRoot\prepare_source.py" --fingerprint @options
    if ($LASTEXITCODE -ne 0 -or $fingerprint -notmatch '^[a-f0-9]{16}$') { throw 'Could not identify local recipe' }
    $source = "$BuildRoot\work\rustdesk-$($A2Versions.rustdeskVersion)-$fingerprint"
    if (-not (Test-Path $source)) {
        Invoke-A2Native 'git' @('clone','--recursive','--branch',$A2Versions.rustdeskVersion,'https://github.com/rustdesk/rustdesk.git',$source)
    }
    Invoke-A2Native $python (@("$PSScriptRoot\prepare_source.py",'--source',$source) + $options)
    Set-Location $source
    # Build dependencies belong to this dedicated build root, never to an installed app.
    if (-not (Test-Path "$env:VCPKG_ROOT\.git")) {
        Invoke-A2Native 'git' @('clone','https://github.com/microsoft/vcpkg.git',$env:VCPKG_ROOT)
        Invoke-A2Native 'git' @('-C',$env:VCPKG_ROOT,'checkout','--detach',$A2Versions.vcpkgCommit)
    }
    $vcpkgCommit = & git -C $env:VCPKG_ROOT rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $vcpkgCommit -ne $A2Versions.vcpkgCommit) { throw 'Existing vcpkg has an unexpected revision; use a new BuildRoot' }
    if (-not (Test-Path "$env:VCPKG_ROOT\vcpkg.exe")) { Invoke-A2Native "$env:VCPKG_ROOT\bootstrap-vcpkg.bat" @('-disableMetrics') }
    Invoke-A2Native "$env:VCPKG_ROOT\vcpkg.exe" @('install','--triplet','x64-windows-static',"--x-install-root=$env:VCPKG_ROOT/installed",'--disable-metrics')
    # Use the same patched Flutter engine as the existing x64 pipeline.
    $flutterRoot = "$BuildRoot\tools\flutter"
    $engineZip = "$BuildRoot\downloads\windows-x64-release.zip"
    Receive-A2BuildFile 'https://github.com/rustdesk/engine/releases/download/main/windows-x64-release.zip' $engineZip
    $engine = "$BuildRoot\downloads\windows-x64-release"
    if (-not (Test-Path $engine)) { Expand-Archive $engineZip $engine }
    Copy-Item "$engine\*" "$flutterRoot\bin\cache\artifacts\engine\windows-x64-release" -Recurse -Force
    $dropdown = Join-Path $repo '.github\patches\flutter_3.24.4_dropdown_menu_enableFilter.diff'
    if (-not (Test-A2ReversePatch $flutterRoot $dropdown)) {
        Invoke-A2Native 'git' @('-C',$flutterRoot,'apply','--check',$dropdown)
        Invoke-A2Native 'git' @('-C',$flutterRoot,'apply',$dropdown)
    }
    Set-Location "$source\flutter"
    Invoke-A2Native 'flutter' @('pub','get')
    Set-Location $source
    Invoke-A2Native 'cargo' @('install','cargo-expand','--version',$A2Versions.cargoExpandVersion,'--locked')
    Invoke-A2Native 'cargo' @('install','flutter_rust_bridge_codegen','--version',$A2Versions.bridgeVersion,'--features','uuid','--locked')
    Invoke-A2Native 'flutter_rust_bridge_codegen' @('--rust-input','./src/flutter_ffi.rs','--dart-output','./flutter/lib/generated_bridge.dart','--c-output','./flutter/macos/Runner/bridge_generated.h')
    Copy-Item './flutter/macos/Runner/bridge_generated.h' './flutter/ios/Runner/bridge_generated.h' -Force
    Set-Location "$source\flutter"
    Invoke-A2Native 'flutter' @('analyze','--no-pub','--no-fatal-infos','--no-fatal-warnings','lib/desktop/pages/desktop_home_page.dart','lib/desktop/pages/connection_page.dart')
    Set-Location $source
    Invoke-A2Native $python @('build.py','--portable','--hwcodec','--flutter','--skip-portable-pack','--vram')
    $release = "$source\flutter\build\windows\x64\runner\Release"
    if (-not (Test-Path "$release\rustdesk.exe")) { throw 'Flutter release executable was not generated' }
    # Pinned helper used by the existing Windows workflow. Build from source.
    $injection = "$BuildRoot\work\window-injection-$($A2Versions.windowInjectionCommit)"
    if (-not (Test-Path $injection)) {
        Invoke-A2Native 'git' @('clone','https://github.com/rustdesk-org/RustDeskTempTopMostWindow.git',$injection)
        Invoke-A2Native 'git' @('-C',$injection,'checkout','--detach',$A2Versions.windowInjectionCommit)
    }
    $injectionCommit = & git -C $injection rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $injectionCommit -ne $A2Versions.windowInjectionCommit) { throw 'Unexpected WindowInjection revision' }
    Invoke-A2Native 'msbuild' @("$injection\WindowInjection\WindowInjection.vcxproj",'/p:Configuration=Release','/p:Platform=x64','/p:TargetVersion=Windows10')
    Copy-Item "$injection\WindowInjection\x64\Release\WindowInjection.dll" $release -Force
    Copy-Item "$source\a2-custom.txt" "$release\custom_.txt" -Force
    Copy-Item "$release\rustdesk.exe" "$release\Connect.exe" -Force
    Remove-Item "$release\rustdesk.exe"
    # The outer portable EXE must carry the same icon/version resources.
    $resources = @(Get-ChildItem "$source\flutter\build\windows\x64" -Filter Runner.res -Recurse)
    if ($resources.Count -ne 1) { throw 'Expected exactly one compiled Runner.res' }
    Copy-Item $resources[0].FullName "$source\libs\portable\Runner.res" -Force
    $out = "$BuildRoot\output\Connect-x64-$stamp"
    New-Item -ItemType Directory $out | Out-Null
    Set-Location "$source\libs\portable"
    Invoke-A2Native $python @('-m','pip','install','-r','requirements.txt')
    Invoke-A2Native $python @('generate.py','-f',$release,'-o','.','-e',"$release\Connect.exe")
    if (-not (Test-Path "$source\target\release\rustdesk-portable-packer.exe")) { throw 'Self-contained portable packer was not generated' }
    Copy-Item "$source\target\release\rustdesk-portable-packer.exe" "$out\Connect-x86_64.exe"
    Set-Location $source
    if (-not $SkipMsi) {
        Set-Location "$source\res\msi"
        Invoke-A2Native $python @('preprocess.py','--app-name','Connect','--version',$A2Versions.rustdeskVersion,'--manufacturer','a2','--arp','-d',$release)
        Invoke-A2Native 'nuget.exe' @('restore','msi.sln','-NonInteractive','-Source','https://api.nuget.org/v3/index.json')
        Invoke-A2Native 'msbuild' @('msi.sln','/p:Configuration=Release','/p:Platform=x64','/p:TargetVersion=Windows10')
        $msi = @(Get-ChildItem '.\Package\bin\*\Release\en-us\Package.msi')
        if ($msi.Count -ne 1) { throw 'Expected exactly one MSI output' }
        Copy-Item $msi[0].FullName "$out\Connect-x86_64.msi"
    }
    $files = @(Get-ChildItem $out -File | Where-Object { $_.Extension -in '.exe','.msi' })
    foreach ($file in $files) { if ($file.Length -eq 0) { throw "Empty output: $($file.Name)" } }
    $hashes = @($files | ForEach-Object { (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower() + '  ' + $_.Name })
    [IO.File]::WriteAllLines("$out\SHA256SUMS.txt", $hashes)
    $generatorCommit = 'source-archive'
    if (Test-Path (Join-Path $repo 'SOURCE-REVISION.txt')) {
        $generatorCommit = (Get-Content (Join-Path $repo 'SOURCE-REVISION.txt') -Raw).Trim()
    }
    if (Test-Path (Join-Path $repo '.git')) {
        $generatorCommit = & git -C $repo rev-parse HEAD
        if ($LASTEXITCODE -ne 0) { throw 'Could not record generator commit' }
    }
    $manifest = [ordered]@{
        status='preview-not-homologated'; recipeFingerprint=$fingerprint; generatorCommit=$generatorCommit
        upstreamCommit=$A2Versions.rustdeskCommit; arch='x86_64'; sourceDirectory=$source
        unattendedControls=[bool]$UnattendedControls; msiRequested=(-not $SkipMsi)
        flutterEngineSha256=(Get-FileHash $engineZip -Algorithm SHA256).Hash
        signatures=@($files | ForEach-Object { @{file=$_.Name; status=(Get-AuthenticodeSignature $_.FullName).Status.ToString()} })
        builtAt=(Get-Date).ToString('o'); log=$log
    }
    $manifest | ConvertTo-Json -Depth 6 | Set-Content "$out\BUILD-INFO.json" -Encoding UTF8
    Copy-Item "$repo\a2\docs\ROTEIRO-EQUIPE.md" "$out\LEIA-PRIMEIRO.md"
    Copy-Item "$repo\a2\docs\TESTES-E-OPERACAO.md" $out
    $zip = "$out.zip"
    Compress-Archive -Path "$out\*" -DestinationPath $zip
    Write-Host "Build completed. Preview ZIP: $zip"
    Write-Host 'No Connect installation/service was executed. These files are not production-signed.'
} finally {
    Set-Location $originalLocation
    Stop-Transcript | Out-Null
    $lock.Dispose()
}
