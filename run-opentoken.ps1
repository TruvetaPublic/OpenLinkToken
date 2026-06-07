# run-opentoken.ps1
# Convenience script to build and run OpenToken via Docker
# Automatically handles Docker image building and container execution

[CmdletBinding()]
param(
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

    [Parameter(Mandatory=$false, HelpMessage="Docker image name (default: opentoken:latest)")]
    [string]$DockerImage = "opentoken:latest",

    [Parameter(Mandatory=$false, HelpMessage="Skip Docker image build (use existing image)")]
    [Alias("s")]
    [switch]$SkipBuild,

    [Parameter(Mandatory=$false, HelpMessage="Enable verbose output")]
    [Alias("v")]
    [switch]$VerboseOutput,

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
    run-opentoken.ps1 [OPTIONS]

DESCRIPTION:
    Convenience wrapper for building and running OpenToken via Docker.
    Automatically builds the Docker image if needed and runs OpenToken with specified parameters.

REQUIRED PARAMETERS:
    -InputFile, -i <file>       Input file path (absolute or relative)
    -HashingSecret, -h <key>    Hashing secret key
    -EncryptionKey, -e <key>    Encryption key

OPTIONAL PARAMETERS:
    -OutputFile, -o <file>      Output file path (defaults to <input>_tokenized.<type>)
    -FileType, -t <type>        File type: csv or parquet (default: csv)
    -SkipBuild, -s              Skip Docker image build (use existing image)
    -DockerImage <name>         Docker image name (default: opentoken:latest)
    -Verbose, -v                Enable verbose output
    -Help                       Show this help message

EXAMPLES:
    # Basic usage with CSV files
    .\run-opentoken.ps1 -i C:\Data\input.csv -h "MyHashKey" -e "MyEncryptionKey"

    # With parquet files
    .\run-opentoken.ps1 -i .\data\input.parquet -t parquet -h "secret" -e "key123"

    # Skip Docker build if image already exists
    .\run-opentoken.ps1 -i .\input.csv -h "secret" -e "key" -SkipBuild

    # Verbose mode for troubleshooting
    .\run-opentoken.ps1 -i .\input.csv -h "secret" -e "key" -Verbose

NOTES:
    - This script must be run from the OpenToken repository root directory
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

if (-not $HashingSecret) {
    Write-Info "Hashing secret is required (use -HashingSecret or -h)"
    Write-Host ""
    Show-Usage
    exit 1
}

if (-not $EncryptionKey) {
    Write-Info "Encryption key is required (use -EncryptionKey or -e)"
    Write-Host ""
    Show-Usage
    exit 1
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

if (-not $OutputFile) {
    $InputDirectory = Split-Path -Parent $InputFile
    $InputStem = [System.IO.Path]::GetFileNameWithoutExtension($InputFile)
    $OutputFile = Join-Path $InputDirectory "$InputStem`_tokenized.$FileType"
    Write-Info "No output file provided; using derived path: $OutputFile"
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

# Run OpenToken via Docker
Write-Info "Running OpenToken..."

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
        -i "/data/$InputFilename" `
        -t $FileType `
        -o "/data/$OutputFilename" `
        -h $HashingSecret `
        -e $EncryptionKey
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
        -i "/data/input/$InputFilename" `
        -t $FileType `
        -o "/data/output/$OutputFilename" `
        -h $HashingSecret `
        -e $EncryptionKey
}

if ($LASTEXITCODE -eq 0) {
    Write-Info "OpenToken completed successfully!"
    Write-Info "Output file: $OutputFile"
} else {
    Write-Info "OpenToken execution failed"
    exit 1
}