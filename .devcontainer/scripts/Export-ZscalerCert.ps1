# Export-ZscalerCert.ps1
# PowerShell script to export Zscaler Root CA certificate from the Windows certificate store

$OutputDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutputFile = Join-Path -Path $OutputDir -ChildPath "zscaler_root.pem"
$CertName = "Zscaler Root CA"

Write-Host "Attempting to export Zscaler Root CA certificate..."
Write-Host "Output will be saved to: $OutputFile"

# First try LocalMachine\Root store
Write-Host "Checking LocalMachine\Root store..."
$cert = Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object {$_.Subject -match "CN=$CertName"} | Select-Object -First 1

if (-not $cert) {
    # Try CurrentUser\Root store if not found in LocalMachine
    Write-Host "Certificate not found in LocalMachine\Root. Checking CurrentUser\Root store..."
    $cert = Get-ChildItem -Path Cert:\CurrentUser\Root | Where-Object {$_.Subject -match "CN=$CertName"} | Select-Object -First 1
}

if ($cert) {
    Write-Host "Zscaler certificate found:"
    Write-Host "  Subject: $($cert.Subject)"
    Write-Host "  Issuer:  $($cert.Issuer)"
    Write-Host "  Thumbprint: $($cert.Thumbprint)"

    # Export the certificate to PEM format
    try {
        # First export as Base64 (PEM)
        $certBytes = $cert.Export("Cert")
        # Convert to PEM format with proper headers
        $pemContent = "-----BEGIN CERTIFICATE-----`n"
        $pemContent += [Convert]::ToBase64String($certBytes, "InsertLineBreaks")
        $pemContent += "`n-----END CERTIFICATE-----"

        # Save to file
        [System.IO.File]::WriteAllText($OutputFile, $pemContent)

        Write-Host "Certificate successfully exported to $OutputFile"
        exit 0
    }
    catch {
        Write-Host "Error exporting certificate: $_"
        exit 1
    }
}
else {
    Write-Host "No Zscaler certificate found in certificate stores."

    # Try to find any certificate with Zscaler in the name
    Write-Host "Looking for any certificate with 'Zscaler' in the name..."
    $zscalerCerts = Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object {$_.Subject -like "*Zscaler*"} | Select-Object -First 1

    if (-not $zscalerCerts) {
        $zscalerCerts = Get-ChildItem -Path Cert:\CurrentUser\Root | Where-Object {$_.Subject -like "*Zscaler*"} | Select-Object -First 1
    }

    if ($zscalerCerts) {
        Write-Host "Found certificate with Zscaler in the name:"
        Write-Host "  Subject: $($zscalerCerts.Subject)"
        Write-Host "  Issuer:  $($zscalerCerts.Issuer)"

        # Export the certificate
        try {
            # Export as Base64 (PEM)
            $certBytes = $zscalerCerts.Export("Cert")
            # Convert to PEM format with proper headers
            $pemContent = "-----BEGIN CERTIFICATE-----`n"
            $pemContent += [Convert]::ToBase64String($certBytes, "InsertLineBreaks")
            $pemContent += "`n-----END CERTIFICATE-----"

            # Save to file
            [System.IO.File]::WriteAllText($OutputFile, $pemContent)

            Write-Host "Alternative Zscaler certificate exported to $OutputFile"
            exit 0
        }
        catch {
            Write-Host "Error exporting certificate: $_"
            exit 1
        }
    }
    else {
        Write-Host "No Zscaler-related certificates found."
        exit 1
    }
}
