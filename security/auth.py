"""
Authentication and authorization utilities for Brain Swarm
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import hashlib
from enum import Enum

from config import settings
from core.base import logger


class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    OPERATOR = "operator"
    AGENT = "agent"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Permissions for operations"""
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    AGENT_REGISTER = "agent:register"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    METRICS_READ = "metrics:read"
    DASHBOARD_READ = "dashboard:read"
    SYSTEM_ADMIN = "system:admin"


# Role-based permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.TASK_CREATE, Permission.TASK_READ, Permission.TASK_UPDATE, Permission.TASK_DELETE,
        Permission.AGENT_REGISTER, Permission.AGENT_READ, Permission.AGENT_UPDATE,
        Permission.METRICS_READ, Permission.DASHBOARD_READ, Permission.SYSTEM_ADMIN
    ],
    UserRole.OPERATOR: [
        Permission.TASK_CREATE, Permission.TASK_READ, Permission.TASK_UPDATE,
        Permission.AGENT_REGISTER, Permission.AGENT_READ, Permission.AGENT_UPDATE,
        Permission.METRICS_READ, Permission.DASHBOARD_READ
    ],
    UserRole.AGENT: [
        Permission.TASK_READ, Permission.AGENT_READ
    ],
    UserRole.VIEWER: [
        Permission.TASK_READ, Permission.AGENT_READ, Permission.METRICS_READ, Permission.DASHBOARD_READ
    ]
}


class SecurityAuditLogger:
    """Security audit logging for authentication and authorization events"""

    @staticmethod
    def log_auth_event(event_type: str, user_id: str, details: Dict[str, Any], success: bool = True):
        """Log authentication/authorization events"""
        log_data = {
            "event_type": event_type,
            "user_id": user_id,
            "success": success,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": details.get("ip_address"),
            "user_agent": details.get("user_agent")
        }

        level = "INFO" if success else "WARNING"
        logger.log(level, "SecurityAudit", f"Auth event: {event_type} for {user_id}", log_data)

    @staticmethod
    def log_token_event(event_type: str, token_id: str, user_id: str, details: Dict[str, Any]):
        """Log token-related events"""
        log_data = {
            "event_type": event_type,
            "token_id": token_id,
            "user_id": user_id,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.log("INFO", "SecurityAudit", f"Token event: {event_type} for {user_id}", log_data)


security = HTTPBearer()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with enhanced security"""
    to_encode = data.copy()

    # Add token metadata
    token_id = secrets.token_hex(16)
    issued_at = datetime.utcnow()
    to_encode.update({
        "jti": token_id,  # JWT ID for token tracking
        "iat": issued_at,  # Issued at
        "iss": "brain-swarm",  # Issuer
        "aud": "brain-swarm-api"  # Audience
    })

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.security.jwt_expiration_hours)

    to_encode.update({"exp": expire})

    # Create token with enhanced algorithm
    encoded_jwt = jwt.encode(to_encode, settings.security.jwt_secret, algorithm=settings.security.jwt_algorithm)

    # Log token creation
    SecurityAuditLogger.log_token_event(
        "token_created",
        token_id,
        data.get("sub", "unknown"),
        {"expires_at": expire.isoformat(), "role": data.get("role", "unknown")}
    )

    return encoded_jwt


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token"""
    token_id = secrets.token_hex(16)
    expire = datetime.utcnow() + timedelta(days=30)  # 30 days for refresh tokens

    to_encode = {
        "sub": user_id,
        "jti": token_id,
        "iat": datetime.utcnow(),
        "exp": expire,
        "type": "refresh",
        "iss": "brain-swarm",
        "aud": "brain-swarm-api"
    }

    encoded_jwt = jwt.encode(to_encode, settings.security.jwt_secret, algorithm=settings.security.jwt_algorithm)

    SecurityAuditLogger.log_token_event(
        "refresh_token_created",
        token_id,
        user_id,
        {"expires_at": expire.isoformat()}
    )

    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Verify JWT token with enhanced validation"""
    try:
        # Decode without verification first to check token type
        header = jwt.get_unverified_header(token)
        if header.get("alg") != settings.security.jwt_algorithm:
            SecurityAuditLogger.log_auth_event("token_verification_failed", "unknown", {"reason": "invalid_algorithm"})
            return None

        # Verify the token
        payload = jwt.decode(
            token,
            settings.security.jwt_secret,
            algorithms=[settings.security.jwt_algorithm],
            audience="brain-swarm-api",
            issuer="brain-swarm"
        )

        # Check token type
        if payload.get("type") != token_type:
            SecurityAuditLogger.log_auth_event("token_verification_failed", payload.get("sub", "unknown"),
                                             {"reason": "wrong_token_type", "expected": token_type, "got": payload.get("type")})
            return None

        # Log successful verification
        SecurityAuditLogger.log_auth_event("token_verified", payload.get("sub", "unknown"),
                                         {"token_type": token_type, "jti": payload.get("jti")})

        return payload

    except jwt.ExpiredSignatureError:
        SecurityAuditLogger.log_auth_event("token_expired", "unknown", {"token_type": token_type})
        return None
    except jwt.InvalidAudienceError:
        SecurityAuditLogger.log_auth_event("token_verification_failed", "unknown", {"reason": "invalid_audience"})
        return None
    except jwt.InvalidIssuerError:
        SecurityAuditLogger.log_auth_event("token_verification_failed", "unknown", {"reason": "invalid_issuer"})
        return None
    except jwt.JWTError as e:
        SecurityAuditLogger.log_auth_event("token_verification_failed", "unknown", {"reason": str(e)})
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token with enhanced validation"""
    token = credentials.credentials
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def get_current_user_with_permissions(required_permissions: List[Permission] = None) -> Dict[str, Any]:
    """Get current user and check permissions"""
    def dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        token = credentials.credentials
        payload = verify_token(token, "access")
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # Check permissions if required
        if required_permissions:
            user_role = UserRole(payload.get("role", "viewer"))
            user_permissions = ROLE_PERMISSIONS.get(user_role, [])

            missing_permissions = []
            for permission in required_permissions:
                if permission not in user_permissions:
                    missing_permissions.append(permission.value)

            if missing_permissions:
                SecurityAuditLogger.log_auth_event(
                    "permission_denied",
                    payload.get("sub", "unknown"),
                    {"missing_permissions": missing_permissions, "required": [p.value for p in required_permissions]}
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Missing: {', '.join(missing_permissions)}"
                )

        return payload

    return dependency


def check_permission(user: Dict[str, Any], permission: Permission) -> bool:
    """Check if user has a specific permission"""
    user_role = UserRole(user.get("role", "viewer"))
    user_permissions = ROLE_PERMISSIONS.get(user_role, [])
    return permission in user_permissions


def require_role(required_role: UserRole):
    """Dependency to require a specific role"""
    def dependency(user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = UserRole(user.get("role", "viewer"))
        if user_role != required_role:
            SecurityAuditLogger.log_auth_event(
                "role_denied",
                user.get("sub", "unknown"),
                {"required_role": required_role.value, "user_role": user_role.value}
            )
            raise HTTPException(
                status_code=403,
                detail=f"Role {required_role.value} required, but user has {user_role.value}"
            )
        return user
    return dependency


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """Refresh an access token using a refresh token"""
    payload = verify_token(refresh_token, "refresh")
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    # Create new access token
    new_access_token = create_access_token({
        "sub": user_id,
        "role": payload.get("role", "viewer"),
        "agent_name": payload.get("agent_name")
    })

    SecurityAuditLogger.log_auth_event(
        "token_refreshed",
        user_id,
        {"old_token_id": payload.get("jti")}
    )

    return new_access_token


def verify_api_key(api_key: str) -> bool:
    """Verify API key for agent registration"""
    return api_key in settings.security.api_keys.values()


def generate_api_key() -> str:
    """Generate a new API key"""
    return secrets.token_url_safe(32)


def authenticate_agent(api_key: str, agent_id: str, role: UserRole = UserRole.AGENT) -> Optional[Dict[str, str]]:
    """Authenticate agent and return JWT tokens if valid"""
    if verify_api_key(api_key):
        # Find the agent name from api_keys
        agent_name = None
        for name, key in settings.security.api_keys.items():
            if key == api_key:
                agent_name = name
                break

        if agent_name:
            # Determine role based on agent type or configuration
            user_role = role
            if agent_name.lower() in ["admin", "coordinator"]:
                user_role = UserRole.ADMIN
            elif agent_name.lower() in ["operator", "supervisor"]:
                user_role = UserRole.OPERATOR

            # Create access token
            access_token = create_access_token({
                "sub": agent_id,
                "agent_name": agent_name,
                "role": user_role.value,
                "type": "access"
            })

            # Create refresh token
            refresh_token = create_refresh_token(agent_id)

            SecurityAuditLogger.log_auth_event(
                "agent_authenticated",
                agent_id,
                {"agent_name": agent_name, "role": user_role.value, "method": "api_key"}
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "role": user_role.value
            }
    return None


def authenticate_user(username: str, password: str) -> Optional[Dict[str, str]]:
    """Authenticate human user with username/password"""
    # Hash password for comparison (in production, use proper password hashing)
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    # Check against configured users (in production, use proper user store)
    users = getattr(settings.security, 'users', {})
    if username in users:
        stored_hash = users[username].get('password_hash')
        if stored_hash == password_hash:
            user_role = UserRole(users[username].get('role', 'viewer'))

            access_token = create_access_token({
                "sub": username,
                "role": user_role.value,
                "type": "access",
                "user_type": "human"
            })

            refresh_token = create_refresh_token(username)

            SecurityAuditLogger.log_auth_event(
                "user_authenticated",
                username,
                {"role": user_role.value, "method": "password"}
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "role": user_role.value
            }

    SecurityAuditLogger.log_auth_event(
        "authentication_failed",
        username,
        {"method": "password", "reason": "invalid_credentials"}
    )
    return None


# Middleware for API key authentication (alternative to JWT)
def get_api_key_from_header(request: Request) -> Optional[str]:
    """Extract API key from request headers"""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        api_key = request.headers.get("Authorization")
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key[7:]  # Remove "Bearer " prefix
    return api_key


def require_api_key(request: Request):
    """Middleware to require API key"""
    api_key = get_api_key_from_header(request)
    if not api_key or not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key