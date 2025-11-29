"""
Security context for managing user permissions and access control
"""

from typing import Optional, Set, Dict, Any, List
from datetime import datetime
from falkordb import FalkorDB


class SecurityContext:
    """
    Security context that holds user information and provides permission checking
    """
    
    def __init__(self, user_data: Optional[Dict[str, Any]] = None, graph: Optional[FalkorDB] = None):
        """
        Initialize security context
        
        Args:
            user_data: Dictionary containing user information (username, roles, permissions)
            graph: FalkorDB graph instance for querying additional permissions
        """
        self.user_data = user_data or {}
        self.graph = graph
        self.username = self.user_data.get('username')
        self.is_superuser = self.user_data.get('is_superuser', False)
        self._permissions_cache: Optional[Set[str]] = None
        self._roles_cache: Optional[List[str]] = None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.username is not None
    
    @property
    def is_anonymous(self) -> bool:
        """Check if user is anonymous"""
        return not self.is_authenticated
    
    def get_permissions(self) -> Set[str]:
        """
        Get all permissions for the current user
        
        Returns:
            Set of permission strings (e.g., {"analytics:read", "ingestion:write"})
        """
        if self._permissions_cache is not None:
            return self._permissions_cache
        
        if self.is_superuser:
            # Superusers have all permissions
            self._permissions_cache = {"*:*"}
            return self._permissions_cache
        
        # Get permissions from user data
        permissions = set(self.user_data.get('permissions', []))
        
        # If graph is available, query for role-based permissions
        if self.graph and self.username:
            try:
                query = """
                MATCH (u:User {username: $username})-[:HAS_ROLE]->(r:Role)
                      -[:HAS_PERMISSION]->(p:Permission)
                RETURN DISTINCT p.name as permission
                """
                result = self.graph.query(query, {'username': self.username})
                permissions.update([row['permission'] for row in result.result_set])
            except Exception as e:
                print(f"Error fetching permissions from graph: {e}")
        
        self._permissions_cache = permissions
        return permissions
    
    def get_roles(self) -> List[str]:
        """
        Get all roles for the current user
        
        Returns:
            List of role names
        """
        if self._roles_cache is not None:
            return self._roles_cache
        
        roles = self.user_data.get('roles', [])
        
        # If graph is available, query for roles
        if self.graph and self.username:
            try:
                query = """
                MATCH (u:User {username: $username})-[:HAS_ROLE]->(r:Role)
                RETURN DISTINCT r.name as role
                """
                result = self.graph.query(query, {'username': self.username})
                roles = [row['role'] for row in result.result_set]
            except Exception as e:
                print(f"Error fetching roles from graph: {e}")
        
        self._roles_cache = roles
        return roles
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            permission: Permission string (e.g., "analytics:read")
            
        Returns:
            True if user has permission, False otherwise
        """
        if not self.is_authenticated:
            return False
        
        if self.is_superuser:
            return True
        
        permissions = self.get_permissions()
        
        # Check for exact match
        if permission in permissions:
            return True
        
        # Check for wildcard permissions
        if "*:*" in permissions:
            return True
        
        # Check for resource wildcard (e.g., "analytics:*")
        resource, action = permission.split(':') if ':' in permission else (permission, '*')
        if f"{resource}:*" in permissions:
            return True
        
        return False
    
    def has_any_permission(self, *permissions: str) -> bool:
        """
        Check if user has any of the specified permissions
        
        Args:
            permissions: Variable number of permission strings
            
        Returns:
            True if user has at least one permission, False otherwise
        """
        return any(self.has_permission(p) for p in permissions)
    
    def has_all_permissions(self, *permissions: str) -> bool:
        """
        Check if user has all of the specified permissions
        
        Args:
            permissions: Variable number of permission strings
            
        Returns:
            True if user has all permissions, False otherwise
        """
        return all(self.has_permission(p) for p in permissions)
    
    def has_role(self, role_name: str) -> bool:
        """
        Check if user has a specific role
        
        Args:
            role_name: Name of the role
            
        Returns:
            True if user has role, False otherwise
        """
        if not self.is_authenticated:
            return False
        
        if self.is_superuser and role_name == 'admin':
            return True
        
        return role_name in self.get_roles()
    
    def require_permission(self, permission: str) -> None:
        """
        Require a specific permission, raise exception if not found
        
        Args:
            permission: Permission string
            
        Raises:
            PermissionError: If user doesn't have the permission
        """
        if not self.has_permission(permission):
            raise PermissionError(
                f"User '{self.username or 'anonymous'}' does not have permission '{permission}'"
            )
    
    def require_authentication(self) -> None:
        """
        Require user to be authenticated
        
        Raises:
            PermissionError: If user is not authenticated
        """
        if not self.is_authenticated:
            raise PermissionError("Authentication required")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert security context to dictionary
        
        Returns:
            Dictionary representation of security context
        """
        return {
            'username': self.username,
            'is_authenticated': self.is_authenticated,
            'is_superuser': self.is_superuser,
            'roles': self.get_roles(),
            'permissions': list(self.get_permissions())
        }


# Anonymous security context (no permissions)
ANONYMOUS_CONTEXT = SecurityContext()
