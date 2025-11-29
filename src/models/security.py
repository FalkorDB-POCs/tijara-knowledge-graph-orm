"""
Security models for RBAC (Role-Based Access Control)
Uses FalkorDB ORM v1.2.0 to store users, roles, and permissions in the graph
"""

from typing import Optional, List
from datetime import datetime
from falkordb_orm import (
    node, relationship, generated_id, property as orm_property,
    unique, required
)


@node("User")
class User:
    """User entity with authentication and RBAC"""
    
    id: Optional[int] = generated_id()
    username: str = unique(required=True)
    email: str = orm_property(required=True)
    password_hash: str = orm_property(required=True)  # Hashed password
    full_name: Optional[str] = orm_property()
    is_active: bool = orm_property(default=True)
    is_superuser: bool = orm_property(default=False)
    created_at: datetime = orm_property(default_factory=datetime.now)
    last_login: Optional[datetime] = orm_property()
    
    # Relationships
    roles = relationship("HAS_ROLE", target="Role", direction="outgoing")


@node("Role")
class Role:
    """Role entity for grouping permissions"""
    
    id: Optional[int] = generated_id()
    name: str = unique(required=True)
    description: Optional[str] = orm_property()
    is_system: bool = orm_property(default=False)  # System roles cannot be deleted
    created_at: datetime = orm_property(default_factory=datetime.now)
    
    # Relationships
    permissions = relationship("HAS_PERMISSION", target="Permission", direction="outgoing")
    parent_roles = relationship("INHERITS_FROM", target="Role", direction="outgoing")


@node("Permission")
class Permission:
    """Permission entity for fine-grained access control"""
    
    id: Optional[int] = generated_id()
    name: str = unique(required=True)
    resource: str = orm_property(required=True)  # e.g., "analytics", "ingestion", "discovery"
    action: str = orm_property(required=True)  # e.g., "read", "write", "execute", "admin"
    description: Optional[str] = orm_property()
    scope: Optional[str] = orm_property()  # Optional scope filter (e.g., "commodity:wheat")
    created_at: datetime = orm_property(default_factory=datetime.now)


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
    "analytics:read": {"resource": "analytics", "action": "read", "description": "View analytics queries and results"},
    "analytics:execute": {"resource": "analytics", "action": "execute", "description": "Execute graph algorithms and analytics"},
    
    # Data Ingestion permissions
    "ingestion:read": {"resource": "ingestion", "action": "read", "description": "View data ingestion status"},
    "ingestion:write": {"resource": "ingestion", "action": "write", "description": "Ingest and modify data"},
    
    # Discovery permissions
    "discovery:read": {"resource": "discovery", "action": "read", "description": "Search and view entities"},
    "discovery:execute": {"resource": "discovery", "action": "execute", "description": "Execute complex search queries"},
    
    # Impact Analysis permissions
    "impact:read": {"resource": "impact", "action": "read", "description": "View impact analysis results"},
    "impact:execute": {"resource": "impact", "action": "execute", "description": "Run impact analysis scenarios"},
    
    # RBAC Management permissions
    "rbac:read": {"resource": "rbac", "action": "read", "description": "View users, roles, and permissions"},
    "rbac:write": {"resource": "rbac", "action": "write", "description": "Create and modify users and roles"},
    "rbac:admin": {"resource": "rbac", "action": "admin", "description": "Full RBAC administration including system roles"}
}
