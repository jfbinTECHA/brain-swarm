"""
Secrets hygiene validation utilities for Brain Swarm
Ensures no hardcoded secrets in code and configuration
"""

import os
import re
import hashlib
from typing import List, Dict, Any
from pathlib import Path

try:
    from ..core.base import logger
except ImportError:
    # Fallback for standalone execution
    import logging
    logger = logging.getLogger(__name__)
    logger.log = lambda level, component, message, data=None: print(f"[{level}] {component}: {message}")


class SecretsHygieneValidator:
    """Validates that secrets are not hardcoded in code and configuration"""

    # Patterns that indicate potential hardcoded secrets
    SECRET_PATTERNS = [
        # API Keys
        r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']([a-zA-Z0-9_-]{20,})["\']',
        r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*["\']([a-zA-Z0-9_-]{20,})["\']',
        r'(?i)(access[_-]?token|accesstoken)\s*[=:]\s*["\']([a-zA-Z0-9_-]{20,})["\']',

        # Passwords
        r'(?i)password\s*[=:]\s*["\']([^"\']{8,})["\']',
        r'(?i)passwd\s*[=:]\s*["\']([^"\']{8,})["\']',

        # JWT Secrets
        r'(?i)jwt[_-]?secret\s*[=:]\s*["\']([a-zA-Z0-9_-]{10,})["\']',

        # Database credentials
        r'(?i)(db[_-]?password|dbpassword)\s*[=:]\s*["\']([^"\']{4,})["\']',
        r'(?i)(database[_-]?password|databasepassword)\s*[=:]\s*["\']([^"\']{4,})["\']',

        # Generic long strings that might be secrets
        r'["\']([a-zA-Z0-9_-]{32,})["\']',  # 32+ character strings
    ]

    # Files to exclude from validation
    EXCLUDE_PATTERNS = [
        r'.*\.pyc$',
        r'.*__pycache__.*',
        r'.*\.git.*',
        r'.*\.env$',
        r'.*\.secret$',
        r'.*secrets\.json$',
        r'.*config\.json$',
        r'.*test.*\.py$',  # Test files might have mock secrets
        r'.*conftest\.py$',
    ]

    # Known safe patterns (false positives to ignore)
    SAFE_PATTERNS = [
        r'.*example.*',
        r'.*placeholder.*',
        r'.*your[_-].*',
        r'.*change[_-].*',
        r'.*replace[_-].*',
        r'.*dummy.*',
        r'.*mock.*',
        r'.*test.*',
        r'.*sample.*',
        r'.*template.*',
    ]

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.violations = []

    def validate_project(self) -> Dict[str, Any]:
        """Validate the entire project for secrets hygiene"""
        self.violations = []

        # Scan all relevant files
        for file_path in self._get_files_to_scan():
            self._validate_file(file_path)

        # Generate report
        report = {
            "total_files_scanned": len(list(self._get_files_to_scan())),
            "violations_found": len(self.violations),
            "violations": self.violations,
            "severity": self._calculate_severity(),
            "recommendations": self._generate_recommendations()
        }

        if self.violations:
            logger.log("WARNING", "SecretsHygiene", f"Found {len(self.violations)} potential secrets hygiene violations")
        else:
            logger.log("INFO", "SecretsHygiene", "No secrets hygiene violations found")

        return report

    def _get_files_to_scan(self):
        """Get all files that should be scanned for secrets"""
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file() and self._should_scan_file(file_path):
                yield file_path

    def _should_scan_file(self, file_path: Path) -> bool:
        """Determine if a file should be scanned"""
        file_str = str(file_path)

        # Check exclude patterns
        for pattern in self.EXCLUDE_PATTERNS:
            if re.match(pattern, file_str):
                return False

        # Only scan text files
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)  # Try to read first 1KB
            return True
        except (UnicodeDecodeError, IOError):
            return False

    def _validate_file(self, file_path: Path):
        """Validate a single file for hardcoded secrets"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()

            for line_num, line in enumerate(lines, 1):
                for pattern in self.SECRET_PATTERNS:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        potential_secret = match.group(1) if len(match.groups()) > 0 else match.group(0)

                        # Check if it's a known safe pattern
                        if not self._is_safe_pattern(potential_secret, line):
                            violation = {
                                "file": str(file_path.relative_to(self.project_root)),
                                "line": line_num,
                                "pattern": pattern,
                                "potential_secret": self._mask_secret(potential_secret),
                                "context": line.strip(),
                                "severity": self._calculate_violation_severity(potential_secret, pattern)
                            }
                            self.violations.append(violation)

        except Exception as e:
            logger.log("ERROR", "SecretsHygiene", f"Error scanning file {file_path}: {e}")

    def _is_safe_pattern(self, secret: str, line: str) -> bool:
        """Check if a potential secret is actually safe"""
        secret_lower = secret.lower()
        line_lower = line.lower()

        # Check safe patterns
        for pattern in self.SAFE_PATTERNS:
            if re.search(pattern, secret_lower) or re.search(pattern, line_lower):
                return True

        # Check if it's a well-known test/example value
        known_safe_values = [
            "your-secret-key-change-in-production",
            "your-jwt-secret-here",
            "sk-test-",
            "pk_test_",
            "example-api-key",
            "placeholder-secret"
        ]

        for safe_value in known_safe_values:
            if safe_value in secret_lower:
                return True

        return False

    def _mask_secret(self, secret: str) -> str:
        """Mask a secret for safe logging"""
        if len(secret) <= 8:
            return secret  # Too short to be a real secret
        elif len(secret) <= 16:
            return secret[:4] + "*" * (len(secret) - 8) + secret[-4:]
        else:
            return secret[:8] + "*" * (len(secret) - 16) + secret[-8:]

    def _calculate_violation_severity(self, secret: str, pattern: str) -> str:
        """Calculate the severity of a violation"""
        secret_length = len(secret)

        # High severity for very long secrets or specific patterns
        if secret_length > 50:
            return "high"
        elif secret_length > 32:
            return "medium"
        elif any(word in pattern.lower() for word in ["password", "secret", "key"]):
            return "medium"
        else:
            return "low"

    def _calculate_severity(self) -> str:
        """Calculate overall severity of all violations"""
        if not self.violations:
            return "clean"

        high_count = sum(1 for v in self.violations if v["severity"] == "high")
        medium_count = sum(1 for v in self.violations if v["severity"] == "medium")

        if high_count > 0:
            return "high"
        elif medium_count > 2:
            return "medium"
        elif len(self.violations) > 5:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on violations found"""
        recommendations = []

        if not self.violations:
            recommendations.append("✅ No secrets hygiene violations found. Good job!")
            return recommendations

        severity = self._calculate_severity()

        if severity == "high":
            recommendations.append("🚨 HIGH PRIORITY: Critical secrets hygiene violations found. Address immediately.")
            recommendations.append("• Move all secrets to environment variables or secrets manager")
            recommendations.append("• Use .env files for development (ensure .env is in .gitignore)")
            recommendations.append("• Implement HashiCorp Vault or AWS Secrets Manager for production")

        elif severity == "medium":
            recommendations.append("⚠️  MEDIUM PRIORITY: Potential secrets hygiene issues found.")
            recommendations.append("• Review and move identified secrets to secure storage")
            recommendations.append("• Implement secrets rotation policies")

        else:
            recommendations.append("ℹ️  LOW PRIORITY: Minor secrets hygiene issues found.")
            recommendations.append("• Consider moving identified values to configuration")

        # Specific recommendations based on violation types
        has_passwords = any("password" in v["pattern"].lower() for v in self.violations)
        has_api_keys = any("api" in v["pattern"].lower() for v in self.violations)
        has_jwt = any("jwt" in v["pattern"].lower() for v in self.violations)

        if has_passwords:
            recommendations.append("• Passwords detected: Use bcrypt/scrypt for password hashing")
        if has_api_keys:
            recommendations.append("• API keys detected: Rotate keys and store securely")
        if has_jwt:
            recommendations.append("• JWT secrets detected: Use strong, random secrets and rotate regularly")

        recommendations.append("• Run secrets hygiene validation in CI/CD pipeline")
        recommendations.append("• Implement automated secrets detection tools")

        return recommendations


def validate_secrets_hygiene(project_root: str = None) -> Dict[str, Any]:
    """Convenience function to validate secrets hygiene"""
    validator = SecretsHygieneValidator(project_root)
    return validator.validate_project()


if __name__ == "__main__":
    # Run validation on current project
    report = validate_secrets_hygiene()
    print(f"Secrets Hygiene Report: {report['severity'].upper()}")
    print(f"Files scanned: {report['total_files_scanned']}")
    print(f"Violations found: {report['violations_found']}")

    if report['violations']:
        print("\nViolations:")
        for violation in report['violations'][:10]:  # Show first 10
            print(f"  {violation['file']}:{violation['line']} - {violation['severity']} - {violation['potential_secret']}")

    print("\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  {rec}")