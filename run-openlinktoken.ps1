# run-openlinktoken.ps1
# Convenience script to build and run OpenLinkToken via Docker
# Automatically handles Docker image building and container execution

[CmdletBinding()]
param(
    [Parameter(Position=0, Mandatory=$false, HelpMessage="Subcommand: package, tokenize, encrypt, or decrypt (default: package)")]
    [ValidateSet("package", "tokenize", "encrypt", "decrypt")]
    [string]$Subcommand = "package",

    [Parameter(Mandatory=$false, HelpMessage="Input file path (absolute or relative)")]
    [Alias("i")]
    [string]$InputFile,

    [Parameter(Mandatory=$false, HelpMessage="Output file path (absolute or relative)")]
    [Alias("o")]
    [string]$OutputFile,

    [Parameter(Mandatory=$false, HelpMessage="File type: csv or parquet (default: csv)")]
    [Alias("t")]
    [ValidateSet("csv", "parquet")]
    [string]$FileType = "csv",

    [Parameter(Mandatory=$false, HelpMessage="Hashing secret key")]
    [Alias("h")]
    [string]$HashingSecret,

    [Parameter(Mandatory=$false, HelpMessage="Encryption key")]
    [Alias("e")]
    [string]$EncryptionKey,

    [Parameter(Mandatory=$false, HelpMessage="Docker image name (default: openlinktoken:latest)")]
    [string]$DockerImage = "openlinktoken:latest",

    [Parameter(Mandatory=$false, HelpMessage="Skip Docker image build (use existing image)")]
    [Alias("s")]
    [switch]$SkipBuild,

    [Parameter(Mandatory=$false, HelpMessage="Show help message")]
    [switch]$Help
)

# Function to write script output in a consistent format
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message"
}

# Function to show usage
function Show-Usage {
    $usage = @"

USAGE:
    run-openlinktoken.ps1 [SUBCOMMAND] [OPTIONS]

DESCRIPTION:
    Convenience wrapper for building and running OpenLinkToken via Docker.
    Automatically builds the Docker image if needed and runs OpenLinkToken with specified parameters.

SUBCOMMANDS:
    package     Tokenize and encrypt in one step (default). Requires -h and -e.
    tokenize    Hash-only mode, no encryption. Requires -h only.
    encrypt     Encrypt previously tokenized output. Requires -e only.
    decrypt     Decrypt encrypted tokens. Requires -e only.

REQUIRED PARAMETERS:
    -InputFile, -i <file>       Input file path (absolute or relative)
    -OutputFile, -o <file>      Output file path (absolute or relative)

SUBCOMMAND-SPECIFIC PARAMETERS:
    -HashingSecret, -h <key>    Hashing secret key          (package, tokenize)
    -EncryptionKey, -e <key>    32-character encryption key (package, encrypt, decrypt)

OPTIONAL PARAMETERS:
    -FileType, -t <type>        File type: csv or parquet (default: csv)
    -SkipBuild, -s              Skip Docker image build (use existing image)
    -DockerImage <name>         Docker image name (default: openlinktoken:latest)
    -Verbose, -v                Enable verbose output
    -Help                       Show this help message

EXAMPLES:
    # Tokenize and encrypt (default package subcommand)
    .\run-openlinktoken.ps1 -i .\input.csv -o .\output.csv -h "MyHashKey" -e "MyEncryptionKey"

    # Explicit package subcommand
    .\run-openlinktoken.ps1 -Subcommand package -i .\input.csv -o .\output.csv -h "HashKey" -e "EncryptionKey"

    # Hash-only mode (no encryption)
    .\run-openlinktoken.ps1 -Subcommand tokenize -i .\input.csv -t csv -o .\hashed.csv -h "HashKey"

    # Decrypt previously encrypted tokens
    .\run-openlinktoken.ps1 -Subcommand decrypt -i .\tokens.csv -t csv -o .\decrypted.csv -e "EncryptionKey"

    # Encrypt previously tokenized (hashed) output
    .\run-openlinktoken.ps1 -Subcommand encrypt -i .\hashed.csv -t csv -o .\encrypted.csv -e "EncryptionKey"

    # Skip Docker build if image already exists
    .\run-openlinktoken.ps1 -i .\input.csv -o .\output.csv -h "secret" -e "key" -SkipBuild

    # Verbose mode for troubleshooting
    .\run-openlinktoken.ps1 -Subcommand tokenize -i .\input.csv -o .\output.csv -h "secret" -Verbose

NOTES:
    - This script must be run from the OpenLinkToken repository root directory
    - Input and output files are automatically mounted into the Docker container
    - The script will build the Docker image on first run (may take a few minutes)
    - Use -SkipBuild to skip rebuilding the image on subsequent runs

"@
    Write-Host $usage
}

# Show help if requested
if ($Help) {
    Show-Usage
    exit 0
}

# Validate required parameters
if (-not $InputFile) {
    Write-Info "Input file is required (use -InputFile or -i)"
    Write-Host ""
    Show-Usage
    exit 1
}

if (-not $OutputFile) {
    Write-Info "Output file is required (use -OutputFile or -o)"
    Write-Host ""
    Show-Usage
    exit 1
}

# Validate subcommand-specific required options
switch ($Subcommand) {
    "package" {
        if (-not $HashingSecret) {
            Write-Info "Hashing secret is required for 'package' (use -HashingSecret or -h)"
            Write-Host ""
            Show-Usage
            exit 1
        }
        if (-not $EncryptionKey) {
            Write-Info "Encryption key is required for 'package' (use -EncryptionKey or -e)"
            Write-Host ""
            Show-Usage
            exit 1
        }
    }
    "tokenize" {
        if (-not $HashingSecret) {
            Write-Info "Hashing secret is required for 'tokenize' (use -HashingSecret or -h)"
            Write-Host ""
            Show-Usage
            exit 1
        }
    }
    { $_ -in @("encrypt", "decrypt") } {
        if (-not $EncryptionKey) {
            Write-Info "Encryption key is required for '$Subcommand' (use -EncryptionKey or -e)"
            Write-Host ""
            Show-Usage
            exit 1
        }
    }
}

# Check if Docker is installed
try {
    $dockerVersion = docker --version 2>$null
    if (-not $dockerVersion) {
        throw "Docker not found"
    }
}
catch {
    Write-Info "Docker is not installed or not in PATH"
    Write-Info "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
}

# Convert to absolute paths
$InputFileRaw = $InputFile
$InputFile = Resolve-Path -Path $InputFile -ErrorAction SilentlyContinue
if (-not $InputFile) {
    Write-Info "Input file does not exist: $InputFileRaw"
    exit 1
}

# For output file, create parent directory if it doesn't exist
$OutputFileParent = Split-Path -Parent $OutputFile
if ($OutputFileParent -and -not (Test-Path $OutputFileParent)) {
    New-Item -ItemType Directory -Path $OutputFileParent -Force | Out-Null
}

# Convert output path to absolute (may not exist yet)
if ([System.IO.Path]::IsPathRooted($OutputFile)) {
    $OutputFile = $OutputFile
} else {
    $OutputFile = Join-Path (Get-Location) $OutputFile
}
$OutputFile = [System.IO.Path]::GetFullPath($OutputFile)

# Verify input file exists
if (-not (Test-Path $InputFile)) {
    Write-Info "Input file does not exist: $InputFile"
    exit 1
}

# Get directory paths for volume mounting
$InputDir = Split-Path -Parent $InputFile
$InputFilename = Split-Path -Leaf $InputFile
$OutputDir = Split-Path -Parent $OutputFile
$OutputFilename = Split-Path -Leaf $OutputFile

# Create output directory if it doesn't exist
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

if ($VerboseOutput) {
    Write-Info "Subcommand: $Subcommand"
    Write-Info "Input file: $InputFile"
    Write-Info "Output file: $OutputFile"
    Write-Info "File type: $FileType"
    Write-Info "Docker image: $DockerImage"
}

# Build Docker image if needed
if (-not $SkipBuild) {
    # Check if image already exists
    docker image inspect $DockerImage > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Info "Docker image '$DockerImage' already exists locally"
        if ($VerboseOutput) {
            Write-Info "Use -SkipBuild to suppress this check"
        }
    } else {
        Write-Info "Building Docker image: $DockerImage"
        Write-Info "This may take a few minutes on first run..."

        if ($VerboseOutput) {
            docker build -t $DockerImage .
        } else {
            docker build -t $DockerImage . 2>&1 | Out-Null
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Info "Docker image built successfully"
        } else {
            Write-Info "Failed to build Docker image"
            exit 1
        }
    }
} else {
    Write-Info "Skipping Docker build (using existing image)"

    # Check if image exists
    docker image inspect $DockerImage > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Docker image '$DockerImage' not found"
        Write-Info "Run without -SkipBuild to build the image first"
        exit 1
    }
}

# Run OpenLinkToken via Docker
Write-Info "Running OpenLinkToken ($Subcommand)..."

# Build subcommand-specific CLI argument list
$CliArgs = @()
switch ($Subcommand) {
    "package"  { $CliArgs += "-h", $HashingSecret, "-e", $EncryptionKey }
    "tokenize" { $CliArgs += "-h", $HashingSecret }
    { $_ -in @("encrypt", "decrypt") } { $CliArgs += "-e", $EncryptionKey }
}

# Convert Windows paths to Docker-compatible format (with forward slashes)
$InputDirDocker = $InputDir -replace '\\', '/'
$OutputDirDocker = $OutputDir -replace '\\', '/'

# Handle drive letter for Windows (C:\ becomes /c/)
$InputDirDocker = $InputDirDocker -replace '^([A-Z]):', '/$1'
$OutputDirDocker = $OutputDirDocker -replace '^([A-Z]):', '/$1'

# If input and output are in the same directory, mount once
if ($InputDir -eq $OutputDir) {
    if ($VerboseOutput) {
        Write-Info "Mounting directory: $InputDir"
    }

    docker run --rm `
        -v "${InputDir}:/data" `
        $DockerImage `
        $Subcommand `
        -i "/data/$InputFilename" `
        -t $FileType `
        -o "/data/$OutputFilename" `
        @CliArgs
} else {
    # Mount input and output directories separately
    if ($VerboseOutput) {
        Write-Info "Mounting input directory: $InputDir"
        Write-Info "Mounting output directory: $OutputDir"
    }

    docker run --rm `
        -v "${InputDir}:/data/input" `
        -v "${OutputDir}:/data/output" `
        $DockerImage `
        $Subcommand `
        -i "/data/input/$InputFilename" `
        -t $FileType `
        -o "/data/output/$OutputFilename" `
        @CliArgs
}

if ($LASTEXITCODE -eq 0) {
    Write-Info "OpenLinkToken completed successfully!"
    Write-Info "Output file: $OutputFile"
} else {
    Write-Info "OpenLinkToken execution failed"
    exit 1
}
