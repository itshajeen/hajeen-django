#!/bin/bash
DOMAIN=${DOMAIN_NAME}
SSL_CERT="/etc/nginx/ssl/live/$DOMAIN/fullchain.pem"
SSL_KEY="/etc/nginx/ssl/live/$DOMAIN/privkey.pem"
SSL_CONF="/etc/nginx/conf.d/ssl.conf"
SSL_TEMPLATE="/etc/nginx/conf.d/ssl.conf.template"
echo "Starting check_and_enable_ssl script for domain: $DOMAIN"

# Check if both SSL certificate and key exist
if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
    echo "SSL certificate and key for $DOMAIN found."
    echo "Copying $SSL_TEMPLATE to $SSL_CONF"
    
    # Ensure the template file exists before copying
    if [ -f "$SSL_TEMPLATE" ]; then
        cp "$SSL_TEMPLATE" "$SSL_CONF"
        echo "SSL configuration applied."
        nginx -t && nginx -s reload
    else
        echo "SSL template $SSL_TEMPLATE not found!"
    fi
else
    echo "SSL certificate or key for $DOMAIN not found. Removing SSL configuration."
    rm -f "$SSL_CONF"
    nginx -t && nginx -s reload
fi