#!/bin/bash

# Create certificates directory if it doesn't exist
mkdir -p certs

# Generate self-signed certificates
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=localhost/emailAddress=email@example.com"

echo "Self-signed certificates generated in the 'certs' directory."
