"""
Security context for managing user permissions and access control
"""

from typing import Optional, Set, Dict, Any, List
from datetime import datetime
import json
from falkordb import FalkorDB


class SecurityContext:
    """
    Security context that holds user information and provides permission checking
    """
    
    def __init__(self, user_data: Optional[Dict[str, Any]] = None, graph: Optional[FalkorDB] = None, lazy_load: bool = True):
        """
        Initialize security context
        
        Args:
            user_data: Dictionary containing user information (username, roles, permissions)
            graph: FalkorDB graph instance for querying additional permissions
            lazy_load: If True, permissions are loaded on-demand (default: True)
        """
        self.user_data = user_data or {}
        self.graph = graph
        self.lazy_load = lazy_load
        # JWT payload uses 'sub' for username, but also check 'username'
        self.username = self.user_data.get('sub') or self.user_data.get('username')
        self.is_superuser = self.user_data.get('is_superuser', False)
        self._permissions_cache: Optional[Set[str]] = None
        self._roles_cache: Optional[List[str]] = None
        # Data-level filtering caches
        self._row_filters_cache: Dict[str, List[str]] = {}
        self._denied_properties_cache: Dict[str, Set[str]] = {}
        self._edge_filters_cache: Dict[str, List[str]] = {}
        self._permissions_details_cache: Optional[List[Dict[str, Any]]] = None
    
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
    
    def _get_permission_details(self) -> List[Dict[str, Any]]:
        """
        Get detailed permission information from graph.
        
        Returns:
            List of permission dictionaries with full metadata
        """
        if self._permissions_details_cache is not None:
            return self._permissions_details_cache
        
        if not self.lazy_load:
            # If lazy loading disabled, return empty
            return []
        
        if not self.graph or not self.username:
            return []
        
        if self.is_superuser:
            # Superusers bypass all filters
            return []
        
        try:
            query = """
            MATCH (u:User {username: $username})-[:HAS_ROLE]->(r:Role)
                  -[:HAS_PERMISSION]->(p:Permission)
            RETURN DISTINCT p.name as name,
                   p.resource as resource,
                   p.action as action,
                   p.node_label as node_label,
                   p.edge_type as edge_type,
                   p.property_name as property_name,
                   p.property_filter as property_filter,
                   p.attribute_conditions as attribute_conditions,
                   p.grant_type as grant_type
            """
            result = self.graph.query(query, {'username': self.username})
            
            permissions = []
            if result.result_set:
                for row in result.result_set:
                    perm = {
                        'name': row[0],
                        'resource': row[1],
                        'action': row[2],
                        'node_label': row[3],
                        'edge_type': row[4],
                        'property_name': row[5],
                        'property_filter': row[6],
                        'attribute_conditions': row[7],
                        'grant_type': row[8] or 'GRANT'
                    }
                    permissions.append(perm)
            
            self._permissions_details_cache = permissions
            return permissions
        except Exception as e:
            print(f"Error fetching permission details: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_row_filters(self, entity_label: str, action: str = 'read') -> List[str]:
        """
        Get WHERE clause conditions for row-level filtering.
        
        Args:
            entity_label: Entity label (e.g., "Geography", "Commodity")
            action: Action type (default: "read")
            
        Returns:
            List of Cypher WHERE condition strings
        """
        cache_key = f"{entity_label}:{action}"
        if cache_key in self._row_filters_cache:
            return self._row_filters_cache[cache_key]
        
        if self.is_superuser:
            return []
        
        filters = []
        permissions = self._get_permission_details()
        
        for perm in permissions:
            # Node-level GRANT permissions -> positive filters
            if (perm.get('resource') == 'node' and 
                perm.get('action') == action and
                perm.get('node_label') == entity_label and
                perm.get('grant_type') == 'GRANT'):
                
                # Build WHERE conditions from property_filter
                if perm.get('property_filter'):
                    try:
                        prop_filter = json.loads(perm['property_filter'])
                        for key, value in prop_filter.items():
                            if isinstance(value, str):
                                filters.append(f"{key} = '{value}'")
                            else:
                                filters.append(f"{key} = {value}")
                    except json.JSONDecodeError:
                        pass
                
                # Add attribute_conditions
                if perm.get('attribute_conditions'):
                    filters.append(perm['attribute_conditions'])
            
            # Node-level DENY permissions -> negative filters (precedence over grant)
            if (perm.get('resource') == 'node' and 
                perm.get('action') == action and
                perm.get('node_label') == entity_label and
                perm.get('grant_type') == 'DENY'):
                # Build NOT(...) condition from property_filter
                if perm.get('property_filter'):
                    try:
                        prop_filter = json.loads(perm['property_filter'])
                        parts = []
                        for key, value in prop_filter.items():
                            if isinstance(value, str):
                                parts.append(f"{key} = '{value}'")
                            else:
                                parts.append(f"{key} = {value}")
                        if parts:
                            # Use NOT (a AND b ...) to correctly represent deny condition
                            filters.append(f"NOT (" + " AND ".join(parts) + ")")
                    except json.JSONDecodeError:
                        pass
        
        self._row_filters_cache[cache_key] = filters
        return filters
    
    def get_denied_properties(self, entity_label: str, action: str = 'read') -> Set[str]:
        """
        Get set of property names that should be filtered out.
        
        Args:
            entity_label: Entity label (e.g., "Geography", "Commodity")
            action: Action type (default: "read")
            
        Returns:
            Set of property names to deny
        """
        cache_key = f"{entity_label}:{action}"
        if cache_key in self._denied_properties_cache:
            return self._denied_properties_cache[cache_key]
        
        if self.is_superuser:
            return set()
        
        denied = set()
        permissions = self._get_permission_details()
        
        for perm in permissions:
            # Process property-level DENY permissions
            if (perm.get('resource') == 'property' and
                perm.get('action') == action and
                perm.get('grant_type') == 'DENY'):
                
                # Check if permission applies to this entity label
                perm_label = perm.get('node_label')
                if perm_label == entity_label or perm_label == '*' or not perm_label:
                    property_name = perm.get('property_name')
                    if property_name:
                        denied.add(property_name)
        
        self._denied_properties_cache[cache_key] = denied
        return denied
    
    def get_edge_filters(self, edge_type: str, action: str = 'read') -> List[str]:
        """
        Get WHERE clause conditions for relationship-level filtering.
        
        Args:
            edge_type: Relationship type (e.g., "TRADES_WITH", "PRODUCES")
            action: Action type (default: "read")
            
        Returns:
            List of Cypher WHERE condition strings for relationships
        """
        cache_key = f"{edge_type}:{action}"
        if cache_key in self._edge_filters_cache:
            return self._edge_filters_cache[cache_key]
        
        if self.is_superuser:
            return []
        
        filters = []
        permissions = self._get_permission_details()
        
        for perm in permissions:
            # Only process edge-level GRANT permissions with filters
            if (perm.get('resource') == 'edge' and
                perm.get('action') == action and
                perm.get('edge_type') == edge_type and
                perm.get('grant_type') == 'GRANT'):
                
                # Build WHERE conditions from property_filter
                if perm.get('property_filter'):
                    try:
                        prop_filter = json.loads(perm['property_filter'])
                        for key, value in prop_filter.items():
                            if isinstance(value, str):
                                filters.append(f"{key} = '{value}'")
                            else:
                                filters.append(f"{key} = {value}")
                    except json.JSONDecodeError:
                        pass
                
                # Add attribute_conditions
                if perm.get('attribute_conditions'):
                    filters.append(perm['attribute_conditions'])
        
        self._edge_filters_cache[cache_key] = filters
        return filters
    
    def get_attribute_conditions(self, entity_label: str, action: str = 'read') -> List[str]:
        """
        Get dynamic attribute conditions for entity.
        
        Args:
            entity_label: Entity label
            action: Action type (default: "read")
            
        Returns:
            List of Cypher condition strings
        """
        # This is a convenience method that extracts just attribute_conditions
        permissions = self._get_permission_details()
        conditions = []
        
        for perm in permissions:
            if (perm.get('node_label') == entity_label and
                perm.get('action') == action and
                perm.get('attribute_conditions')):
                conditions.append(perm['attribute_conditions'])
        
        return conditions
    
    def clear_cache(self):
        """Clear all caches."""
        self._permissions_cache = None
        self._roles_cache = None
        self._permissions_details_cache = None
        self._row_filters_cache.clear()
        self._denied_properties_cache.clear()
        self._edge_filters_cache.clear()
    
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
