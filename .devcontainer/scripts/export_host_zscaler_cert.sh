#!/bin/bash

# Script to export Zscaler Root CA certificate from system certificate store
# Works on both macOS and Windows (using Git Bash or WSL)

# Output location within the .devcontainer directory
OUTPUT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_FILE="$OUTPUT_DIR/zscaler_root.pem"
CERT_NAME="Zscaler Root CA"

echo "Attempting to export Zscaler Root CA certificate..."
echo "Output will be saved to: $OUTPUT_FILE"

# Function to check if we're on macOS
is_macos() {
  [[ "$(uname -s)" == "Darwin" ]]
}

# Function to check if we're on Windows
is_windows() {
  [[ "$(uname -s)" == *"MINGW"* ]] || [[ "$(uname -s)" == *"MSYS"* ]] || [[ -n "$WINDIR" ]] || [[ -n "$windir" ]]
}

# Function to export certificate on macOS
export_cert_macos() {
  echo "Detected macOS system..."
  echo "Attempting to export Zscaler Root CA from Keychain..."

  # Check if certificate exists in keychain
  if security find-certificate -a -c "$CERT_NAME" -Z | grep -q "SHA-1"; then
    echo "Certificate found in keychain. Exporting..."

    # Export the certificate
    security find-certificate -a -c "$CERT_NAME" -p > "$OUTPUT_FILE"

    if [ $? -eq 0 ] && [ -s "$OUTPUT_FILE" ]; then
      echo "Certificate successfully exported to $OUTPUT_FILE"
      return 0
    else
      echo "Failed to export certificate or export was empty."
      return 1
    fi
  else
    echo "Certificate not found in keychain."
    return 1
  fi
}

# Function to export certificate on Windows
export_cert_windows() {
  echo "Detected Windows system..."
  echo "Attempting to export Zscaler Root CA from Windows certificate store..."

  # First, check if PowerShell is available
  if command -v powershell.exe &> /dev/null; then
    echo "Using PowerShell to export certificate..."

    # Call the PowerShell script to export the certificate
    PS1_SCRIPT="$OUTPUT_DIR/Export-ZscalerCert.ps1"

    # Check if the PS1 script exists
    if [ -f "$PS1_SCRIPT" ]; then
      echo "Found PowerShell script: $PS1_SCRIPT"
      powershell.exe -ExecutionPolicy Bypass -File "$PS1_SCRIPT"

      if [ $? -eq 0 ] && [ -s "$OUTPUT_FILE" ]; then
        echo "Certificate successfully exported to $OUTPUT_FILE"
        # No need for DER to PEM conversion as the PS1 script already outputs in PEM format
        return 0
      else
        echo "Failed to export certificate or export was empty."
        return 1
      fi
    else
      echo "PowerShell script not found: $PS1_SCRIPT"
      return 1
    fi
  else
    echo "PowerShell not available. Cannot export certificate on Windows without PowerShell."
    return 1
  fi
}

# Main script execution
if is_macos; then
  export_cert_macos
elif is_windows; then
  export_cert_windows
else
  echo "This script only supports macOS and Windows. Detected OS: $(uname -s)"
  exit 1
fi

# Check if we successfully exported a certificate
if [ $? -ne 0 ] || [ ! -s "$OUTPUT_FILE" ]; then
  echo "Failed to export Zscaler Root CA certificate."
  # Remove empty output file if it exists
  [ -f "$OUTPUT_FILE" ] && rm "$OUTPUT_FILE"
  exit 1
fi

echo "Zscaler certificate successfully exported and ready for container use."
exit 0
