#!/bin/bash
DOMAIN=${DOMAIN_NAME}
SSL_CERT="/etc/nginx/ssl/live/$DOMAIN/fullchain.pem"
SSL_KEY="/etc/nginx/ssl/live/$DOMAIN/privkey.pem"
echo "Starting check_ssl_exist_or_no script for domain: $DOMAIN"

# Check if both SSL certificate and key exist
if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
    echo "SSL certificate and key for $DOMAIN found. No need for new ones."
else
    echo "SSL certificate or key for $DOMAIN not found. Creating new one."
    certbot certonly --webroot --webroot-path=/var/www/certbot --email salahelsayed995@gmail.com --agree-tos --no-eff-email  --non-interactive -d $DOMAIN 
    if [ $? -ne 0 ]; then
        echo "Failed to generate SSL certificate for $DOMAIN."
        exit 1
    fi
fi

# Start the renewal procees 
while :; do
    certbot renew
    echo "Certificate renewed for $DOMAIN."
    sleep 12h
done