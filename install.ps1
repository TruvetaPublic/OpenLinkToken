[CmdletBinding()]
param(
    [Alias("v")]
    [string]$Version,

    [string]$InstallDir = (Join-Path $HOME ".openlinktoken\bin"),

    [switch]$Help
)

$ErrorActionPreference = "Stop"

$Repository = "TruvetaPublic/OpenLinkToken"
$ReleasesUrl = "https://github.com/$Repository/releases"
$ApiUrl = "https://api.github.com/repos/$Repository"

function Show-Usage {
    @"
Install the Open Link Token CLI for Windows.

Usage:
  .\install.ps1 [-Version VERSION] [-InstallDir DIRECTORY]

Options:
  -Version VERSION        Install a specific release (default: latest)
  -InstallDir DIRECTORY   Install into DIRECTORY (default: ~/.openlinktoken/bin)
  -Help                   Show this help
"@
}

if ($Help) {
    Show-Usage
    exit 0
}

if (-not $Version) {
    try {
        $release = Invoke-RestMethod -Uri "$ApiUrl/releases/latest" -Headers @{
            Accept = "application/vnd.github+json"
        }
        $Version = $release.tag_name
    } catch {
        throw "Unable to resolve the latest release: $($_.Exception.Message)"
    }
}

if ($Version -notmatch '^[vV]?\d+(\.\d+){2}([.-][0-9A-Za-z.-]+)?$') {
    throw "Invalid version: $Version"
}

$Version = $Version -replace '^[vV]', ''
$Tag = "v$Version"

$Architecture = if ($env:PROCESSOR_ARCHITEW6432) {
    $env:PROCESSOR_ARCHITEW6432
} else {
    $env:PROCESSOR_ARCHITECTURE
}
if ($Architecture -notmatch '^(AMD64|x86_64)$') {
    throw "No Windows CLI asset is available for architecture $Architecture"
}

$Asset = "olt-cli-$Version-windows-x64.zip"
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("olt-install-" + [Guid]::NewGuid().ToString("N"))
$Archive = Join-Path $TempDir $Asset
$ChecksumFile = "$Archive.sha256"
$DownloadUrl = "$ReleasesUrl/download/$Tag/$Asset"

try {
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
    Write-Host "Downloading Open Link Token $Tag..."
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $Archive
    Invoke-WebRequest -Uri "$DownloadUrl.sha256" -OutFile $ChecksumFile

    $ExpectedChecksum = ((Get-Content -Raw $ChecksumFile).Trim() -split '\s+')[0]
    if ($ExpectedChecksum -notmatch '^[0-9a-fA-F]{64}$') {
        throw "Invalid SHA-256 checksum file"
    }

    $ActualChecksum = (Get-FileHash -Algorithm SHA256 -LiteralPath $Archive).Hash
    if ($ActualChecksum -ine $ExpectedChecksum) {
        throw "SHA-256 verification failed"
    }

    $ExtractDir = Join-Path $TempDir "extracted"
    Expand-Archive -LiteralPath $Archive -DestinationPath $ExtractDir
    $Binary = Get-ChildItem -Path $ExtractDir -Filter "olt.exe" -File -Recurse | Select-Object -First 1
    if (-not $Binary) {
        throw "Release archive does not contain olt.exe"
    }

    $InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Copy-Item -LiteralPath $Binary.FullName -Destination (Join-Path $InstallDir "olt.exe") -Force

    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $PathEntries = if ($UserPath) { @($UserPath -split ";") } else { @() }
    if (-not ($PathEntries | Where-Object { $_ -ieq $InstallDir })) {
        [Environment]::SetEnvironmentVariable("Path", (($PathEntries + $InstallDir) -join ";"), "User")
    }
    $env:Path = "$InstallDir;$env:Path"

    Write-Host "Installed olt $Tag to $(Join-Path $InstallDir 'olt.exe')"
} finally {
    if (Test-Path -LiteralPath $TempDir) {
        Remove-Item -LiteralPath $TempDir -Recurse -Force
    }
}
