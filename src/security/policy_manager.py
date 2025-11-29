"""
Policy manager for converting Permission entities to SecurityPolicy rules.

This module bridges the gap between the application's Permission entities
stored in the graph and the falkordb-orm SecurityPolicy abstraction.
"""

from typing import List, Optional, Dict, Any
import json
from falkordb import Graph
from falkordb_orm.security import SecurityPolicy, PolicyRule


class PolicyManager:
    """
    Manages security policies by loading Permission entities from the graph
    and converting them to PolicyRules for use with QueryRewriter.
    """
    
    def __init__(self, graph: Graph):
        """
        Initialize PolicyManager.
        
        Args:
            graph: FalkorDB graph instance
        """
        self.graph = graph
        self._policy_cache: Optional[SecurityPolicy] = None
    
    @staticmethod
    def initialize_policy(graph: Graph) -> SecurityPolicy:
        """
        Initialize SecurityPolicy from Permission entities in the graph.
        
        Args:
            graph: FalkorDB graph instance
            
        Returns:
            SecurityPolicy with rules loaded from graph
        """
        manager = PolicyManager(graph)
        return manager.load_policy()
    
    def load_policy(self) -> SecurityPolicy:
        """
        Load all permissions from graph and create SecurityPolicy.
        
        Returns:
            SecurityPolicy with all permission rules
        """
        # Query all permissions from graph
        query = """
        MATCH (p:Permission)
        RETURN p.name as name,
               p.resource as resource,
               p.action as action,
               p.node_label as node_label,
               p.edge_type as edge_type,
               p.property_name as property_name,
               p.property_filter as property_filter,
               p.attribute_conditions as attribute_conditions,
               p.grant_type as grant_type
        """
        
        result = self.graph.query(query)
        
        # Convert to permission dictionaries
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
        
        return self.sync_permissions_to_policy(permissions)
    
    def sync_permissions_to_policy(
        self, 
        permissions: List[Dict[str, Any]]
    ) -> SecurityPolicy:
        """
        Convert Permission dictionaries to SecurityPolicy.
        
        Args:
            permissions: List of permission dictionaries
            
        Returns:
            SecurityPolicy with converted rules
        """
        policy = SecurityPolicy(self.graph)
        
        for perm in permissions:
            # Build resource pattern from permission
            resource_pattern = self._build_resource_pattern(perm)
            
            # Build conditions from permission metadata
            conditions = self._build_conditions(perm)
            
            # Create PolicyRule
            rule = PolicyRule(
                action=perm['action'],
                resource_pattern=resource_pattern,
                grant_type=perm['grant_type'],
                role='*',  # Will be filtered by SecurityContext based on user roles
                conditions=conditions if conditions else None
            )
            
            # Add to policy
            policy.rules.append(rule)
        
        self._policy_cache = policy
        return policy
    
    def _build_resource_pattern(self, permission: Dict[str, Any]) -> str:
        """
        Build resource pattern from permission fields.
        
        Args:
            permission: Permission dictionary
            
        Returns:
            Resource pattern string
        """
        resource = permission.get('resource', '')
        
        # Node-level: use node_label
        if resource == 'node' and permission.get('node_label'):
            return permission['node_label']
        
        # Edge-level: use edge_type
        if resource == 'edge' and permission.get('edge_type'):
            return permission['edge_type']
        
        # Property-level: use Label.property format
        if resource == 'property' and permission.get('property_name'):
            node_label = permission.get('node_label', '*')
            return f"{node_label}.{permission['property_name']}"
        
        # Default to resource name
        return resource
    
    def _build_conditions(self, permission: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Build conditions dictionary from permission metadata.
        
        Args:
            permission: Permission dictionary
            
        Returns:
            Conditions dictionary or None
        """
        conditions = {}
        
        # Add node_label condition
        if permission.get('node_label'):
            conditions['node_label'] = permission['node_label']
        
        # Add edge_type condition
        if permission.get('edge_type'):
            conditions['edge_type'] = permission['edge_type']
        
        # Add property_name condition
        if permission.get('property_name'):
            conditions['property_name'] = permission['property_name']
        
        # Parse property_filter JSON
        if permission.get('property_filter'):
            try:
                property_filter = json.loads(permission['property_filter'])
                conditions['property_filter'] = property_filter
            except json.JSONDecodeError:
                pass
        
        # Add attribute_conditions as raw Cypher
        if permission.get('attribute_conditions'):
            conditions['attribute_conditions'] = permission['attribute_conditions']
        
        return conditions if conditions else None
    
    @staticmethod
    def build_cypher_condition(permission: Dict[str, Any], var_name: str = 'n') -> Optional[str]:
        """
        Generate Cypher WHERE clause from permission metadata.
        
        Args:
            permission: Permission dictionary
            var_name: Variable name to use in Cypher (default: 'n')
            
        Returns:
            Cypher WHERE condition string or None
        """
        conditions = []
        
        # Add property_filter conditions
        if permission.get('property_filter'):
            try:
                property_filter = json.loads(permission['property_filter'])
                for key, value in property_filter.items():
                    if isinstance(value, str):
                        conditions.append(f"{var_name}.{key} = '{value}'")
                    else:
                        conditions.append(f"{var_name}.{key} = {value}")
            except json.JSONDecodeError:
                pass
        
        # Add attribute_conditions as-is
        if permission.get('attribute_conditions'):
            attr_cond = permission['attribute_conditions']
            # Replace generic 'n' with actual variable name
            attr_cond = attr_cond.replace('n.', f'{var_name}.')
            conditions.append(f"({attr_cond})")
        
        return ' AND '.join(conditions) if conditions else None
    
    def clear_cache(self):
        """Clear the policy cache."""
        self._policy_cache = None
    
    def get_cached_policy(self) -> Optional[SecurityPolicy]:
        """
        Get cached policy without reloading from graph.
        
        Returns:
            Cached SecurityPolicy or None
        """
        return self._policy_cache
