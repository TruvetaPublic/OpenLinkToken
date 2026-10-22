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

function Install-ModelAsset {
    param(
        [string]$AssetId,
        [string]$FileName
    )

    $ModelDirectory = Join-Path $StagedDir "_internal\openlinktoken\core\ai\tokens"
    $Destination = Join-Path $ModelDirectory $FileName
    if (Test-Path -LiteralPath $Destination) {
        return
    }

    $ManifestName = "olt-model-$Version-windows-x64-$AssetId.manifest"
    $ManifestPath = Join-Path $TempDir $ManifestName
    Invoke-WebRequest -Uri "$ReleasesUrl/download/$Tag/$ManifestName" -OutFile $ManifestPath
    $ManifestLines = @(Get-Content -LiteralPath $ManifestPath)
    if ($ManifestLines.Count -lt 2) {
        throw "Invalid ML1 model asset manifest: $ManifestName"
    }

    $Header = $ManifestLines[0] -split "`t"
    if ($Header.Count -ne 2 -or $Header[0] -ne "sha256" -or $Header[1] -notmatch '^[0-9a-fA-F]{64}$') {
        throw "Invalid ML1 model asset manifest: $ManifestName"
    }

    $PartPrefix = "olt-model-$Version-windows-x64-$AssetId-part-"
    $AssembledPath = Join-Path $TempDir $FileName
    $OutputStream = [System.IO.File]::Open(
        $AssembledPath,
        [System.IO.FileMode]::Create,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    $PartCount = 0
    try {
        foreach ($Line in $ManifestLines | Select-Object -Skip 1) {
            $Entry = $Line -split "`t"
            if ($Entry.Count -ne 3 -or $Entry[0] -ne "part" -or $Entry[1] -notmatch '^[0-9a-fA-F]{64}$') {
                throw "Invalid ML1 model asset manifest entry"
            }

            $ExpectedPartNumber = "{0:D3}" -f ($PartCount + 1)
            if ($Entry[2] -notmatch "^$([regex]::Escape($PartPrefix))$ExpectedPartNumber\.bin$") {
                throw "Invalid ML1 model asset part name: $($Entry[2])"
            }

            $PartPath = Join-Path $TempDir $Entry[2]
            Invoke-WebRequest -Uri "$ReleasesUrl/download/$Tag/$($Entry[2])" -OutFile $PartPath
            $PartChecksum = (Get-FileHash -Algorithm SHA256 -LiteralPath $PartPath).Hash
            if ($PartChecksum -ine $Entry[1]) {
                throw "SHA-256 verification failed for $($Entry[2])"
            }

            $PartStream = [System.IO.File]::OpenRead($PartPath)
            try {
                $PartStream.CopyTo($OutputStream)
            } finally {
                $PartStream.Dispose()
            }
            $PartCount++
        }
    } finally {
        $OutputStream.Dispose()
    }

    if ($PartCount -eq 0) {
        throw "ML1 model asset manifest contains no parts: $ManifestName"
    }
    $ModelChecksum = (Get-FileHash -Algorithm SHA256 -LiteralPath $AssembledPath).Hash
    if ($ModelChecksum -ine $Header[1]) {
        throw "SHA-256 verification failed for assembled $FileName"
    }

    New-Item -ItemType Directory -Path $ModelDirectory -Force | Out-Null
    Move-Item -LiteralPath $AssembledPath -Destination $Destination -Force
}

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

$StagedDir = $null
$PreviousDir = $null
$MovedPrevious = $false
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
    $InstallParent = Split-Path -Parent $InstallDir
    New-Item -ItemType Directory -Path $InstallParent -Force | Out-Null
    $StagedDir = Join-Path $InstallParent (".olt-staged-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $StagedDir -Force | Out-Null
    Copy-Item -Path (Join-Path $Binary.Directory.FullName "*") -Destination $StagedDir -Recurse -Force

    Write-Host "Downloading required ML1 model assets when missing..."
    Install-ModelAsset -AssetId "model" -FileName "model.onnx"
    Install-ModelAsset -AssetId "model-data" -FileName "model.onnx.data"

    $PreviousDir = "$InstallDir.previous"
    if (Test-Path -LiteralPath $PreviousDir) {
        Remove-Item -LiteralPath $PreviousDir -Recurse -Force
    }
    if (Test-Path -LiteralPath $InstallDir) {
        Move-Item -LiteralPath $InstallDir -Destination $PreviousDir
        $MovedPrevious = $true
    }
    try {
        Move-Item -LiteralPath $StagedDir -Destination $InstallDir
    } catch {
        if ($MovedPrevious -and -not (Test-Path -LiteralPath $InstallDir)) {
            Move-Item -LiteralPath $PreviousDir -Destination $InstallDir
        }
        throw
    }
    if (Test-Path -LiteralPath $PreviousDir) {
        Remove-Item -LiteralPath $PreviousDir -Recurse -Force
    }

    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $PathEntries = if ($UserPath) { @($UserPath -split ";") } else { @() }
    if (-not ($PathEntries | Where-Object { $_ -ieq $InstallDir })) {
        [Environment]::SetEnvironmentVariable("Path", (($PathEntries + $InstallDir) -join ";"), "User")
    }
    $env:Path = "$InstallDir;$env:Path"

    Write-Host "Installed olt $Tag to $(Join-Path $InstallDir 'olt.exe')"
} finally {
    if ($StagedDir -and (Test-Path -LiteralPath $StagedDir)) {
        Remove-Item -LiteralPath $StagedDir -Recurse -Force
    }
    if (Test-Path -LiteralPath $TempDir) {
        Remove-Item -LiteralPath $TempDir -Recurse -Force
    }
}
