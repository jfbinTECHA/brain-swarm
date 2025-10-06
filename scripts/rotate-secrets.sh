#!/bin/bash

# Brain Swarm Secret Rotation Script
# This script automates the rotation of secrets in AWS Secrets Manager

set -e

# Configuration
CLUSTER_NAME="${CLUSTER_NAME:-brain-swarm}"
AWS_REGION="${AWS_REGION:-us-east-1}"
NAMESPACE="${NAMESPACE:-brainswarm}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Function to rotate a secret
rotate_secret() {
    local secret_name=$1
    local rotation_interval=$2

    log "Starting rotation for secret: $secret_name"

    # Check if secret exists
    if ! aws secretsmanager describe-secret --secret-id "$secret_name" --region "$AWS_REGION" >/dev/null 2>&1; then
        error "Secret $secret_name does not exist in AWS Secrets Manager"
        return 1
    fi

    # Generate new secret value (this would be customized per secret type)
    local new_value
    case $secret_name in
        *webhook-secret*)
            new_value=$(openssl rand -hex 32)
            ;;
        *github-token*)
            warn "GitHub token rotation requires manual intervention"
            warn "Please generate a new GitHub token and update AWS Secrets Manager"
            return 0
            ;;
        *openai-api-key*)
            warn "OpenAI API key rotation requires manual intervention"
            warn "Please generate a new API key and update AWS Secrets Manager"
            return 0
            ;;
        *)
            new_value=$(openssl rand -hex 32)
            ;;
    esac

    # Update the secret
    aws secretsmanager update-secret \
        --secret-id "$secret_name" \
        --secret-string "$new_value" \
        --region "$AWS_REGION"

    log "Successfully rotated secret: $secret_name"

    # Update rotation date
    aws secretsmanager update-secret-version-stage \
        --secret-id "$secret_name" \
        --version-stage "AWSCURRENT" \
        --move-to-version-id "$(aws secretsmanager list-secret-version-ids --secret-id "$secret_name" --region "$AWS_REGION" --query 'Versions[0].VersionId' --output text)" \
        --region "$AWS_REGION"

    log "Updated rotation timestamp for: $secret_name"
}

# Function to check rotation status
check_rotation_status() {
    local secret_name=$1
    local rotation_interval=$2

    log "Checking rotation status for: $secret_name"

    local last_rotated
    last_rotated=$(aws secretsmanager describe-secret \
        --secret-id "$secret_name" \
        --region "$AWS_REGION" \
        --query 'LastRotatedDate' \
        --output text 2>/dev/null || echo "Never")

    if [ "$last_rotated" = "Never" ]; then
        warn "Secret $secret_name has never been rotated"
        return 1
    fi

    # Calculate days since last rotation
    local last_rotated_epoch
    last_rotated_epoch=$(date -d "$last_rotated" +%s)
    local now_epoch
    now_epoch=$(date +%s)
    local days_since_rotation=$(( (now_epoch - last_rotated_epoch) / 86400 ))

    # Parse rotation interval (e.g., "30d" -> 30)
    local interval_days
    interval_days=$(echo "$rotation_interval" | sed 's/d$//')

    if [ "$days_since_rotation" -gt "$interval_days" ]; then
        warn "Secret $secret_name is overdue for rotation (${days_since_rotation} days since last rotation)"
        return 1
    else
        log "Secret $secret_name is up to date (${days_since_rotation} days since last rotation)"
        return 0
    fi
}

# Main function
main() {
    log "Starting Brain Swarm secret rotation check"

    # Define secrets to rotate
    declare -A secrets=(
        ["brain-swarm/webhook-secret"]="30"
        ["brain-swarm/github-token"]="7"
        ["brain-swarm/openai-api-key"]="90"
    )

    local needs_rotation=0

    # Check all secrets
    for secret in "${!secrets[@]}"; do
        if ! check_rotation_status "$secret" "${secrets[$secret]}d"; then
            needs_rotation=1
        fi
    done

    if [ "$needs_rotation" -eq 1 ]; then
        log "Some secrets need rotation. Starting rotation process..."

        for secret in "${!secrets[@]}"; do
            if ! check_rotation_status "$secret" "${secrets[$secret]}d"; then
                rotate_secret "$secret" "${secrets[$secret]}d"
            fi
        done

        log "Secret rotation completed. Triggering application restart..."

        # Restart deployments that use the secrets
        kubectl rollout restart deployment -n "$NAMESPACE" -l app.kubernetes.io/name=brain-swarm
        kubectl rollout restart deployment -n "$NAMESPACE" -l app.kubernetes.io/name=cortex

        log "Application restart completed"
    else
        log "All secrets are up to date"
    fi

    log "Secret rotation check completed"
}

# Run main function
main "$@"