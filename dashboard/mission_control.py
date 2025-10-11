"""
Mission Control Dashboard for Brain Swarm
Real-time incident monitoring and AI triage visualization
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ..observability.metrics import prometheus_metrics
from ..cortex.incident_broadcast import broadcast_to_kilo
from ..schemas.incident import IncidentStatus, IncidentResponse
from ..config import settings


class MissionControlDashboard:
    """Real-time incident monitoring dashboard"""

    def __init__(self):
        self.active_incidents: Dict[str, IncidentStatus] = {}
        self.ai_responses: Dict[str, List[IncidentResponse]] = {}
        self.websocket_clients: List[WebSocket] = []

    async def add_incident(self, incident_data: Dict[str, Any]) -> str:
        """Add new incident to mission control"""
        incident_id = incident_data.get("id", f"incident_{int(datetime.now().timestamp())}")

        incident = IncidentStatus(
            incident_id=incident_id,
            status="active",
            alerts=incident_data.get("alerts", []),
            tickets=[],
            ai_responses=[],
            last_updated=datetime.now().timestamp(),
            resolution_time=None
        )

        self.active_incidents[incident_id] = incident
        self.ai_responses[incident_id] = []

        # Broadcast to all connected clients
        await self._broadcast_update({
            "type": "incident_added",
            "incident": incident.dict()
        })

        return incident_id

    async def update_incident_status(self, incident_id: str, status: str, resolution_time: Optional[float] = None):
        """Update incident status"""
        if incident_id in self.active_incidents:
            self.active_incidents[incident_id].status = status
            self.active_incidents[incident_id].last_updated = datetime.now().timestamp()
            if resolution_time:
                self.active_incidents[incident_id].resolution_time = resolution_time

            await self._broadcast_update({
                "type": "incident_updated",
                "incident_id": incident_id,
                "status": status,
                "resolution_time": resolution_time
            })

    async def add_ai_response(self, incident_id: str, response: IncidentResponse):
        """Add AI triage response"""
        if incident_id not in self.ai_responses:
            self.ai_responses[incident_id] = []

        self.ai_responses[incident_id].append(response)

        await self._broadcast_update({
            "type": "ai_response_added",
            "incident_id": incident_id,
            "response": response.dict()
        })

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        active_count = len([i for i in self.active_incidents.values() if i.status == "active"])
        resolved_count = len([i for i in self.active_incidents.values() if i.status == "resolved"])

        # Calculate metrics
        avg_resolution_time = 0
        resolved_incidents = [i for i in self.active_incidents.values() if i.resolution_time]
        if resolved_incidents:
            avg_resolution_time = sum(i.resolution_time for i in resolved_incidents) / len(resolved_incidents)

        # Severity breakdown
        severity_counts = {"critical": 0, "warning": 0, "info": 0}
        for incident in self.active_incidents.values():
            if incident.alerts:
                severity = incident.alerts[0].get("labels", {}).get("severity", "info")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "timestamp": datetime.now().timestamp(),
            "active_incidents": active_count,
            "resolved_incidents": resolved_count,
            "total_incidents": len(self.active_incidents),
            "avg_resolution_time": avg_resolution_time,
            "severity_breakdown": severity_counts,
            "recent_incidents": [
                {
                    "id": incident.incident_id,
                    "status": incident.status,
                    "severity": incident.alerts[0].get("labels", {}).get("severity", "unknown") if incident.alerts else "unknown",
                    "source": incident.alerts[0].get("labels", {}).get("source", "unknown") if incident.alerts else "unknown",
                    "last_updated": incident.last_updated,
                    "resolution_time": incident.resolution_time,
                    "ai_responses_count": len(self.ai_responses.get(incident.incident_id, []))
                }
                for incident in list(self.active_incidents.values())[-10:]  # Last 10 incidents
            ]
        }

    async def websocket_endpoint(self, websocket: WebSocket):
        """WebSocket endpoint for real-time updates"""
        await websocket.accept()
        self.websocket_clients.append(websocket)

        try:
            # Send initial data
            dashboard_data = await self.get_dashboard_data()
            await websocket.send_json({
                "type": "dashboard_init",
                "data": dashboard_data
            })

            # Keep connection alive
            while True:
                # Could handle client messages here
                data = await websocket.receive_text()
                # Process any client commands if needed

        except WebSocketDisconnect:
            if websocket in self.websocket_clients:
                self.websocket_clients.remove(websocket)

    async def _broadcast_update(self, update_data: Dict[str, Any]):
        """Broadcast update to all connected clients"""
        disconnected_clients = []

        for client in self.websocket_clients:
            try:
                await client.send_json(update_data)
            except Exception:
                disconnected_clients.append(client)

        # Clean up disconnected clients
        for client in disconnected_clients:
            if client in self.websocket_clients:
                self.websocket_clients.remove(client)


# Global instance
mission_control = MissionControlDashboard()


async def get_mission_control_dashboard() -> Dict[str, Any]:
    """Get mission control dashboard data"""
    return await mission_control.get_dashboard_data()


def create_mission_control_html() -> str:
    """Create HTML for Mission Control dashboard"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Brain Swarm - Mission Control</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
            .metric { font-size: 2em; font-weight: bold; color: #007bff; }
            .incident-list { max-height: 400px; overflow-y: auto; }
            .incident-item { padding: 10px; margin: 5px 0; border-left: 4px solid; }
            .severity-critical { border-left-color: #dc3545; }
            .severity-warning { border-left-color: #ffc107; }
            .severity-info { border-left-color: #17a2b8; }
            .status-active { background-color: #fff3cd; }
            .status-resolved { background-color: #d4edda; }
        </style>
    </head>
    <body>
        <h1>🛰️ Brain Swarm Mission Control</h1>

        <div class="dashboard">
            <div class="card">
                <h3>Active Incidents</h3>
                <div class="metric" id="active-count">0</div>
            </div>

            <div class="card">
                <h3>Resolved Today</h3>
                <div class="metric" id="resolved-count">0</div>
            </div>

            <div class="card">
                <h3>Avg Resolution Time</h3>
                <div class="metric" id="avg-resolution">0s</div>
            </div>

            <div class="card">
                <h3>Severity Breakdown</h3>
                <canvas id="severityChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h3>Recent Incidents</h3>
            <div id="incident-list" class="incident-list">
                <!-- Incidents will be populated here -->
            </div>
        </div>

        <script>
            let ws;
            let severityChart;

            function initWebSocket() {
                ws = new WebSocket('ws://' + window.location.host + '/ws/mission-control');

                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    updateDashboard(data);
                };

                ws.onclose = function() {
                    setTimeout(initWebSocket, 1000);
                };
            }

            function updateDashboard(data) {
                if (data.type === 'dashboard_init') {
                    updateMetrics(data.data);
                    updateIncidentList(data.data.recent_incidents);
                    updateSeverityChart(data.data.severity_breakdown);
                } else if (data.type === 'incident_added' || data.type === 'incident_updated') {
                    // Refresh dashboard data
                    fetch('/api/mission-control')
                        .then(r => r.json())
                        .then(data => {
                            updateMetrics(data);
                            updateIncidentList(data.recent_incidents);
                            updateSeverityChart(data.severity_breakdown);
                        });
                }
            }

            function updateMetrics(data) {
                document.getElementById('active-count').textContent = data.active_incidents;
                document.getElementById('resolved-count').textContent = data.resolved_incidents;
                document.getElementById('avg-resolution').textContent = Math.round(data.avg_resolution_time) + 's';
            }

            function updateIncidentList(incidents) {
                const list = document.getElementById('incident-list');
                list.innerHTML = incidents.map(incident => `
                    <div class="incident-item severity-${incident.severity} status-${incident.status}">
                        <strong>${incident.id}</strong> - ${incident.severity.toUpperCase()}
                        <br>Source: ${incident.source}
                        <br>Status: ${incident.status}
                        <br>AI Responses: ${incident.ai_responses_count}
                        ${incident.resolution_time ? `<br>Resolution: ${Math.round(incident.resolution_time)}s` : ''}
                    </div>
                `).join('');
            }

            function updateSeverityChart(severityData) {
                if (severityChart) {
                    severityChart.destroy();
                }

                const ctx = document.getElementById('severityChart').getContext('2d');
                severityChart = new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: ['Critical', 'Warning', 'Info'],
                        datasets: [{
                            data: [severityData.critical, severityData.warning, severityData.info],
                            backgroundColor: ['#dc3545', '#ffc107', '#17a2b8']
                        }]
                    }
                });
            }

            // Initialize
            initWebSocket();
        </script>
    </body>
    </html>
    """
    return html