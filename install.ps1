[CmdletBinding()]
param(
    [Alias("v")]
    [string]$Version,

    [string]$ModelTag = $(if ($env:OLT_ML1_MODEL_TAG) { $env:OLT_ML1_MODEL_TAG } else { "v1" }),

    [string]$InstallDir = (Join-Path $HOME ".openlinktoken\bin"),

    [switch]$Help
)

$ErrorActionPreference = "Stop"

$Repository = "TruvetaPublic/OpenLinkToken"
$ReleasesUrl = "https://github.com/$Repository/releases"
$ApiUrl = "https://api.github.com/repos/$Repository"
$ModelPackage = "ghcr.io/truvetapublic/openlinktoken-ml1-assets"
$OrasVersion = "1.3.3"

function Install-Ml1Assets {
    $ModelDirectory = Join-Path $StagedDir "_internal\openlinktoken\core\ai\tokens"
    $RequiredFiles = @("model.onnx", "model.onnx.data", "tokenizer.json", "asset-manifest.json")
    if (@($RequiredFiles | Where-Object { -not (Test-Path -LiteralPath (Join-Path $ModelDirectory $_)) }).Count -eq 0) {
        Write-Host "ML1 model assets are already included in the CLI archive."
        return
    }

    $OrasArchive = "oras_${OrasVersion}_windows_amd64.zip"
    $OrasChecksum = "30ca213a565a450de33001dae83053db53c221e6674c5233dc3406b686657969"
    $OrasArchivePath = Join-Path $TempDir $OrasArchive
    $OrasUrl = "https://github.com/oras-project/oras/releases/download/v$OrasVersion/$OrasArchive"
    Write-Host "Downloading ORAS $OrasVersion..."
    Invoke-WebRequest -Uri $OrasUrl -OutFile $OrasArchivePath
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $OrasArchivePath).Hash -ine $OrasChecksum) {
        throw "SHA-256 verification failed for ORAS $OrasVersion"
    }

    $OrasDirectory = Join-Path $TempDir "oras"
    Expand-Archive -LiteralPath $OrasArchivePath -DestinationPath $OrasDirectory
    $Oras = Join-Path $OrasDirectory "oras.exe"
    $ModelAssetsDirectory = Join-Path $TempDir "ml1-assets"
    New-Item -ItemType Directory -Path $ModelAssetsDirectory -Force | Out-Null
    Write-Host "Downloading ML1 model assets $ModelTag..."
    & $Oras pull "${ModelPackage}:$ModelTag" --output $ModelAssetsDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to pull ML1 model assets ${ModelPackage}:$ModelTag; ensure the GHCR package is public"
    }

    foreach ($FileName in $RequiredFiles) {
        $AssetPath = Join-Path $ModelAssetsDirectory $FileName
        if (-not (Test-Path -LiteralPath $AssetPath -PathType Leaf) -or (Get-Item -LiteralPath $AssetPath).Length -eq 0) {
            throw "ML1 OCI artifact is missing $FileName"
        }
    }
    try {
        $Manifest = Get-Content -Raw -LiteralPath (Join-Path $ModelAssetsDirectory "asset-manifest.json") |
            ConvertFrom-Json
    } catch {
        throw "Invalid ML1 asset manifest in OCI artifact: $($_.Exception.Message)"
    }
    foreach ($FileName in @("model.onnx", "model.onnx.data", "tokenizer.json")) {
        $AssetMetadata = $Manifest.assets.PSObject.Properties[$FileName].Value
        if (-not $AssetMetadata) {
            throw "ML1 asset manifest is missing $FileName"
        }
        $AssetPath = Join-Path $ModelAssetsDirectory $FileName
        if ((Get-Item -LiteralPath $AssetPath).Length -ne $AssetMetadata.size) {
            throw "Unexpected size for ML1 asset $FileName"
        }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $AssetPath).Hash -ine $AssetMetadata.sha256) {
            throw "SHA-256 verification failed for $FileName"
        }
    }
    New-Item -ItemType Directory -Path $ModelDirectory -Force | Out-Null
    Copy-Item -Path (Join-Path $ModelAssetsDirectory "*") -Destination $ModelDirectory -Force
}

function Show-Usage {
    @"
Install the Open Link Token CLI for Windows.

Usage:
  .\install.ps1 [-Version VERSION] [-ModelTag TAG] [-InstallDir DIRECTORY]

Options:
  -Version VERSION        Install a specific release (default: latest)
  -ModelTag TAG           Install this ML1 model tag (default: v1 or OLT_ML1_MODEL_TAG)
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
if ($ModelTag -notmatch '^v[0-9]+$') {
    throw "Invalid ML1 model tag: $ModelTag (expected vN)"
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

    Install-Ml1Assets

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
