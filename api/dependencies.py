"""
FastAPI Security Dependencies

Provides authentication and authorization dependencies for protecting API endpoints.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.security.auth import decode_access_token
from src.security.context import SecurityContext, ANONYMOUS_CONTEXT

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Dependency to extract and validate the current user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials containing JWT token
        
    Returns:
        User data dictionary with 'sub' (username), 'user_id', and 'is_superuser'
        
    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Optional authentication dependency - returns None if not authenticated.
    
    Useful for endpoints that support both authenticated and anonymous access.
    
    Args:
        credentials: HTTP Bearer credentials containing JWT token
        
    Returns:
        User data dictionary if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    return payload


def require_permission(permission: str):
    """
    Dependency factory to require a specific permission.
    
    Usage:
        @app.get("/analytics", dependencies=[Depends(require_permission("analytics:read"))])
        
    Args:
        permission: Permission string in format "resource:action" (e.g., "analytics:execute")
        
    Returns:
        Dependency function that checks the permission
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if permission denied
    """
    async def permission_checker(user: dict = Depends(get_current_user)) -> SecurityContext:
        """Check if user has the required permission."""
        context = SecurityContext(user_data=user)
        
        try:
            context.require_permission(permission)
        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        
        return context
    
    return permission_checker


def require_any_permission(*permissions: str):
    """
    Dependency factory to require ANY of the specified permissions.
    
    Usage:
        @app.get("/data", dependencies=[Depends(require_any_permission("read:data", "admin:all"))])
        
    Args:
        *permissions: Variable number of permission strings
        
    Returns:
        Dependency function that checks if user has any of the permissions
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if none of the permissions match
    """
    async def permission_checker(user: dict = Depends(get_current_user)) -> SecurityContext:
        """Check if user has any of the required permissions."""
        context = SecurityContext(user_data=user)
        
        # Try each permission
        for permission in permissions:
            if context.has_permission(permission):
                return context
        
        # None of the permissions matched
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of: {', '.join(permissions)}"
        )
    
    return permission_checker


def require_superuser():
    """
    Dependency to require superuser (admin) access.
    
    Usage:
        @app.post("/system/config", dependencies=[Depends(require_superuser())])
        
    Returns:
        Dependency function that checks for superuser status
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if not superuser
    """
    async def superuser_checker(user: dict = Depends(get_current_user)) -> dict:
        """Check if user is a superuser."""
        if not user.get("is_superuser", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superuser access required"
            )
        
        return user
    
    return superuser_checker


async def get_security_context(
    request: Request,
    user: Optional[dict] = Depends(get_current_user_optional)
) -> SecurityContext:
    """
    Dependency to get SecurityContext for the current request.
    
    Creates a SecurityContext with user data and graph connection for
    data-level security filtering.
    
    Args:
        request: FastAPI request object
        user: Optional user data from JWT token
        
    Returns:
        SecurityContext instance
    """
    if not user:
        return ANONYMOUS_CONTEXT
    
    # Get graph connection from app state (will be set in main.py)
    graph = getattr(request.app.state, 'rbac_graph', None)
    
    # Create SecurityContext with user data and graph
    # Use lazy_load=True to avoid loading permissions during simple auth checks
    context = SecurityContext(user_data=user, graph=graph, lazy_load=True)
    
    return context
