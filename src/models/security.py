"""
Security models for RBAC (Role-Based Access Control)
Uses FalkorDB ORM v1.2.0 to store users, roles, and permissions in the graph
"""

from typing import Optional, List
from datetime import datetime
from falkordb_orm import (
    node, relationship, generated_id, property as orm_property,
    unique
)


@node("User")
class User:
    """User entity with authentication and RBAC"""
    
    id: Optional[int] = generated_id()
    username: str = unique()
    email: str = orm_property()
    password_hash: str = orm_property()  # Hashed password
    full_name: Optional[str] = orm_property()
    is_active: bool = orm_property()
    is_superuser: bool = orm_property()
    created_at: str = orm_property()  # ISO format datetime string
    last_login: Optional[str] = orm_property()  # ISO format datetime string
    
    # Relationships
    roles = relationship("HAS_ROLE", target="Role", direction="outgoing")


@node("Role")
class Role:
    """Role entity for grouping permissions"""
    
    id: Optional[int] = generated_id()
    name: str = unique()
    description: Optional[str] = orm_property()
    is_system: bool = orm_property()  # System roles cannot be deleted
    created_at: str = orm_property()  # ISO format datetime string
    
    # Relationships
    permissions = relationship("HAS_PERMISSION", target="Permission", direction="outgoing")
    parent_roles = relationship("INHERITS_FROM", target="Role", direction="outgoing")


@node("Permission")
class Permission:
    """Permission entity for fine-grained access control
    
    Supports attribute-based access control (ABAC) through:
    - node_label: Restrict access to specific node types
    - edge_type: Restrict access to specific relationship types
    - property_filter: JSON filter for property-level access
    - attribute_conditions: Cypher WHERE clause for dynamic filtering
    """
    
    id: Optional[int] = generated_id()
    name: str = unique()
    resource: str = orm_property()  # e.g., "analytics", "ingestion", "discovery", "node", "edge"
    action: str = orm_property()  # e.g., "read", "write", "execute", "admin", "traverse"
    description: Optional[str] = orm_property()
    scope: Optional[str] = orm_property()  # Optional scope filter (e.g., "commodity:wheat")
    created_at: str = orm_property()  # ISO format datetime string
    
    # Attribute-based access control fields
    node_label: Optional[str] = orm_property()  # Specific node label (e.g., "Geography", "Commodity")
    edge_type: Optional[str] = orm_property()  # Specific relationship type (e.g., "TRADES_WITH", "PRODUCES")
    property_name: Optional[str] = orm_property()  # Specific property name for property-level security
    property_filter: Optional[str] = orm_property()  # JSON filter: {"country": "France", "type": "Export"}
    attribute_conditions: Optional[str] = orm_property()  # Cypher WHERE clause for complex conditions
    grant_type: str = orm_property()  # "GRANT" or "DENY" - DENY takes precedence


# Built-in system roles
SYSTEM_ROLES = {
    "admin": {
        "description": "Full system access including user management",
        "permissions": [
            "analytics:read", "analytics:execute",
            "ingestion:read", "ingestion:write",
            "discovery:read", "discovery:execute",
            "impact:read", "impact:execute",
            "rbac:read", "rbac:write", "rbac:admin"
        ]
    },
    "analyst": {
        "description": "Can view and run analytics, read-only on data",
        "permissions": [
            "analytics:read", "analytics:execute",
            "discovery:read",
            "impact:read", "impact:execute"
        ]
    },
    "trader": {
        "description": "Can view data, run queries, and analyze impacts",
        "permissions": [
            "analytics:read", "analytics:execute",
            "discovery:read", "discovery:execute",
            "impact:read", "impact:execute"
        ]
    },
    "data_engineer": {
        "description": "Can ingest data and manage data pipelines",
        "permissions": [
            "ingestion:read", "ingestion:write",
            "discovery:read"
        ]
    },
    "viewer": {
        "description": "Read-only access to discovery and basic analytics",
        "permissions": [
            "analytics:read",
            "discovery:read"
        ]
    }
}


# Permission definitions
PERMISSION_DEFINITIONS = {
    # Analytics permissions
    "analytics:read": {"resource": "analytics", "action": "read", "description": "View analytics queries and results", "grant_type": "GRANT"},
    "analytics:execute": {"resource": "analytics", "action": "execute", "description": "Execute graph algorithms and analytics", "grant_type": "GRANT"},
    
    # Data Ingestion permissions
    "ingestion:read": {"resource": "ingestion", "action": "read", "description": "View data ingestion status", "grant_type": "GRANT"},
    "ingestion:write": {"resource": "ingestion", "action": "write", "description": "Ingest and modify data", "grant_type": "GRANT"},
    
    # Discovery permissions
    "discovery:read": {"resource": "discovery", "action": "read", "description": "View search and view entities", "grant_type": "GRANT"},
    "discovery:execute": {"resource": "discovery", "action": "execute", "description": "Execute complex search queries", "grant_type": "GRANT"},
    
    # Impact Analysis permissions
    "impact:read": {"resource": "impact", "action": "read", "description": "View impact analysis results", "grant_type": "GRANT"},
    "impact:execute": {"resource": "impact", "action": "execute", "description": "Run impact analysis scenarios", "grant_type": "GRANT"},
    
    # RBAC Management permissions
    "rbac:read": {"resource": "rbac", "action": "read", "description": "View users, roles, and permissions", "grant_type": "GRANT"},
    "rbac:write": {"resource": "rbac", "action": "write", "description": "Create and modify users and roles", "grant_type": "GRANT"},
    "rbac:admin": {"resource": "rbac", "action": "admin", "description": "Full RBAC administration including system roles", "grant_type": "GRANT"},
    
    # Node-level attribute-based permissions
    "node:read:geography": {
        "resource": "node",
        "action": "read",
        "description": "Read Geography nodes",
        "node_label": "Geography",
        "grant_type": "GRANT"
    },
    "node:read:commodity": {
        "resource": "node",
        "action": "read",
        "description": "Read Commodity nodes",
        "node_label": "Commodity",
        "grant_type": "GRANT"
    },
    "node:read:france_only": {
        "resource": "node",
        "action": "read",
        "description": "Read only French geography nodes",
        "node_label": "Geography",
        "property_filter": '{"country": "France"}',
        "grant_type": "GRANT"
    },
    "node:write:production": {
        "resource": "node",
        "action": "write",
        "description": "Write Production data nodes",
        "node_label": "Production",
        "grant_type": "GRANT"
    },
    
    # Edge-level attribute-based permissions
    "edge:read:trades": {
        "resource": "edge",
        "action": "read",
        "description": "Read TRADES_WITH relationships",
        "edge_type": "TRADES_WITH",
        "grant_type": "GRANT"
    },
    "edge:read:wheat_trades": {
        "resource": "edge",
        "action": "read",
        "description": "Read wheat trading relationships only",
        "edge_type": "TRADES_WITH",
        "property_filter": '{"commodity": "Wheat"}',
        "grant_type": "GRANT"
    },
    "edge:traverse:produces": {
        "resource": "edge",
        "action": "traverse",
        "description": "Traverse PRODUCES relationships",
        "edge_type": "PRODUCES",
        "grant_type": "GRANT"
    },
    
    # Property-level permissions
    "property:deny:sensitive": {
        "resource": "property",
        "action": "read",
        "description": "Deny access to sensitive properties",
        "property_name": "confidential_notes",
        "grant_type": "DENY"
    },
    "property:deny:price": {
        "resource": "property",
        "action": "read",
        "description": "Deny access to price information",
        "property_name": "price",
        "grant_type": "DENY"
    },
    
    # Complex conditional permissions
    "node:read:high_value_trades": {
        "resource": "node",
        "action": "read",
        "description": "Read trades above 1M USD only",
        "node_label": "Trade",
        "attribute_conditions": "n.value > 1000000",
        "grant_type": "GRANT"
    },
    "node:read:recent_data": {
        "resource": "node",
        "action": "read",
        "description": "Read only data from last year",
        "node_label": "Production",
        "attribute_conditions": "n.year >= 2024",
        "grant_type": "GRANT"
    },
    "edge:read:us_france_only": {
        "resource": "edge",
        "action": "read",
        "description": "Read trades between US and France only",
        "edge_type": "TRADES_WITH",
        "attribute_conditions": "(startNode(r).country = 'USA' AND endNode(r).country = 'France') OR (startNode(r).country = 'France' AND endNode(r).country = 'USA')",
        "grant_type": "GRANT"
    }
}
