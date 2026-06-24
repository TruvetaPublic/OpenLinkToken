# run-openlinktoken.ps1
# Convenience script to run Open Link Token via Docker.
# Automatically builds the Docker image when needed, mounts all required file
# paths into the container, and forwards every option to the olt CLI.
#
# Usage: .\run-openlinktoken.ps1 <subcommand> [options]
# Run with -Help for full usage information.

[CmdletBinding()]
param(
    [Parameter(Position=0, Mandatory=$true,
        HelpMessage="Subcommand: package, tokenize, encrypt, decrypt, initiate-exchange, or generate-key-pair")]
    [ValidateSet("package", "tokenize", "encrypt", "decrypt", "initiate-exchange", "generate-key-pair")]
    [string]$Subcommand,

    [Parameter(Mandatory=$false, HelpMessage="Docker image name (default: openlinktoken:latest)")]
    [string]$DockerImage = "openlinktoken:latest",

    [Parameter(Mandatory=$false, HelpMessage="Skip Docker image build (use existing image)")]
    [switch]$SkipBuild,

    [Parameter(Mandatory=$false, HelpMessage="Show help message")]
    [switch]$Help,

    # All remaining arguments are forwarded to olt inside the container.
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$OltArgs
)

function Write-OltInfo    { param([string]$Msg) Write-Host "[INFO] $Msg" }
function Write-OltSuccess { param([string]$Msg) Write-Host "[OK]   $Msg" }
function Write-OltError   { param([string]$Msg) Write-Host "[ERR]  $Msg" -ForegroundColor Red }

function Show-Usage {
    Write-Host @"

USAGE:
    .\run-openlinktoken.ps1 <Subcommand> [OltOptions] [-DockerImage name] [-SkipBuild] [-Verbose]

DESCRIPTION:
    Docker convenience wrapper for Open Link Token. Builds the Docker image when
    needed, mounts file paths into the container, and forwards all options to olt.

SUBCOMMANDS:
    package             Tokenize and encrypt in one step
    tokenize            Generate hashed tokens (--mode hash-only for SHA-256 only)
    encrypt             Encrypt previously tokenized output
    decrypt             Decrypt encrypted tokens
    initiate-exchange   Create an exchange config from a partner's public key
    generate-key-pair   Generate an ECDH key pair (written to ~/.openlinktoken/)

OLT OPTIONS (forwarded to the container -- see olt help <subcommand> for full details):
    -i / --input PATH               Input file (package, tokenize, encrypt, decrypt)
    -o / --output PATH              Output file
    --exchange-config PATH          Exchange config JSON
    --private-key PATH              Private key PEM file
    --private-key-env VAR           Read private key from this environment variable
    --public-key PATH               Partner public key PEM (initiate-exchange)
    --public-key-env VAR            Read partner public key from this environment variable
    --public-key-stdin              Read partner public key from stdin
    --sender-private-key PATH       Sender private key PEM (initiate-exchange)
    --sender-private-key-env VAR    Read sender private key from this environment variable
    --hashingsecret SECRET          Hashing secret (initiate-exchange)
    --hashingsecret-env VAR         Read hashing secret from this environment variable
    --hashingsecret-stdin           Read hashing secret from stdin
    --mode MODE                     Tokenize mode: olt|hash-only|demo
    --ring-id ID                    Ring identifier (package, encrypt)
    --hash-record-ids               Hash record IDs before writing output
    -n / --name NAME                Key/config base name (generate-key-pair, initiate-exchange)
    -c / --curve CURVE              EC curve: P-256, P-384, P-521 (default: P-256)
    --force                         Overwrite existing key or config files
    -q / --no-progress              Suppress progress indicator

SCRIPT OPTIONS:
    -DockerImage <name>     Docker image name (default: openlinktoken:latest)
    -SkipBuild              Skip Docker image build
    -Verbose                Verbose output
    -Help                   Show this message

NOTES:
    - Run from the Open Link Token repository root directory
    - ~/.openlinktoken/ is always mounted so key files persist across runs
    - File paths are automatically resolved and mounted into the container
    - Environment variables named by --*-env flags are forwarded to the container

EXAMPLES:
    # Generate a key pair
    .\run-openlinktoken.ps1 generate-key-pair --name recipient

    # Create an exchange config from the recipient's public key
    .\run-openlinktoken.ps1 initiate-exchange --public-key "`$HOME\.openlinktoken\recipient.public.pem"

    # Tokenize and encrypt
    .\run-openlinktoken.ps1 package ``
        -i .\data\input.csv -o .\data\output.zip ``
        --exchange-config .\openlinktoken.exchange.json ``
        --private-key "`$HOME\.openlinktoken\mykey.private.pem"

    # Hash-only tokenize (no exchange config needed)
    .\run-openlinktoken.ps1 tokenize --mode hash-only -i .\data\input.csv -o .\data\hashed.csv

    # Decrypt
    .\run-openlinktoken.ps1 decrypt ``
        -i .\data\output.zip -o .\data\decrypted.csv ``
        --exchange-config .\openlinktoken.exchange.json ``
        --private-key "`$HOME\.openlinktoken\mykey.private.pem"

    # Use an existing image (skip rebuild)
    .\run-openlinktoken.ps1 package --skip-build ``
        -i .\input.csv -o .\output.zip --exchange-config .\openlinktoken.exchange.json

"@
}

if ($Help) { Show-Usage; exit 0 }

# ─── Docker check ─────────────────────────────────────────────────────────────

try {
    $null = docker --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw }
} catch {
    Write-OltError "Docker is not installed or not in PATH."
    Write-OltError "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
}

# ─── Volume mount planning ────────────────────────────────────────────────────
# Flags whose next argument is a host file path that must be mounted.
$FileFlagSet = [System.Collections.Generic.HashSet[string]]@(
    "-i", "--input", "-o", "--output",
    "--exchange-config", "--private-key", "--public-key", "--sender-private-key"
)

# Flags whose next argument is an environment variable name — forward the var.
$EnvVarFlagSet = [System.Collections.Generic.HashSet[string]]@(
    "--private-key-env", "--hashingsecret-env", "--public-key-env", "--sender-private-key-env"
)

# Flags that indicate stdin will be used.
$StdinFlagSet = [System.Collections.Generic.HashSet[string]]@(
    "--hashingsecret-stdin", "--public-key-stdin"
)

$DirMap      = @{}   # host_dir -> container mount point
$MountArgs   = [System.Collections.Generic.List[string]]::new()
$EnvPassArgs = [System.Collections.Generic.List[string]]::new()
$MountIndex  = 0
$NeedsStdin  = $false

# Always mount ~/.openlinktoken so key files persist.
$OltHome = [System.IO.Path]::GetFullPath((Join-Path $HOME ".openlinktoken"))
if (-not (Test-Path $OltHome)) { New-Item -ItemType Directory -Path $OltHome -Force | Out-Null }
$DirMap[$OltHome] = "/root/.openlinktoken"
$MountArgs.AddRange([string[]]@("-v", "${OltHome}:/root/.openlinktoken"))

function Get-ContainerDir {
    param([string]$HostDir)
    if (-not $DirMap.ContainsKey($HostDir)) {
        $ContainerDir = "/data/$MountIndex"
        $DirMap[$HostDir] = $ContainerDir
        $MountArgs.AddRange([string[]]@("-v", "${HostDir}:${ContainerDir}"))
        $script:MountIndex++
    }
    return $DirMap[$HostDir]
}

function Resolve-ToAbsolute {
    param([string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Path))
}

function Get-RemappedPath {
    param([string]$HostPath)
    $Abs  = Resolve-ToAbsolute $HostPath
    $Dir  = Split-Path -Parent $Abs
    $File = Split-Path -Leaf  $Abs
    if (-not (Test-Path $Dir)) { New-Item -ItemType Directory -Path $Dir -Force | Out-Null }
    $ContainerDir = Get-ContainerDir $Dir
    return "$ContainerDir/$File"
}

# ─── First pass: register dirs, collect env var forwarding ───────────────────

$Args = if ($OltArgs) { $OltArgs } else { @() }
$i = 0
while ($i -lt $Args.Count) {
    $arg = $Args[$i]
    if ($FileFlagSet.Contains($arg)) {
        $path = $Args[$i + 1]
        $abs  = Resolve-ToAbsolute $path
        $dir  = Split-Path -Parent $abs
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        $null = Get-ContainerDir $dir
        $i += 2
    } elseif ($EnvVarFlagSet.Contains($arg)) {
        $VarName  = $Args[$i + 1]
        $VarValue = [System.Environment]::GetEnvironmentVariable($VarName)
        if ($null -ne $VarValue) {
            $EnvPassArgs.AddRange([string[]]@("-e", "${VarName}=${VarValue}"))
        }
        $i += 2
    } elseif ($StdinFlagSet.Contains($arg)) {
        $NeedsStdin = $true
        $i++
    } else {
        $i++
    }
}

# ─── Second pass: rewrite file path values to container-internal paths ────────

$RemappedArgs = [System.Collections.Generic.List[string]]::new()
$i = 0
while ($i -lt $Args.Count) {
    $arg = $Args[$i]
    if ($FileFlagSet.Contains($arg)) {
        $path      = $Args[$i + 1]
        $remapped  = Get-RemappedPath $path
        $RemappedArgs.AddRange([string[]]@($arg, $remapped))
        $i += 2
    } else {
        $RemappedArgs.Add($arg)
        $i++
    }
}

# ─── Docker build ─────────────────────────────────────────────────────────────

if (-not $SkipBuild) {
    docker image inspect $DockerImage > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        if ($VerbosePreference -ne 'SilentlyContinue') {
            Write-OltInfo "Using existing image '$DockerImage'"
        }
    } else {
        Write-OltInfo "Building Docker image '$DockerImage' (first run may take a few minutes)..."
        if ($VerbosePreference -ne 'SilentlyContinue') {
            docker build -t $DockerImage .
        } else {
            docker build -t $DockerImage . 2>&1 | Out-Null
        }
        if ($LASTEXITCODE -ne 0) { Write-OltError "Docker build failed"; exit 1 }
        Write-OltSuccess "Docker image built"
    }
} else {
    Write-OltInfo "Skipping Docker build"
    docker image inspect $DockerImage > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-OltError "Image '$DockerImage' not found. Run without -SkipBuild first."
        exit 1
    }
}

# ─── Run ──────────────────────────────────────────────────────────────────────

if ($VerbosePreference -ne 'SilentlyContinue') {
    Write-OltInfo "Subcommand: $Subcommand"
    Write-OltInfo "Mounts:     $($MountArgs -join ' ')"
    Write-OltInfo "Env:        $($EnvPassArgs -join ' ')"
    Write-OltInfo "Args:       $($RemappedArgs -join ' ')"
}

Write-OltInfo "Running Open Link Token ($Subcommand)..."

$DockerRunOpts = [System.Collections.Generic.List[string]]@("run", "--rm")
if ($NeedsStdin) { $DockerRunOpts.Add("-i") }
$DockerRunOpts.AddRange($MountArgs)
$DockerRunOpts.AddRange($EnvPassArgs)
$DockerRunOpts.Add($DockerImage)
$DockerRunOpts.Add($Subcommand)
$DockerRunOpts.AddRange($RemappedArgs)

& docker @DockerRunOpts

if ($LASTEXITCODE -eq 0) {
    Write-OltSuccess "Completed successfully"
} else {
    Write-OltError "Open Link Token exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}
