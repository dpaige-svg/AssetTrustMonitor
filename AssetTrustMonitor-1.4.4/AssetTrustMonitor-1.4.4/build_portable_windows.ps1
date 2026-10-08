param(
    [string]$Version = "1.4.4"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot "build\packaging-venv-312\Scripts\python.exe"
$EntryPoint = Join-Path $ProjectRoot "main.py"
$BuildRoot = Join-Path $ProjectRoot "build\portable-windows-$Version"
$WorkPath = Join-Path $BuildRoot "work"
$SpecPath = Join-Path $BuildRoot "spec"
$DistPath = Join-Path $BuildRoot "dist"
$ReleaseRoot = Join-Path $ProjectRoot "release\ATM-$Version"
$ArchivePath = Join-Path $ProjectRoot "release\AssetTrustMonitor-$Version-Windows-Portable.zip"
$IconPath = Join-Path $ProjectRoot "app\App_Build\assets\ApplicationIcon.png"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python 3.12 packaging environment is missing: $Python"
}

function Remove-GeneratedPath([string]$Path) {
    $fullProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\') + '\'
    $fullTarget = [System.IO.Path]::GetFullPath($Path)
    if (-not $fullTarget.StartsWith($fullProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a path outside the project: $fullTarget"
    }
    if (Test-Path -LiteralPath $fullTarget) {
        Remove-Item -LiteralPath $fullTarget -Recurse -Force
    }
}

Remove-GeneratedPath $BuildRoot
Remove-GeneratedPath $ReleaseRoot
if (Test-Path -LiteralPath $ArchivePath) {
    Remove-Item -LiteralPath $ArchivePath -Force
}

New-Item -ItemType Directory -Force -Path $WorkPath, $SpecPath, $DistPath, $ReleaseRoot | Out-Null

# The managed build environment restricts Tcl from reading the per-user Python
# installation directory. A workspace-local copy also gives PyInstaller a
# stable source for the Tcl/Tk runtime bundled with the executable.
$BasePrefix = (& $Python -c "import sys; print(sys.base_prefix)").Trim()
$TclBuildRoot = Join-Path $BuildRoot "tcl-runtime"
New-Item -ItemType Directory -Force -Path $TclBuildRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $BasePrefix "tcl\tcl8.6") -Destination $TclBuildRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $BasePrefix "tcl\tk8.6") -Destination $TclBuildRoot -Recurse -Force
$env:TCL_LIBRARY = Join-Path $TclBuildRoot "tcl8.6"
$env:TK_LIBRARY = Join-Path $TclBuildRoot "tk8.6"

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name "AssetTrustMonitor" `
    --contents-directory "i" `
    --icon $IconPath `
    --paths (Join-Path $ProjectRoot "app") `
    --collect-submodules "src" `
    --hidden-import "pystray._win32" `
    --distpath $DistPath `
    --workpath $WorkPath `
    --specpath $SpecPath `
    $EntryPoint

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$BuiltApp = Join-Path $DistPath "AssetTrustMonitor"
Copy-Item -LiteralPath (Join-Path $BuiltApp "AssetTrustMonitor.exe") -Destination $ReleaseRoot -Force
Copy-Item -LiteralPath (Join-Path $BuiltApp "i") -Destination $ReleaseRoot -Recurse -Force

# Qt ships a newer compatible Visual C++ runtime than the Python runtime used
# for the build. Windows loads one DLL per basename, so keep the shared copies
# in the bundle root at the Qt version to prevent QtCore procedure mismatches.
$ReleaseInternal = Join-Path $ReleaseRoot "i"
$QtRuntime = Join-Path $ReleaseInternal "PySide6"
@(
    "MSVCP140.dll",
    "MSVCP140_1.dll",
    "MSVCP140_2.dll",
    "VCRUNTIME140.dll",
    "VCRUNTIME140_1.dll"
) | ForEach-Object {
    $source = Join-Path $QtRuntime $_
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $ReleaseInternal $_) -Force
    }
}

$ReleaseApp = Join-Path $ReleaseRoot "app"
New-Item -ItemType Directory -Force -Path $ReleaseApp | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot "app\App_Build") -Destination $ReleaseApp -Recurse -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "app\Rojo_Build") -Destination $ReleaseApp -Recurse -Force
$ReleaseWorkspace = Join-Path $ReleaseApp "Rojo_Build\src\Workspace"
Get-ChildItem -LiteralPath $ReleaseWorkspace -Force -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-GeneratedPath $_.FullName
}
$ReleaseLock = Join-Path $ReleaseApp "Rojo_Build\Asset_Trust_Place.rbxl.lock"
if (Test-Path -LiteralPath $ReleaseLock) {
    Remove-Item -LiteralPath $ReleaseLock -Force
}
New-Item -ItemType Directory -Force -Path `
    (Join-Path $ReleaseApp "processing\Processing_rbxm"), `
    (Join-Path $ReleaseApp "processing\FLAGGED-ASSETS"), `
    (Join-Path $ReleaseApp "processing\DataStore") | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot "app\processing\DataStore\debug_options.json") `
    -Destination (Join-Path $ReleaseApp "processing\DataStore\debug_options.json") -Force
New-Item -ItemType Directory -Force -Path (Join-Path $ReleaseRoot "Assets") | Out-Null

$Readme = @"
AssetTrustMonitor $Version - Windows Portable

1. Extract the entire ZIP to a short local path such as C:\AssetTrustMonitor.
2. Keep the _internal and app folders beside AssetTrustMonitor.exe.
3. Double-click AssetTrustMonitor.exe.

Python does not need to be installed. Internet access is still required on the
first run when AssetTrustMonitor installs or updates Rokit and Rojo.

If Windows blocks the downloaded ZIP, right-click the ZIP, choose Properties,
select Unblock, click Apply, and then extract it again.
"@
Set-Content -LiteralPath (Join-Path $ReleaseRoot "README.txt") -Value $Readme -Encoding UTF8

Compress-Archive -LiteralPath $ReleaseRoot -DestinationPath $ArchivePath -Force

Write-Output "Portable folder: $ReleaseRoot"
Write-Output "Portable ZIP:    $ArchivePath"
