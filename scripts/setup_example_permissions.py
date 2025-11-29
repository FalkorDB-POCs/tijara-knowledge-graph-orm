#!/usr/bin/env python3
"""
Setup example permissions for testing data-level security filtering.

This script creates sample Permission entities that demonstrate:
- Row-level filtering (France-only Geography access)
- Property-level filtering (price denial)
- Edge-level filtering (wheat trades only)
- Attribute-based filtering (high-value trades)
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from falkordb import FalkorDB
from src.models.security import Permission, Role, User, PERMISSION_DEFINITIONS
from src.security.auth import hash_password


def load_config():
    """Load configuration."""
    config_path = project_root / 'config' / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def connect_to_rbac_graph(config):
    """Connect to RBAC graph."""
    db = FalkorDB(
        host=config['rbac'].get('host', 'localhost'),
        port=config['rbac'].get('port', 6379)
    )
    return db.select_graph(config['rbac']['graph_name'])


def create_sample_permissions(graph):
    """Create sample permissions for testing."""
    
    print("Creating example permissions...")
    
    permissions = [
        # Row-level: France-only Geography access
        {
            'name': 'node:read:france_only',
            'resource': 'node',
            'action': 'read',
            'description': 'Read only French geography nodes',
            'node_label': 'Geography',
            'property_filter': '{"country": "France"}',
            'grant_type': 'GRANT'
        },
        
        # Row-level: Recent data only (2024+)
        {
            'name': 'node:read:recent_data',
            'resource': 'node',
            'action': 'read',
            'description': 'Read only recent production data',
            'node_label': 'Production',
            'attribute_conditions': 'n.year >= 2024',
            'grant_type': 'GRANT'
        },
        
        # Property-level: Deny price
        {
            'name': 'property:deny:price',
            'resource': 'property',
            'action': 'read',
            'description': 'Deny access to price information',
            'property_name': 'price',
            'grant_type': 'DENY'
        },
        
        # Property-level: Deny confidential notes
        {
            'name': 'property:deny:confidential',
            'resource': 'property',
            'action': 'read',
            'description': 'Deny access to confidential notes',
            'property_name': 'confidential_notes',
            'grant_type': 'DENY'
        },
        
        # Edge-level: Wheat trades only
        {
            'name': 'edge:read:wheat_trades',
            'resource': 'edge',
            'action': 'read',
            'description': 'Read wheat trading relationships only',
            'edge_type': 'TRADES_WITH',
            'property_filter': '{"commodity": "Wheat"}',
            'grant_type': 'GRANT'
        },
        
        # Attribute-based: High-value trades only
        {
            'name': 'node:read:high_value_trades',
            'resource': 'node',
            'action': 'read',
            'description': 'Read trades above 1M USD only',
            'node_label': 'Trade',
            'attribute_conditions': 'n.value > 1000000',
            'grant_type': 'GRANT'
        },
        
        # Combined: France + Recent
        {
            'name': 'node:read:france_recent',
            'resource': 'node',
            'action': 'read',
            'description': 'Read French data from 2024+',
            'node_label': 'BalanceSheet',
            'property_filter': '{"country": "France"}',
            'attribute_conditions': 'n.year >= 2024',
            'grant_type': 'GRANT'
        }
    ]
    
    created_count = 0
    for perm_data in permissions:
        # Check if exists
        check_query = "MATCH (p:Permission {name: $name}) RETURN p"
        result = graph.query(check_query, {'name': perm_data['name']})
        
        if result.result_set:
            print(f"  ✓ Permission '{perm_data['name']}' already exists")
            continue
        
        # Create permission
        query = """
        CREATE (p:Permission {
            name: $name,
            resource: $resource,
            action: $action,
            description: $description,
            node_label: $node_label,
            edge_type: $edge_type,
            property_name: $property_name,
            property_filter: $property_filter,
            attribute_conditions: $attribute_conditions,
            grant_type: $grant_type,
            created_at: datetime()
        })
        RETURN p
        """
        
        params = {
            'name': perm_data['name'],
            'resource': perm_data['resource'],
            'action': perm_data['action'],
            'description': perm_data.get('description'),
            'node_label': perm_data.get('node_label'),
            'edge_type': perm_data.get('edge_type'),
            'property_name': perm_data.get('property_name'),
            'property_filter': perm_data.get('property_filter'),
            'attribute_conditions': perm_data.get('attribute_conditions'),
            'grant_type': perm_data['grant_type']
        }
        
        graph.query(query, params)
        print(f"  ✓ Created permission '{perm_data['name']}'")
        created_count += 1
    
    print(f"\nCreated {created_count} new permissions")
    return created_count


def create_test_roles(graph):
    """Create test roles with permissions."""
    
    print("\nCreating test roles...")
    
    roles = [
        {
            'name': 'french_analyst',
            'description': 'Analyst with access to French data only',
            'permissions': ['node:read:france_only', 'property:deny:price']
        },
        {
            'name': 'recent_data_viewer',
            'description': 'Viewer with access to recent data only',
            'permissions': ['node:read:recent_data', 'property:deny:confidential']
        },
        {
            'name': 'wheat_trader',
            'description': 'Trader focused on wheat commodities',
            'permissions': ['edge:read:wheat_trades', 'node:read:high_value_trades']
        },
        {
            'name': 'restricted_viewer',
            'description': 'Highly restricted viewer',
            'permissions': ['node:read:france_recent', 'property:deny:price', 'property:deny:confidential']
        }
    ]
    
    created_count = 0
    for role_data in roles:
        # Check if exists
        check_query = "MATCH (r:Role {name: $name}) RETURN r"
        result = graph.query(check_query, {'name': role_data['name']})
        
        if result.result_set:
            print(f"  ✓ Role '{role_data['name']}' already exists")
            continue
        
        # Create role
        query = """
        CREATE (r:Role {
            name: $name,
            description: $description,
            is_system: false,
            created_at: datetime()
        })
        RETURN r
        """
        
        graph.query(query, {
            'name': role_data['name'],
            'description': role_data['description']
        })
        
        # Link permissions
        for perm_name in role_data['permissions']:
            link_query = """
            MATCH (r:Role {name: $role_name})
            MATCH (p:Permission {name: $perm_name})
            MERGE (r)-[:HAS_PERMISSION]->(p)
            """
            graph.query(link_query, {
                'role_name': role_data['name'],
                'perm_name': perm_name
            })
        
        print(f"  ✓ Created role '{role_data['name']}' with {len(role_data['permissions'])} permissions")
        created_count += 1
    
    print(f"\nCreated {created_count} new roles")
    return created_count


def create_test_users(graph):
    """Create test users."""
    
    print("\nCreating test users...")
    
    users = [
        {
            'username': 'french_analyst1',
            'email': 'analyst@france.example.com',
            'full_name': 'French Analyst',
            'password': 'test123',
            'roles': ['french_analyst']
        },
        {
            'username': 'wheat_trader1',
            'email': 'trader@wheat.example.com',
            'full_name': 'Wheat Trader',
            'password': 'test123',
            'roles': ['wheat_trader']
        },
        {
            'username': 'restricted_viewer1',
            'email': 'viewer@restricted.example.com',
            'full_name': 'Restricted Viewer',
            'password': 'test123',
            'roles': ['restricted_viewer']
        }
    ]
    
    created_count = 0
    for user_data in users:
        # Check if exists
        check_query = "MATCH (u:User {username: $username}) RETURN u"
        result = graph.query(check_query, {'username': user_data['username']})
        
        if result.result_set:
            print(f"  ✓ User '{user_data['username']}' already exists")
            continue
        
        # Create user
        password_hash = hash_password(user_data['password'])
        
        query = """
        CREATE (u:User {
            username: $username,
            email: $email,
            full_name: $full_name,
            password_hash: $password_hash,
            is_active: true,
            is_superuser: false,
            created_at: datetime()
        })
        RETURN u
        """
        
        graph.query(query, {
            'username': user_data['username'],
            'email': user_data['email'],
            'full_name': user_data['full_name'],
            'password_hash': password_hash
        })
        
        # Link roles
        for role_name in user_data['roles']:
            link_query = """
            MATCH (u:User {username: $username})
            MATCH (r:Role {name: $role_name})
            MERGE (u)-[:HAS_ROLE]->(r)
            """
            graph.query(link_query, {
                'username': user_data['username'],
                'role_name': role_name
            })
        
        print(f"  ✓ Created user '{user_data['username']}' (password: {user_data['password']})")
        created_count += 1
    
    print(f"\nCreated {created_count} new users")
    return created_count


def main():
    """Main setup function."""
    print("=" * 60)
    print("Setting up example permissions for data-level security")
    print("=" * 60)
    
    # Load config and connect
    config = load_config()
    graph = connect_to_rbac_graph(config)
    
    # Create permissions, roles, and users
    perms_created = create_sample_permissions(graph)
    roles_created = create_test_roles(graph)
    users_created = create_test_users(graph)
    
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  - {perms_created} permissions created")
    print(f"  - {roles_created} roles created")
    print(f"  - {users_created} users created")
    
    print("\nTest users:")
    print("  - french_analyst1 / test123")
    print("  - wheat_trader1 / test123")
    print("  - restricted_viewer1 / test123")
    
    print("\nYou can now test data-level filtering with these users!")


if __name__ == "__main__":
    main()
