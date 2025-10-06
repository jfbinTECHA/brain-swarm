# Secret Rotation Automation

This document describes the automated secret rotation system for Brain Swarm Ops using AWS Secrets Manager and the External Secrets Operator.

## Overview

The system provides automated rotation of sensitive credentials and API keys with the following features:

- **Automated Rotation**: Secrets are rotated on configurable schedules
- **External Management**: Secrets stored securely in AWS Secrets Manager
- **Application Integration**: Seamless integration with Kubernetes applications
- **Audit Trail**: Full logging of rotation events

## Architecture

```
AWS Secrets Manager <-> External Secrets Operator <-> Kubernetes Secrets <-> Applications
```

## Supported Secrets

| Secret | Rotation Interval | Description |
|--------|------------------|-------------|
| Webhook Secret | 30 days | Used for webhook authentication |
| GitHub Token | 7 days | GitHub API access token |
| OpenAI API Key | 90 days | OpenAI API authentication |
| S3 Configuration | Manual | Static S3 bucket configuration |

## Prerequisites

### AWS Setup

1. **IAM Policy**: Create an IAM policy for secret access:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:ListSecretVersionIds",
        "secretsmanager:UpdateSecret",
        "secretsmanager:UpdateSecretVersionStage"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:brain-swarm/*"
    }
  ]
}
```

2. **IAM Role**: Create an IAM role for the Kubernetes service account with the above policy.

3. **Secrets**: Create the required secrets in AWS Secrets Manager:
```bash
# Webhook secret
aws secretsmanager create-secret \
  --name "brain-swarm/webhook-secret" \
  --secret-string "$(openssl rand -hex 32)"

# GitHub token (replace with actual token)
aws secretsmanager create-secret \
  --name "brain-swarm/github-token" \
  --secret-string "ghp_your_github_token_here"

# OpenAI API key (replace with actual key)
aws secretsmanager create-secret \
  --name "brain-swarm/openai-api-key" \
  --secret-string "sk-your_openai_key_here"
```

### Kubernetes Setup

1. **Service Account**: Annotate the service account for IAM role assumption:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: brain-swarm-sa
  namespace: brainswarm
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/brain-swarm-secrets-role
```

2. **AWS Credentials**: Create a secret with AWS credentials for the rotation job:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: brain-swarm-aws-credentials
  namespace: brainswarm
type: Opaque
data:
  credentials: <base64-encoded-aws-credentials>
```

## Configuration

### Helm Values

Enable secret rotation in your `values-prod.yaml`:

```yaml
monitoring:
  externalSecrets:
    enabled: true
    aws:
      enabled: true
      region: us-east-1
    secrets:
      webhookSecret:
        rotationEnabled: true
        rotationInterval: 30d
        awsSecretName: "brain-swarm/webhook-secret"
      githubToken:
        rotationEnabled: true
        rotationInterval: 7d
        awsSecretName: "brain-swarm/github-token"
      openaiApiKey:
        rotationEnabled: true
        rotationInterval: 90d
        awsSecretName: "brain-swarm/openai-api-key"
```

### Rotation Intervals

- **30 days**: Webhook secrets (high rotation for security)
- **7 days**: GitHub tokens (frequent rotation due to exposure)
- **90 days**: OpenAI API keys (balance between security and usability)

## Operation

### Automatic Rotation

The system automatically rotates secrets based on the configured intervals:

1. **Daily Check**: CronJob runs daily at 2 AM
2. **Status Assessment**: Checks last rotation date for each secret
3. **Rotation Execution**: Rotates overdue secrets
4. **Application Restart**: Restarts affected deployments to pick up new secrets

### Manual Rotation

To manually rotate a secret:

```bash
# Run the rotation script
kubectl exec -n brainswarm deployment/brain-swarm-secret-rotation -- ./rotate-secrets.sh

# Or trigger the CronJob manually
kubectl create job -n brainswarm --from=cronjob/brain-swarm-secret-rotation manual-rotation
```

### Monitoring Rotation

Check rotation status:

```bash
# View rotation job logs
kubectl logs -n brainswarm -l app.kubernetes.io/name=secret-rotation

# Check secret last rotation dates
aws secretsmanager describe-secret --secret-id brain-swarm/webhook-secret --query 'LastRotatedDate'
```

## Security Considerations

### Access Control

- **Principle of Least Privilege**: IAM roles have minimal required permissions
- **Network Security**: ESO runs within the cluster, accessing AWS via IAM roles
- **Audit Logging**: All rotation events are logged for compliance

### Secret Types

- **Automatic Rotation**: Webhook secrets are auto-generated
- **Manual Intervention**: GitHub tokens and OpenAI keys require manual updates in AWS Secrets Manager
- **Static Secrets**: S3 configuration remains static (infrequent changes)

### Backup and Recovery

- **AWS Backup**: Secrets are automatically backed up by AWS
- **Version History**: AWS maintains version history for rollback
- **Emergency Access**: Break-glass procedures for immediate rotation

## Troubleshooting

### Common Issues

1. **IAM Permissions**: Check service account annotations and IAM role policies
2. **Secret Not Found**: Verify secret names in AWS Secrets Manager
3. **Rotation Failures**: Check CronJob logs for detailed error messages

### Logs and Debugging

```bash
# ESO controller logs
kubectl logs -n brainswarm deployment/external-secrets

# Rotation job logs
kubectl logs -n brainswarm -l job-name=brain-swarm-secret-rotation

# AWS CLI debugging
aws secretsmanager list-secrets --region us-east-1
```

## Alternative: HashiCorp Vault

For environments preferring Vault over AWS Secrets Manager:

```yaml
monitoring:
  externalSecrets:
    vault:
      enabled: true
      server: "https://vault.example.com:8200"
      path: "secret/brain-swarm"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "brain-swarm"
```

## Best Practices

1. **Regular Review**: Review rotation intervals and adjust based on security requirements
2. **Monitoring**: Set up alerts for rotation failures
3. **Testing**: Test rotation in non-production environments first
4. **Documentation**: Keep secret naming conventions and procedures documented
5. **Compliance**: Ensure rotation meets organizational security policies