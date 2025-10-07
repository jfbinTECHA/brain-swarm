#!/usr/bin/env bash
# BrainSwarmOps NGINX + Certbot initialization script

DOMAIN=${1:-localhost}
EMAIL=${2:-"admin@example.com"}

echo "🧠 Initializing Let's Encrypt SSL certificate for $DOMAIN ..."

mkdir -p nginx/certs nginx/letsencrypt nginx/certbot-data

# Run one-time certificate issuance (staging mode optional)
docker run --rm \
  -v $(pwd)/nginx/certs:/etc/letsencrypt/live \
  -v $(pwd)/nginx/letsencrypt:/etc/letsencrypt \
  -v $(pwd)/nginx/certbot-data:/var/www/certbot \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d "$DOMAIN" \
  -m "$EMAIL" \
  --agree-tos --no-eff-email --non-interactive

echo "✅ Certificate generated in nginx/certs/"
echo "🔁 Restart nginx-proxy container to apply new SSL certs."