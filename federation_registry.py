#!/usr/bin/env python3
"""
Central Registry Service for Brain Swarm Global Discovery

A secure, centralized registry service that enables Brain Swarm instances
on different networks to discover and connect with each other automatically.

Features:
- Secure API key-based authentication
- Swarm registration and discovery
- Health monitoring and status tracking
- Federation metadata management
- Rate limiting and security controls
- RESTful API with JSON responses
"""

import asyncio
import json
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import hashlib
import hmac

from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SwarmRegistration:
    """Swarm registration data."""
    swarm_id: str
    node_name: str
    host: str
    api_port: int
    discovery_port: int
    capabilities: List[str]
    federation_enabled: bool
    api_key_hash: str  # Hashed API key for verification
    registered_at: float
    last_seen: float
    status: str = "active"
    metadata: Dict[str, Any] = None
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_expired(self, timeout: float = 300.0) -> bool:
        """Check if registration has expired."""
        return time.time() - self.last_seen > timeout

    def update_heartbeat(self):
        """Update last seen timestamp."""
        self.last_seen = time.time()


@dataclass
class APIKey:
    """API key data."""
    key_id: str
    key_hash: str
    owner: str
    created_at: float
    last_used: float
    permissions: List[str]
    rate_limit: int = 100  # requests per minute
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FederationRegistry:
    """Central registry for swarm discovery and management."""

    def __init__(self):
        self.registered_swarms: Dict[str, SwarmRegistration] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self.request_counts: Dict[str, List[float]] = {}  # API key -> timestamps

        # Create default admin API key
        self._create_admin_key()

    def _create_admin_key(self):
        """Create default admin API key."""
        admin_key = secrets.token_urlsafe(32)
        key_hash = self._hash_api_key(admin_key)
        admin_api_key = APIKey(
            key_id="admin-key",
            key_hash=key_hash,
            owner="system",
            created_at=time.time(),
            last_used=time.time(),
            permissions=["read", "write", "admin"],
            rate_limit=1000,
            active=True
        )
        self.api_keys["admin-key"] = admin_api_key

        # Log the admin key (in production, this should be stored securely)
        logger.warning(f"DEFAULT ADMIN API KEY: {admin_key}")
        logger.warning("Store this key securely and delete this log entry!")

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _verify_api_key(self, provided_key: str) -> Optional[APIKey]:
        """Verify API key and return key data."""
        key_hash = self._hash_api_key(provided_key)

        for api_key in self.api_keys.values():
            if api_key.key_hash == key_hash and api_key.active:
                api_key.last_used = time.time()
                return api_key

        return None

    def _check_rate_limit(self, api_key: APIKey) -> bool:
        """Check if API key is within rate limits."""
        now = time.time()
        key_id = api_key.key_id

        if key_id not in self.request_counts:
            self.request_counts[key_id] = []

        # Clean old requests (older than 1 minute)
        self.request_counts[key_id] = [
            ts for ts in self.request_counts[key_id]
            if now - ts < 60
        ]

        # Check rate limit
        if len(self.request_counts[key_id]) >= api_key.rate_limit:
            return False

        # Add current request
        self.request_counts[key_id].append(now)
        return True

    def register_swarm(self, swarm_data: Dict[str, Any], api_key: APIKey) -> SwarmRegistration:
        """Register or update a swarm."""
        swarm_id = swarm_data["swarm_id"]

        # Check permissions
        if "write" not in api_key.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        # Create or update registration
        if swarm_id in self.registered_swarms:
            # Update existing
            registration = self.registered_swarms[swarm_id]
            registration.node_name = swarm_data["node_name"]
            registration.host = swarm_data["host"]
            registration.api_port = swarm_data["api_port"]
            registration.discovery_port = swarm_data["discovery_port"]
            registration.capabilities = swarm_data["capabilities"]
            registration.federation_enabled = swarm_data["federation_enabled"]
            registration.metadata = swarm_data.get("metadata", {})
            registration.version = swarm_data.get("version", "1.0.0")
            registration.update_heartbeat()
        else:
            # Create new registration
            registration = SwarmRegistration(
                swarm_id=swarm_id,
                node_name=swarm_data["node_name"],
                host=swarm_data["host"],
                api_port=swarm_data["api_port"],
                discovery_port=swarm_data["discovery_port"],
                capabilities=swarm_data["capabilities"],
                federation_enabled=swarm_data["federation_enabled"],
                api_key_hash=api_key.key_hash,
                registered_at=time.time(),
                last_seen=time.time(),
                metadata=swarm_data.get("metadata", {}),
                version=swarm_data.get("version", "1.0.0")
            )
            self.registered_swarms[swarm_id] = registration

        logger.info(f"Registered swarm: {swarm_id} from {registration.host}")
        return registration

    def unregister_swarm(self, swarm_id: str, api_key: APIKey) -> bool:
        """Unregister a swarm."""
        if swarm_id not in self.registered_swarms:
            return False

        registration = self.registered_swarms[swarm_id]

        # Check ownership or admin permissions
        if (registration.api_key_hash != api_key.key_hash and
            "admin" not in api_key.permissions):
            raise HTTPException(status_code=403, detail="Not authorized to unregister this swarm")

        del self.registered_swarms[swarm_id]
        logger.info(f"Unregistered swarm: {swarm_id}")
        return True

    def get_swarm(self, swarm_id: str, api_key: APIKey) -> Optional[SwarmRegistration]:
        """Get a specific swarm registration."""
        if "read" not in api_key.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return self.registered_swarms.get(swarm_id)

    def list_swarms(self, api_key: APIKey, filters: Optional[Dict[str, Any]] = None) -> List[SwarmRegistration]:
        """List registered swarms with optional filtering."""
        if "read" not in api_key.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        swarms = list(self.registered_swarms.values())

        # Apply filters
        if filters:
            if "capability" in filters:
                swarms = [s for s in swarms if filters["capability"] in s.capabilities]
            if "federation_enabled" in filters:
                swarms = [s for s in swarms if s.federation_enabled == filters["federation_enabled"]]
            if "status" in filters:
                swarms = [s for s in swarms if s.status == filters["status"]]

        return swarms

    def heartbeat(self, swarm_id: str, api_key: APIKey) -> bool:
        """Update swarm heartbeat."""
        if swarm_id not in self.registered_swarms:
            return False

        registration = self.registered_swarms[swarm_id]

        # Check ownership
        if registration.api_key_hash != api_key.key_hash:
            raise HTTPException(status_code=403, detail="Not authorized for this swarm")

        registration.update_heartbeat()
        return True

    def cleanup_expired(self, timeout: float = 300.0):
        """Clean up expired swarm registrations."""
        expired = []
        for swarm_id, registration in self.registered_swarms.items():
            if registration.is_expired(timeout):
                expired.append(swarm_id)

        for swarm_id in expired:
            del self.registered_swarms[swarm_id]
            logger.info(f"Cleaned up expired swarm: {swarm_id}")

        return len(expired)

    def create_api_key(self, owner: str, permissions: List[str], rate_limit: int = 100) -> str:
        """Create a new API key."""
        key_id = f"key_{secrets.token_hex(8)}"
        api_key = secrets.token_urlsafe(32)
        key_hash = self._hash_api_key(api_key)

        api_key_obj = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            owner=owner,
            created_at=time.time(),
            last_used=time.time(),
            permissions=permissions,
            rate_limit=rate_limit,
            active=True
        )

        self.api_keys[key_id] = api_key_obj
        logger.info(f"Created API key for {owner}: {key_id}")
        return api_key

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if key_id in self.api_keys:
            self.api_keys[key_id].active = False
            logger.info(f"Revoked API key: {key_id}")
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total_swarms = len(self.registered_swarms)
        active_swarms = len([s for s in self.registered_swarms.values() if s.status == "active"])
        total_keys = len(self.api_keys)
        active_keys = len([k for k in self.api_keys.values() if k.active])

        return {
            "total_swarms": total_swarms,
            "active_swarms": active_swarms,
            "total_api_keys": total_keys,
            "active_api_keys": active_keys,
            "uptime": time.time() - getattr(self, '_start_time', time.time()),
            "version": "1.0.0"
        }


# Global registry instance
registry = FederationRegistry()
registry._start_time = time.time()

# FastAPI app
app = FastAPI(
    title="Brain Swarm Federation Registry",
    description="Central registry service for global Brain Swarm discovery",
    version="1.0.0"
)

# Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class SwarmRegistrationRequest(BaseModel):
    swarm_id: str = Field(..., description="Unique swarm identifier")
    node_name: str = Field(..., description="Human-readable node name")
    host: str = Field(..., description="Host address or IP")
    api_port: int = Field(..., description="API port for WebSocket connections")
    discovery_port: int = Field(..., description="Discovery port (UDP)")
    capabilities: List[str] = Field(default_factory=list, description="Swarm capabilities")
    federation_enabled: bool = Field(True, description="Federation participation enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    version: str = Field("1.0.0", description="Swarm version")

class APIKeyCreateRequest(BaseModel):
    owner: str = Field(..., description="Key owner identifier")
    permissions: List[str] = Field(..., description="Key permissions")
    rate_limit: int = Field(100, description="Rate limit (requests per minute)")

# Dependencies
async def get_api_key(request: Request, api_key: str = Security(api_key_header)) -> APIKey:
    """Dependency to get and validate API key."""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    key_data = registry._verify_api_key(api_key)
    if not key_data:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check rate limit
    if not registry._check_rate_limit(key_data):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return key_data

# Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Brain Swarm Federation Registry", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/stats")
async def get_registry_stats(api_key: APIKey = Depends(get_api_key)):
    """Get registry statistics."""
    if "admin" not in api_key.permissions:
        raise HTTPException(status_code=403, detail="Admin access required")

    return registry.get_stats()

@app.post("/swarms")
async def register_swarm(
    registration: SwarmRegistrationRequest,
    api_key: APIKey = Depends(get_api_key)
):
    """Register or update a swarm."""
    try:
        swarm_reg = registry.register_swarm(registration.dict(), api_key)
        return {
            "status": "registered",
            "swarm_id": swarm_reg.swarm_id,
            "registered_at": swarm_reg.registered_at
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/swarms/{swarm_id}")
async def unregister_swarm(
    swarm_id: str,
    api_key: APIKey = Depends(get_api_key)
):
    """Unregister a swarm."""
    success = registry.unregister_swarm(swarm_id, api_key)
    if not success:
        raise HTTPException(status_code=404, detail="Swarm not found")

    return {"status": "unregistered", "swarm_id": swarm_id}

@app.get("/swarms/{swarm_id}")
async def get_swarm(
    swarm_id: str,
    api_key: APIKey = Depends(get_api_key)
):
    """Get a specific swarm."""
    swarm = registry.get_swarm(swarm_id, api_key)
    if not swarm:
        raise HTTPException(status_code=404, detail="Swarm not found")

    return swarm.to_dict()

@app.get("/swarms")
async def list_swarms(
    capability: Optional[str] = None,
    federation_enabled: Optional[bool] = None,
    status: Optional[str] = None,
    api_key: APIKey = Depends(get_api_key)
):
    """List registered swarms with optional filtering."""
    filters = {}
    if capability:
        filters["capability"] = capability
    if federation_enabled is not None:
        filters["federation_enabled"] = federation_enabled
    if status:
        filters["status"] = status

    swarms = registry.list_swarms(api_key, filters)
    return {"swarms": [s.to_dict() for s in swarms], "count": len(swarms)}

@app.post("/swarms/{swarm_id}/heartbeat")
async def swarm_heartbeat(
    swarm_id: str,
    api_key: APIKey = Depends(get_api_key)
):
    """Update swarm heartbeat."""
    success = registry.heartbeat(swarm_id, api_key)
    if not success:
        raise HTTPException(status_code=404, detail="Swarm not found")

    return {"status": "heartbeat_updated", "timestamp": time.time()}

@app.post("/keys")
async def create_api_key(
    key_request: APIKeyCreateRequest,
    api_key: APIKey = Depends(get_api_key)
):
    """Create a new API key."""
    if "admin" not in api_key.permissions:
        raise HTTPException(status_code=403, detail="Admin access required")

    new_key = registry.create_api_key(
        key_request.owner,
        key_request.permissions,
        key_request.rate_limit
    )

    return {
        "status": "created",
        "api_key": new_key,
        "key_id": f"key_{secrets.token_hex(8)}",  # This is approximate
        "owner": key_request.owner
    }

@app.delete("/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    api_key: APIKey = Depends(get_api_key)
):
    """Revoke an API key."""
    if "admin" not in api_key.permissions:
        raise HTTPException(status_code=403, detail="Admin access required")

    success = registry.revoke_api_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"status": "revoked", "key_id": key_id}

@app.post("/cleanup")
async def cleanup_expired(
    timeout: float = 300.0,
    api_key: APIKey = Depends(get_api_key)
):
    """Clean up expired swarm registrations."""
    if "admin" not in api_key.permissions:
        raise HTTPException(status_code=403, detail="Admin access required")

    cleaned = registry.cleanup_expired(timeout)
    return {"status": "cleanup_completed", "cleaned_count": cleaned}

# Background task for periodic cleanup
@app.on_event("startup")
async def startup_event():
    """Initialize registry on startup."""
    logger.info("Federation Registry starting up")

    # Start periodic cleanup task
    asyncio.create_task(periodic_cleanup())

async def periodic_cleanup():
    """Periodic cleanup of expired registrations."""
    while True:
        await asyncio.sleep(60)  # Clean up every minute
        try:
            cleaned = registry.cleanup_expired()
            if cleaned > 0:
                logger.info(f"Periodic cleanup: removed {cleaned} expired swarms")
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

if __name__ == "__main__":
    # Run with uvicorn for development
    uvicorn.run(
        "brain_swarm.federation_registry:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )