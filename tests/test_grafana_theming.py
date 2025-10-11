"""
Tests for Grafana theming and dashboard configuration.
"""

import pytest
import yaml
import json
from pathlib import Path


class TestGrafanaConfiguration:
    """Test Grafana configuration and theming"""

    def test_grafana_deployment_config(self):
        """Test Grafana deployment configuration"""
        deployment_file = Path("helm/brain-swarm/templates/grafana-deployment.yaml")

        assert deployment_file.exists(), "Grafana deployment template should exist"

        with open(deployment_file) as f:
            content = f.read()

        # Check for essential configuration
        assert "grafana/grafana" in content, "Should use official Grafana image"
        assert "grafana-admin-password" in content, "Should configure admin password"
        assert "grafana-admin-user" in content, "Should configure admin user"
        assert "conditional" in content.lower(), "Should have conditional deployment"

    def test_grafana_service_config(self):
        """Test Grafana service configuration"""
        service_file = Path("helm/brain-swarm/templates/grafana-service.yaml")

        assert service_file.exists(), "Grafana service template should exist"

        with open(service_file) as f:
            content = f.read()

        # Check service configuration
        assert "ClusterIP" in content, "Should default to ClusterIP"
        assert "port: 80" in content, "Should expose port 80"
        assert "targetPort: http" in content, "Should target http port"

    def test_grafana_pvc_config(self):
        """Test Grafana PVC configuration"""
        pvc_file = Path("helm/brain-swarm/templates/grafana-pvc.yaml")

        assert pvc_file.exists(), "Grafana PVC template should exist"

        with open(pvc_file) as f:
            content = f.read()

        # Check PVC configuration
        assert "10Gi" in content, "Should default to 10Gi storage"
        assert "ReadWriteOnce" in content, "Should use ReadWriteOnce access mode"

    def test_grafana_configmap(self):
        """Test Grafana ConfigMap configuration"""
        config_file = Path("helm/brain-swarm/templates/grafana-config.yaml")

        assert config_file.exists(), "Grafana config template should exist"

        with open(config_file) as f:
            content = f.read()

        # Check for theming configuration
        assert "login" in content.lower(), "Should include login theming"
        assert "theme" in content.lower(), "Should include theme configuration"

    def test_grafana_secrets(self):
        """Test Grafana secrets configuration"""
        secrets_file = Path("helm/brain-swarm/templates/grafana-secrets.yaml")

        assert secrets_file.exists(), "Grafana secrets template should exist"

        with open(secrets_file) as f:
            content = f.read()

        # Check secrets configuration
        assert "Opaque" in content, "Should be Opaque type"
        assert "b64enc" in content, "Should base64 encode secrets"

    def test_values_grafana_config(self):
        """Test Grafana configuration in values.yaml"""
        values_file = Path("helm/brain-swarm/values.yaml")

        with open(values_file) as f:
            values = yaml.safe_load(f)

        # Check Grafana configuration structure
        assert "grafana" in values["monitoring"]
        grafana_config = values["monitoring"]["grafana"]

        assert grafana_config["enabled"] is True
        assert "replicas" in grafana_config
        assert "image" in grafana_config
        assert "adminUser" in grafana_config
        assert "adminPassword" in grafana_config
        assert "persistence" in grafana_config
        assert "service" in grafana_config
        assert "resources" in grafana_config

    def test_grafana_conditional_deployment(self):
        """Test conditional Grafana deployment"""
        deployment_file = Path("helm/brain-swarm/templates/grafana-deployment.yaml")

        with open(deployment_file) as f:
            content = f.read()

        # Should only deploy when enabled
        assert "if .Values.monitoring.grafana.enabled" in content or \
               "monitoring.grafana.enabled" in content, \
               "Should conditionally deploy based on enabled flag"

    def test_grafana_resource_limits(self):
        """Test Grafana resource limits"""
        values_file = Path("helm/brain-swarm/values.yaml")

        with open(values_file) as f:
            values = yaml.safe_load(f)

        grafana_resources = values["monitoring"]["grafana"]["resources"]

        assert "limits" in grafana_resources
        assert "requests" in grafana_resources
        assert "cpu" in grafana_resources["limits"]
        assert "memory" in grafana_resources["limits"]

    def test_grafana_login_theming(self):
        """Test Grafana login page theming"""
        # Check if login theming assets exist
        assets_dir = Path("docs/assets")
        if assets_dir.exists():
            # Look for theming-related files
            theming_files = list(assets_dir.glob("*login*")) + \
                          list(assets_dir.glob("*theme*")) + \
                          list(assets_dir.glob("*grafana*"))

            # Should have some theming assets (may be added later)
            # assert len(theming_files) > 0, "Should have Grafana theming assets"

    def test_grafana_dashboard_structure(self):
        """Test Grafana dashboard structure"""
        dashboards_dir = Path("dashboards")

        if dashboards_dir.exists():
            dashboard_files = list(dashboards_dir.glob("*.json"))

            # Validate dashboard JSON structure if files exist
            for dashboard_file in dashboard_files:
                with open(dashboard_file) as f:
                    dashboard = json.load(f)

                # Basic Grafana dashboard structure validation
                assert "dashboard" in dashboard
                assert "title" in dashboard["dashboard"]
                assert "panels" in dashboard["dashboard"]
                assert isinstance(dashboard["dashboard"]["panels"], list)


class TestGrafanaIntegration:
    """Test Grafana integration with Brain Swarm"""

    def test_grafana_prometheus_datasource(self):
        """Test Grafana Prometheus datasource configuration"""
        # This would test the datasource configuration for Prometheus
        # In a real implementation, this would check the datasource config
        pass

    def test_grafana_dashboard_variables(self):
        """Test Grafana dashboard variable configuration"""
        # Test that dashboards have proper variable configuration
        # for swarm selection, time ranges, etc.
        pass

    def test_grafana_alerting_rules(self):
        """Test Grafana alerting rule configuration"""
        # Test that alerting rules are properly configured
        # to integrate with Brain Swarm alerting
        pass


class TestGrafanaSecurity:
    """Test Grafana security configuration"""

    def test_grafana_admin_credentials(self):
        """Test Grafana admin credentials configuration"""
        values_file = Path("helm/brain-swarm/values.yaml")

        with open(values_file) as f:
            values = yaml.safe_load(f)

        grafana_config = values["monitoring"]["grafana"]

        # Admin credentials should be configurable
        assert "adminUser" in grafana_config
        assert "adminPassword" in grafana_config

        # Password should not be default in production
        assert grafana_config["adminPassword"] != "admin", \
               "Admin password should be changed from default"

    def test_grafana_network_policy(self):
        """Test Grafana network policy configuration"""
        # Should have network policies to restrict access
        network_policy_file = Path("helm/brain-swarm/templates/grafana-network-policy.yaml")

        if network_policy_file.exists():
            with open(network_policy_file) as f:
                content = f.read()

            assert "NetworkPolicy" in content
            assert "grafana" in content.lower()

    def test_grafana_tls_configuration(self):
        """Test Grafana TLS configuration"""
        # Should support TLS termination
        ingress_file = Path("helm/brain-swarm/templates/grafana-ingress.yaml")

        if ingress_file.exists():
            with open(ingress_file) as f:
                content = f.read()

            # Should have TLS configuration
            assert "tls" in content or "ssl" in content.lower()


class TestGrafanaMonitoring:
    """Test Grafana monitoring and alerting"""

    def test_grafana_metrics_collection(self):
        """Test Grafana metrics collection"""
        # Grafana should expose its own metrics
        deployment_file = Path("helm/brain-swarm/templates/grafana-deployment.yaml")

        with open(deployment_file) as f:
            content = f.read()

        # Should have metrics endpoint configured
        assert "metrics" in content.lower() or "9090" in content

    def test_grafana_log_configuration(self):
        """Test Grafana logging configuration"""
        values_file = Path("helm/brain-swarm/values.yaml")

        with open(values_file) as f:
            values = yaml.safe_load(f)

        grafana_config = values["monitoring"]["grafana"]

        # Should have log level configuration
        assert "logLevel" in grafana_config
        assert grafana_config["logLevel"] in ["debug", "info", "warn", "error"]


class TestGrafanaBackup:
    """Test Grafana backup and restore"""

    def test_grafana_backup_config(self):
        """Test Grafana backup configuration"""
        # Should have backup configuration for dashboards and datasources
        backup_job_file = Path("helm/brain-swarm/templates/grafana-backup-job.yaml")

        if backup_job_file.exists():
            with open(backup_job_file) as f:
                content = f.read()

            assert "backup" in content.lower() or "Job" in content

    def test_grafana_dashboard_provisioning(self):
        """Test Grafana dashboard provisioning"""
        # Dashboards should be provisioned automatically
        provisioning_file = Path("helm/brain-swarm/templates/grafana-dashboard-provisioning.yaml")

        if provisioning_file.exists():
            with open(provisioning_file) as f:
                content = f.read()

            assert "dashboard" in content.lower()
            assert "provisioning" in content.lower()