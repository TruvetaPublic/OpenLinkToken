#!/bin/bash

# Script to detect and install Zscaler Root CA certificate
# This script first checks for a host-provided certificate, then falls back to detection
ZSCALER_CERT_NAME="Zscaler Root CA"
HOST_CERT_PATH="/tmp/host_zscaler_cert.pem"
KNOWN_DOMAINS=("bing.com" "github.com" "google.com" "microsoft.com")
TEMP_DIR="/tmp/zscaler_certs"

echo "===> Checking for Zscaler certificates..."

# First, check if we have a certificate provided from the host
if [ -f "$HOST_CERT_PATH" ] && [ -s "$HOST_CERT_PATH" ]; then
    echo "===> FOUND: Host-provided Zscaler certificate detected"

    # Install the certificate
    cert_cn=$(openssl x509 -in "$HOST_CERT_PATH" -noout -subject 2>/dev/null | sed -n 's/.*CN=\([^,]*\).*/\1/p' | tr ' ' '_' | tr -cd '[:alnum:]._-')
    if [ -z "$cert_cn" ]; then
        cert_cn="host_provided"
    fi

    cert_name="zscaler_host_${cert_cn}.crt"
    cp "$HOST_CERT_PATH" "/usr/local/share/ca-certificates/$cert_name"
    echo "===> Installed host-provided certificate as: $cert_name"

    # Update certificate store
    update-ca-certificates
    echo "===> SUCCESS: Host-provided Zscaler certificate installed and certificate store updated."
    exit 0
fi

echo "===> No host-provided certificate found. Attempting auto-detection..."
mkdir -p "$TEMP_DIR"

# Function to check if a certificate chain contains Zscaler
check_domain_for_zscaler() {
    local domain=$1
    echo "===> Checking domain: $domain"

    # Get certificate chain
    cert_output=$(echo "" | openssl s_client -showcerts -connect ${domain}:443 -timeout 5 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "===> Failed to connect to $domain"
        return 1
    fi

    # Check if Zscaler appears in the certificate chain
    if echo "$cert_output" | grep -qi "zscaler"; then
        echo "===> FOUND: Zscaler certificate detected in connection to $domain"

        # Extract all certificates from the chain
        echo "$cert_output" | sed -n "/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p" > "$TEMP_DIR/cert_chain.pem"

        # Split the certificate chain into individual certificates
        csplit -f "$TEMP_DIR/cert_" -b "%02d.pem" "$TEMP_DIR/cert_chain.pem" "/-----BEGIN CERTIFICATE-----/" "{*}" 2>/dev/null || true

        return 0
    fi

    return 1
}

# Try multiple domains to find Zscaler certificates
zscaler_found=false
for domain in "${KNOWN_DOMAINS[@]}"; do
    if check_domain_for_zscaler "$domain"; then
        zscaler_found=true
        break
    fi
done

if [ "$zscaler_found" = "true" ]; then
    # Find the root certificate (self-signed certificate where issuer equals subject)
    root_cert_found=false
    echo "===> Looking for Zscaler root certificates..."

    # First, try to find certificates with "Zscaler" in the subject
    for cert_file in "$TEMP_DIR"/cert_*.pem; do
        if [ -s "$cert_file" ]; then
            cert_subject=$(openssl x509 -in "$cert_file" -noout -subject 2>/dev/null)
            cert_issuer=$(openssl x509 -in "$cert_file" -noout -issuer 2>/dev/null)

            echo "===> Checking certificate: $(basename "$cert_file")"
            echo "     Subject: $cert_subject"
            echo "     Issuer:  $cert_issuer"

            # Check if this is a Zscaler certificate
            if echo "$cert_subject" | grep -qi "zscaler"; then
                # Extract clean subject and issuer without prefix
                clean_subj=$(echo "$cert_subject" | sed "s/subject=//g")
                clean_issuer=$(echo "$cert_issuer" | sed "s/issuer=//g")

                # Check if this is a root certificate (self-signed: issuer == subject)
                if [ "$clean_subj" = "$clean_issuer" ]; then
                    echo "===> FOUND ROOT: Zscaler self-signed root certificate detected"
                    # Extract common name for filename
                    cert_cn=$(echo "$clean_subj" | sed -n "s/.*CN=\([^,]*\).*/\1/p" | tr " " "_" | tr -cd "[:alnum:]._-")
                    root_cert_name="zscaler_root_${cert_cn}.crt"
                    cp "$cert_file" "/usr/local/share/ca-certificates/$root_cert_name"
                    echo "===> Installed Zscaler root certificate: $root_cert_name"
                    root_cert_found=true
                fi
            fi
        fi
    done

    # If no Zscaler-labeled root found, try to find any self-signed certificate
    if [ "$root_cert_found" = "false" ]; then
        echo "===> No Zscaler-labeled root found, looking for any self-signed certificate..."
        for cert_file in "$TEMP_DIR"/cert_*.pem; do
            if [ -s "$cert_file" ]; then
                # Get clean issuer and subject
                clean_subj=$(openssl x509 -in "$cert_file" -noout -subject 2>/dev/null | sed "s/subject=//g")
                clean_issuer=$(openssl x509 -in "$cert_file" -noout -issuer 2>/dev/null | sed "s/issuer=//g")

                # Check if this is a root certificate (self-signed: issuer == subject)
                if [ "$clean_subj" = "$clean_issuer" ]; then
                    echo "===> FOUND ROOT: Self-signed certificate in Zscaler chain"
                    # Extract common name for filename
                    cert_cn=$(echo "$clean_subj" | sed -n "s/.*CN=\([^,]*\).*/\1/p" | tr " " "_" | tr -cd "[:alnum:]._-")
                    root_cert_name="zscaler_proxy_root_${cert_cn}.crt"
                    cp "$cert_file" "/usr/local/share/ca-certificates/$root_cert_name"
                    echo "===> Installed proxy root certificate: $root_cert_name"
                    root_cert_found=true
                fi
            fi
        done
    fi

    # If no self-signed root found, use the last certificate in the chain
    if [ "$root_cert_found" = "false" ]; then
        echo "===> No self-signed root found, installing last certificate in chain..."
        last_cert=$(ls "$TEMP_DIR"/cert_*.pem 2>/dev/null | sort -V | tail -1)
        if [ -n "$last_cert" ] && [ -s "$last_cert" ]; then
            cert_subject=$(openssl x509 -in "$last_cert" -noout -subject 2>/dev/null)
            cert_cn=$(echo "$cert_subject" | sed -n "s/.*CN=\([^,]*\).*/\1/p" | tr " " "_" | tr -cd "[:alnum:]._-")
            fallback_cert_name="zscaler_chain_root_${cert_cn}.crt"
            cp "$last_cert" "/usr/local/share/ca-certificates/$fallback_cert_name"
            echo "===> Installed chain root certificate: $fallback_cert_name"
            root_cert_found=true
        fi
    fi

    # Update certificate store if we found and installed a root certificate
    if [ "$root_cert_found" = "true" ]; then
        update-ca-certificates
        echo "===> SUCCESS: Zscaler root certificate installed and certificate store updated."
        exit 0
    else
        echo "===> ERROR: No suitable root certificate found in chain."
        exit 1
    fi
else
    echo "===> NOT FOUND: No Zscaler certificates detected. Skipping certificate installation."
    exit 0
fi
