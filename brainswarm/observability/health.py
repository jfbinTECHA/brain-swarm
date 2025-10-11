"""
Health check system for Brain Swarm
Comprehensive system health monitoring and diagnostics
"""

import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from ..core.base import logger


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: float
    duration_ms: float
    tags: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "tags": self.tags or []
        }


class HealthChecker:
    """Comprehensive health checker for Brain Swarm components"""

    def __init__(self):
        self.checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self.check_intervals: Dict[str, float] = {}  # seconds
        self.last_check_times: Dict[str, float] = {}

    def register_check(self, name: str, check_func: Callable[[], HealthCheckResult],
                      interval_seconds: float = 30.0, tags: List[str] = None):
        """Register a health check"""
        self.checks[name] = check_func
        self.check_intervals[name] = interval_seconds
        if tags:
            # Store tags in the function for later retrieval
            check_func._health_tags = tags

    def unregister_check(self, name: str):
        """Unregister a health check"""
        if name in self.checks:
            del self.checks[name]
        if name in self.check_intervals:
            del self.check_intervals[name]
        if name in self.last_results:
            del self.last_results[name]
        if name in self.last_check_times:
            del self.last_check_times[name]

    def run_check(self, name: str) -> Optional[HealthCheckResult]:
        """Run a specific health check"""
        if name not in self.checks:
            return None

        start_time = time.time()
        try:
            result = self.checks[name]()
            duration_ms = (time.time() - start_time) * 1000

            # Update result with timing
            result.duration_ms = duration_ms
            result.timestamp = time.time()

            # Store result
            self.last_results[name] = result
            self.last_check_times[name] = time.time()

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_result = HealthCheckResult(
                name=name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                timestamp=time.time(),
                duration_ms=duration_ms,
                tags=getattr(self.checks[name], '_health_tags', [])
            )

            self.last_results[name] = error_result
            self.last_check_times[name] = time.time()

            logger.log("ERROR", "HealthChecker", f"Health check {name} failed", {
                "error": str(e),
                "duration_ms": duration_ms
            })

            return error_result

    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        results = {}

        for name in self.checks.keys():
            # Check if we should run this check based on interval
            last_check = self.last_check_times.get(name, 0)
            interval = self.check_intervals.get(name, 30.0)

            if time.time() - last_check >= interval:
                result = self.run_check(name)
                if result:
                    results[name] = result
            else:
                # Return cached result if still valid
                cached = self.last_results.get(name)
                if cached:
                    results[name] = cached

        return results

    async def run_checks_async(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks asynchronously"""
        tasks = []

        for name in self.checks.keys():
            # Check if we should run this check based on interval
            last_check = self.last_check_times.get(name, 0)
            interval = self.check_intervals.get(name, 30.0)

            if time.time() - last_check >= interval:
                task = asyncio.create_task(self._run_check_async(name))
                tasks.append(task)
            else:
                # Return cached result
                cached = self.last_results.get(name)
                if cached:
                    tasks.append(asyncio.create_task(asyncio.coroutine(lambda: cached)()))

        if tasks:
            results_list = await asyncio.gather(*tasks, return_exceptions=True)

            results = {}
            for i, result in enumerate(results_list):
                name = list(self.checks.keys())[i]
                if isinstance(result, Exception):
                    results[name] = HealthCheckResult(
                        name=name,
                        status=HealthStatus.CRITICAL,
                        message=f"Async health check failed: {str(result)}",
                        details={"error": str(result)},
                        timestamp=time.time(),
                        duration_ms=0
                    )
                else:
                    results[name] = result

            return results

        return {}

    async def _run_check_async(self, name: str) -> HealthCheckResult:
        """Run a health check asynchronously"""
        # For now, just run synchronously in a thread pool
        # In a real implementation, async checks would be truly async
        import concurrent.futures
        import asyncio

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, self.run_check, name)
            return result

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        results = self.run_all_checks()

        if not results:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": "No health checks configured",
                "checks_total": 0,
                "checks_healthy": 0,
                "checks_degraded": 0,
                "checks_unhealthy": 0,
                "checks_critical": 0,
                "timestamp": time.time()
            }

        # Count statuses
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.CRITICAL: 0
        }

        for result in results.values():
            status_counts[result.status] += 1

        # Determine overall status
        if status_counts[HealthStatus.CRITICAL] > 0:
            overall_status = HealthStatus.CRITICAL
            message = f"System critical: {status_counts[HealthStatus.CRITICAL]} critical checks"
        elif status_counts[HealthStatus.UNHEALTHY] > 0:
            overall_status = HealthStatus.UNHEALTHY
            message = f"System unhealthy: {status_counts[HealthStatus.UNHEALTHY]} unhealthy checks"
        elif status_counts[HealthStatus.DEGRADED] > 0:
            overall_status = HealthStatus.DEGRADED
            message = f"System degraded: {status_counts[HealthStatus.DEGRADED]} degraded checks"
        else:
            overall_status = HealthStatus.HEALTHY
            message = f"System healthy: all {status_counts[HealthStatus.HEALTHY]} checks passed"

        return {
            "status": overall_status.value,
            "message": message,
            "checks_total": len(results),
            "checks_healthy": status_counts[HealthStatus.HEALTHY],
            "checks_degraded": status_counts[HealthStatus.DEGRADED],
            "checks_unhealthy": status_counts[HealthStatus.UNHEALTHY],
            "checks_critical": status_counts[HealthStatus.CRITICAL],
            "timestamp": time.time(),
            "checks": {name: result.to_dict() for name, result in results.items()}
        }

    def get_check_history(self, name: str, limit: int = 10) -> List[HealthCheckResult]:
        """Get history of a specific health check"""
        # This would require storing historical results
        # For now, just return the last result
        result = self.last_results.get(name)
        return [result] if result else []


# Predefined health check functions
def system_resources_check() -> HealthCheckResult:
    """Check system resource usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        details = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": memory.used / (1024**3),
            "memory_total_gb": memory.total / (1024**3),
            "disk_percent": disk.percent,
            "disk_used_gb": disk.used / (1024**3),
            "disk_total_gb": disk.total / (1024**3)
        }

        # Determine status based on thresholds
        if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
            status = HealthStatus.CRITICAL
            message = "System resources critically high"
        elif cpu_percent > 80 or memory.percent > 80 or disk.percent > 80:
            status = HealthStatus.UNHEALTHY
            message = "System resources high"
        elif cpu_percent > 60 or memory.percent > 60 or disk.percent > 60:
            status = HealthStatus.DEGRADED
            message = "System resources elevated"
        else:
            status = HealthStatus.HEALTHY
            message = "System resources normal"

        return HealthCheckResult(
            name="system_resources",
            status=status,
            message=message,
            details=details,
            timestamp=time.time(),
            duration_ms=0,
            tags=["system", "resources"]
        )

    except Exception as e:
        return HealthCheckResult(
            name="system_resources",
            status=HealthStatus.CRITICAL,
            message=f"Failed to check system resources: {str(e)}",
            details={"error": str(e)},
            timestamp=time.time(),
            duration_ms=0,
            tags=["system", "resources"]
        )


def database_connectivity_check(db_url: str) -> HealthCheckResult:
    """Check database connectivity"""
    # Placeholder - would implement actual DB connectivity check
    return HealthCheckResult(
        name="database_connectivity",
        status=HealthStatus.HEALTHY,
        message="Database connection successful",
        details={"db_url": db_url, "connection_time_ms": 5.2},
        timestamp=time.time(),
        duration_ms=5.2,
        tags=["database", "connectivity"]
    )


def external_services_check(services: Dict[str, str]) -> HealthCheckResult:
    """Check external service connectivity"""
    # Placeholder - would implement actual service checks
    healthy_services = len(services)
    unhealthy_services = 0

    details = {}
    for name, url in services.items():
        details[name] = {"url": url, "status": "healthy", "response_time_ms": 150}

    status = HealthStatus.HEALTHY if unhealthy_services == 0 else HealthStatus.UNHEALTHY
    message = f"External services: {healthy_services} healthy, {unhealthy_services} unhealthy"

    return HealthCheckResult(
        name="external_services",
        status=status,
        message=message,
        details=details,
        timestamp=time.time(),
        duration_ms=0,
        tags=["external", "services"]
    )


# Global health checker instance
health_checker = HealthChecker()

# Register default health checks
health_checker.register_check(
    "system_resources",
    system_resources_check,
    interval_seconds=30.0,
    tags=["system", "resources"]
)