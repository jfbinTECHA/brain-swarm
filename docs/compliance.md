# Compliance & Security

This document describes the compliance and security measures implemented for Brain Swarm Ops, including automated SBOM generation, security scanning, and compliance reporting.

## Overview

The compliance pipeline ensures that all code changes are automatically scanned for security vulnerabilities, dependencies are tracked via SBOM, and compliance artifacts are published to the security portal.

## Compliance Pipeline

### Triggers

The compliance workflow runs on:
- **Push to main/develop branches**
- **Pull requests to main**
- **Weekly schedule** (Mondays at 2 AM UTC)
- **Manual trigger** via GitHub Actions

### Jobs

#### 1. SBOM Generation (`sbom`)
- **Tool**: Anchore Syft
- **Format**: SPDX JSON
- **Output**: `sbom.spdx.json`
- **Purpose**: Creates comprehensive Software Bill of Materials

#### 2. Security Scanning (`security-scan`)
- **Tool**: Trivy Vulnerability Scanner
- **Scope**: Filesystem scan
- **Severity**: CRITICAL, HIGH vulnerabilities
- **Output**: SARIF format for GitHub Security tab
- **Reports**: Compliance report with vulnerability counts

#### 3. Container Image Scanning (`container-scan`)
- **Tool**: Trivy
- **Scope**: Built container images
- **Output**: SARIF format
- **Integration**: GitHub Security tab

#### 4. Publish to Security Portal (`publish-compliance`)
- **Artifacts**: SBOM, compliance reports, metadata
- **Format**: Structured compliance package
- **Destination**: Configurable security portal/API

#### 5. Dependency Audit (`dependency-check`)
- **Tools**: `pip-audit`, `safety`
- **Scope**: Python dependencies
- **Output**: Vulnerability reports

#### 6. License Compliance (`license-check`)
- **Tool**: Licensee
- **Scope**: Repository license detection
- **Output**: License compliance report

## SBOM (Software Bill of Materials)

### What is SBOM?

SBOM is a comprehensive inventory of all components, libraries, and dependencies used in the software, including:
- Direct dependencies
- Transitive dependencies
- Versions and licenses
- Vulnerability information

### Generation Process

```yaml
- name: Generate SBOM with Syft
  uses: anchore/sbom-action@v0
  with:
    path: .
    format: spdx-json
    output-file: sbom.spdx.json
```

### SBOM Contents

The generated SBOM includes:
- **Package information**: Name, version, supplier
- **License information**: SPDX license identifiers
- **Dependency relationships**: Parent/child relationships
- **Vulnerability data**: Known CVEs and severity levels

## Security Scanning

### Vulnerability Scanning

**Trivy** performs comprehensive security scanning:

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    scan-ref: '.'
    format: 'sarif'
    severity: 'CRITICAL,HIGH'
```

### Scan Types

1. **Filesystem Scan**: Scans source code and dependencies
2. **Container Scan**: Scans built Docker images
3. **GitHub Integration**: Results appear in Security tab

### Severity Levels

- **CRITICAL**: Immediate security risk
- **HIGH**: Significant security risk
- **MEDIUM**: Moderate security risk
- **LOW**: Minor security risk
- **UNKNOWN**: Unclassified risk

## Compliance Reports

### Generated Reports

1. **SBOM** (`sbom.spdx.json`): Complete software inventory
2. **Compliance Report** (`compliance-report.md`): Security scan summary
3. **Dependency Audit** (`python-audit.md`): Python package vulnerabilities
4. **License Report** (`license-report.md`): License compliance status

### Report Contents

**Compliance Report Example:**
```markdown
## Security Scan Report
- **Date:** 2024-01-15T02:00:00Z
- **Commit:** abc123...
- **Branch:** main

### Vulnerabilities Found
- Total vulnerabilities: 3
- Critical: 0
- High: 2
- Medium: 1
```

## Security Portal Integration

### Package Structure

Compliance packages are structured as:

```
compliance-package/
├── sbom.spdx.json          # Software Bill of Materials
├── compliance-report.md    # Security scan results
├── metadata.json          # Build information
└── README.md              # Package documentation
```

### Metadata Format

```json
{
  "repository": "jfbinTECHA/brain-swarm",
  "commit": "abc123...",
  "branch": "main",
  "timestamp": "2024-01-15T02:00:00Z",
  "workflow_run": "123456789",
  "actor": "github-actor",
  "compliance_version": "1.0"
}
```

### Publishing Methods

#### Option 1: S3 Upload
```bash
aws s3 cp compliance-package/ s3://security-portal-bucket/${COMMIT_SHA}/ --recursive
```

#### Option 2: API Upload
```bash
curl -X POST \
  -H "Authorization: Bearer ${SECURITY_PORTAL_TOKEN}" \
  -F "repository=${REPOSITORY}" \
  -F "commit=${COMMIT_SHA}" \
  -F "sbom=@sbom.spdx.json" \
  -F "report=@compliance-report.md" \
  https://security-portal.company.com/api/compliance/upload
```

#### Option 3: GitHub Release Assets
```yaml
- name: Create compliance release
  uses: actions/create-release@v1
  with:
    tag_name: compliance-${{ github.sha }}
    release_name: Compliance Package ${{ github.sha }}
    body: |
      Automated compliance package for commit ${{ github.sha }}
    assets:
      - sbom.spdx.json
      - compliance-report.md
```

## Configuration

### Required Secrets

Add these secrets to your GitHub repository:

```bash
# For S3 upload
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
SECURITY_PORTAL_BUCKET=your-bucket-name

# For API upload
SECURITY_PORTAL_TOKEN=your-api-token
SECURITY_PORTAL_URL=https://security-portal.company.com
```

### Environment Variables

```bash
# AWS Region for S3 uploads
AWS_REGION=us-east-1

# Security portal configuration
SECURITY_PORTAL_API_URL=https://security-portal.company.com/api
```

## Compliance Gates

### Pull Request Checks

Compliance checks run on pull requests and can:
- **Block merges** if critical vulnerabilities found
- **Require reviews** for high-severity issues
- **Add comments** with compliance status

### Branch Protection

Configure branch protection rules:

```yaml
required_status_checks:
  contexts:
    - "compliance / sbom"
    - "compliance / security-scan"
    - "compliance / container-scan"
```

## Monitoring & Alerts

### Compliance Metrics

Track compliance health using metrics:
- SBOM generation success rate
- Average vulnerabilities per scan
- Time to compliance completion
- Security portal upload success rate

### Alerting Rules

Set up alerts for:
- Failed compliance checks
- Critical vulnerabilities detected
- SBOM generation failures
- Security portal upload failures

## Troubleshooting

### Common Issues

1. **SBOM Generation Fails**
   - Check repository structure
   - Ensure all dependencies are declared
   - Verify file permissions

2. **Security Scan Errors**
   - Check Trivy configuration
   - Verify internet access for vulnerability databases
   - Ensure proper file permissions

3. **Security Portal Upload Fails**
   - Verify API credentials
   - Check network connectivity
   - Validate payload format

### Debug Mode

Enable debug logging:

```yaml
- name: Run Trivy with debug
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    scan-ref: '.'
    format: 'sarif'
    output: 'trivy-results.sarif'
    trivy-config: |
      debug: true
      trace: true
```

## Compliance Standards

### Supported Standards

- **SPDX 2.3**: Software Bill of Materials format
- **SARIF**: Static Analysis Results Interchange Format
- **OWASP Dependency Check**: Vulnerability scanning
- **OSI License Compliance**: Open source license checking

### Regulatory Compliance

The compliance pipeline supports:
- **NIST SSDF**: Secure Software Development Framework
- **CISA SBOM Requirements**: Software Bill of Materials
- **OWASP Application Security Verification Standard**

## Best Practices

1. **Regular Scanning**: Run compliance checks on every commit
2. **Fail Fast**: Block deployments with critical vulnerabilities
3. **Monitor Trends**: Track vulnerability trends over time
4. **Automate Remediation**: Use automated dependency updates
5. **Document Exceptions**: Maintain records of accepted risks
6. **Regular Audits**: Perform manual compliance audits quarterly

## Integration Examples

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    stages {
        stage('Compliance') {
            steps {
                script {
                    // Download compliance artifacts
                    sh 'curl -O https://api.github.com/repos/${REPO}/actions/artifacts/${ARTIFACT_ID}/download'

                    // Process SBOM
                    sh 'syft convert sbom.spdx.json -o cyclonedx-json'

                    // Upload to security portal
                    sh 'curl -X POST -H "Authorization: Bearer ${PORTAL_TOKEN}" -F "sbom=@sbom.cyclonedx.json" ${PORTAL_URL}/api/compliance'
                }
            }
        }
    }
}
```

### GitLab CI

```yaml
compliance:
  stage: compliance
  script:
    - syft . -o spdx-json=sbom.spdx.json
    - trivy fs --format sarif --output trivy.sarif .
    - |
      curl -X POST \
        -H "Authorization: Bearer ${SECURITY_PORTAL_TOKEN}" \
        -F "repository=${CI_PROJECT_PATH}" \
        -F "commit=${CI_COMMIT_SHA}" \
        -F "sbom=@sbom.spdx.json" \
        -F "scan=@trivy.sarif" \
        ${SECURITY_PORTAL_URL}/api/compliance/upload
  artifacts:
    reports:
      sarif: trivy.sarif
    paths:
      - sbom.spdx.json
```

This comprehensive compliance pipeline ensures that Brain Swarm Ops maintains high security standards and regulatory compliance throughout the development lifecycle.