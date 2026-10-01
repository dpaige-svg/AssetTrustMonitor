param(
    [string]$Version = "1.4.3"
)

$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$releaseDirectory = Join-Path $projectRoot "release"
$packageName = "AssetTrustMonitor-$Version"
$archivePath = Join-Path $releaseDirectory "$packageName.zip"
$temporaryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path ([System.IO.Path]::GetTempPath()) ("atm-package-" + [guid]::NewGuid().ToString("N")))
)
$stagingDirectory = Join-Path $temporaryRoot $packageName

if (-not $temporaryRoot.StartsWith([System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to use an unexpected temporary path: $temporaryRoot"
}

New-Item -ItemType Directory -Path $stagingDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null

try {
    $excludedDirectories = @(
        (Join-Path $projectRoot "app\venv"),
        (Join-Path $projectRoot ".ruff_cache"),
        (Join-Path $projectRoot "release"),
        "__pycache__"
    )

    $robocopyArguments = @(
        $projectRoot,
        $stagingDirectory,
        "/E",
        "/R:1",
        "/W:1",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP",
        "/XD"
    ) + $excludedDirectories + @(
        "/XF",
        "*.pyc",
        "runtime.log",
        "rojo-server.log",
        "startup.log",
        "bootstrap.log",
        "*.prof",
        "bandit-report.txt",
        "ruff-report.txt",
        "memory-profile-report.txt",
        "profile_current_top50.txt",
        "profile_current_selftime.txt",
        "long_duration_memory_test.py",
        "memory_profile.py"
    )

    & robocopy @robocopyArguments | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "Robocopy failed with exit code $LASTEXITCODE"
    }

    if (Test-Path -LiteralPath $archivePath) {
        Remove-Item -LiteralPath $archivePath -Force
    }

    Compress-Archive -LiteralPath $stagingDirectory -DestinationPath $archivePath -CompressionLevel Optimal

    $pluginEntry = "$packageName/app/App_Build/plugins/AssetTrustMirrorPlugin.lua"
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
    try {
        $entry = $archive.Entries | Where-Object { $_.FullName.Replace("\", "/") -eq $pluginEntry }
        if (-not $entry) {
            throw "Package validation failed: plugin payload is missing"
        }
    }
    finally {
        $archive.Dispose()
    }

    Get-Item -LiteralPath $archivePath
}
finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
