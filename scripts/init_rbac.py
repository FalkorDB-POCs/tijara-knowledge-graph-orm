#!/usr/bin/env python3
"""
Initialize RBAC data in FalkorDB graph
Creates system roles, permissions, and demo users
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from falkordb import FalkorDB
from src.models.security import User, Role, Permission, SYSTEM_ROLES, PERMISSION_DEFINITIONS
from src.security.auth import hash_password
from datetime import datetime
import yaml


def init_rbac(graph_name=None):
    """Initialize RBAC data in separate RBAC graph"""
    
    # Load config to get RBAC graph name
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Use configured RBAC graph or provided graph_name
    if graph_name is None:
        graph_name = config['rbac']['graph_name']
    
    # Connect to FalkorDB
    print(f"Connecting to FalkorDB RBAC graph: {graph_name}")
    db = FalkorDB(host='localhost', port=6379)
    graph = db.select_graph(graph_name)
    
    print("\n" + "="*60)
    print("RBAC Initialization")
    print("="*60)
    
    # Step 1: Create Permissions
    print("\n1. Creating Permissions...")
    permission_map = {}
    for perm_name, perm_def in PERMISSION_DEFINITIONS.items():
        query = """
        MERGE (p:Permission {name: $name})
        SET p.resource = $resource,
            p.action = $action,
            p.description = $description,
            p.grant_type = $grant_type,
            p.node_label = $node_label,
            p.edge_type = $edge_type,
            p.property_name = $property_name,
            p.property_filter = $property_filter,
            p.attribute_conditions = $attribute_conditions,
            p.created_at = $created_at
        RETURN id(p) as id
        """
        params = {
            'name': perm_name,
            'resource': perm_def['resource'],
            'action': perm_def['action'],
            'description': perm_def['description'],
            'grant_type': perm_def.get('grant_type', 'GRANT'),
            'node_label': perm_def.get('node_label'),
            'edge_type': perm_def.get('edge_type'),
            'property_name': perm_def.get('property_name'),
            'property_filter': perm_def.get('property_filter'),
            'attribute_conditions': perm_def.get('attribute_conditions'),
            'created_at': datetime.now().isoformat()
        }
        result = graph.query(query, params)
        perm_id = result.result_set[0][0] if result.result_set else None
        permission_map[perm_name] = perm_id
        
        # Show simplified output for basic permissions, detailed for attribute-based
        if perm_def.get('node_label') or perm_def.get('edge_type') or perm_def.get('attribute_conditions'):
            details = []
            if perm_def.get('node_label'):
                details.append(f"label={perm_def['node_label']}")
            if perm_def.get('edge_type'):
                details.append(f"type={perm_def['edge_type']}")
            if perm_def.get('property_filter'):
                details.append(f"filter={perm_def['property_filter'][:30]}...")
            if perm_def.get('attribute_conditions'):
                details.append(f"where={perm_def['attribute_conditions'][:40]}...")
            print(f"   ✓ {perm_name} ({', '.join(details)})")
        else:
            print(f"   ✓ {perm_name}")
    
    # Step 2: Create Roles
    print("\n2. Creating System Roles...")
    role_map = {}
    for role_name, role_def in SYSTEM_ROLES.items():
        query = """
        MERGE (r:Role {name: $name})
        SET r.description = $description,
            r.is_system = true,
            r.created_at = $created_at
        RETURN id(r) as id
        """
        params = {
            'name': role_name,
            'description': role_def['description'],
            'created_at': datetime.now().isoformat()
        }
        result = graph.query(query, params)
        role_id = result.result_set[0][0] if result.result_set else None
        role_map[role_name] = role_id
        print(f"   ✓ Created role: {role_name}")
        
        # Link role to permissions
        for perm_name in role_def['permissions']:
            if perm_name in permission_map:
                link_query = """
                MATCH (r:Role), (p:Permission)
                WHERE id(r) = $role_id AND id(p) = $perm_id
                MERGE (r)-[:HAS_PERMISSION]->(p)
                """
                graph.query(link_query, {
                    'role_id': role_id,
                    'perm_id': permission_map[perm_name]
                })
        print(f"      Linked {len(role_def['permissions'])} permissions")
    
    # Step 3: Create Demo Users
    print("\n3. Creating Demo Users...")
    demo_users = [
        {
            'username': 'admin',
            'email': 'admin@tijara.local',
            'password': 'admin123',
            'full_name': 'System Administrator',
            'roles': ['admin'],
            'is_superuser': True
        },
        {
            'username': 'alice_analyst',
            'email': 'alice@tijara.local',
            'password': 'password',
            'full_name': 'Alice Analyst',
            'roles': ['analyst'],
            'is_superuser': False
        },
        {
            'username': 'bob_trader',
            'email': 'bob@tijara.local',
            'password': 'password',
            'full_name': 'Bob Trader',
            'roles': ['trader'],
            'is_superuser': False
        },
        {
            'username': 'charlie_engineer',
            'email': 'charlie@tijara.local',
            'password': 'password',
            'full_name': 'Charlie Engineer',
            'roles': ['data_engineer'],
            'is_superuser': False
        },
        {
            'username': 'dave_viewer',
            'email': 'dave@tijara.local',
            'password': 'password',
            'full_name': 'Dave Viewer',
            'roles': ['viewer'],
            'is_superuser': False
        }
    ]
    
    for user_data in demo_users:
        # Create user
        password_hash = hash_password(user_data['password'])
        query = """
        MERGE (u:User {username: $username})
        SET u.email = $email,
            u.password_hash = $password_hash,
            u.full_name = $full_name,
            u.is_active = true,
            u.is_superuser = $is_superuser,
            u.created_at = $created_at
        RETURN id(u) as id
        """
        params = {
            'username': user_data['username'],
            'email': user_data['email'],
            'password_hash': password_hash,
            'full_name': user_data['full_name'],
            'is_superuser': user_data['is_superuser'],
            'created_at': datetime.now().isoformat()
        }
        result = graph.query(query, params)
        user_id = result.result_set[0][0] if result.result_set else None
        
        print(f"   ✓ Created user: {user_data['username']} ({user_data['full_name']})")
        
        # Assign roles
        for role_name in user_data['roles']:
            if role_name in role_map:
                link_query = """
                MATCH (u:User), (r:Role)
                WHERE id(u) = $user_id AND id(r) = $role_id
                MERGE (u)-[:HAS_ROLE]->(r)
                """
                graph.query(link_query, {
                    'user_id': user_id,
                    'role_id': role_map[role_name]
                })
        print(f"      Assigned roles: {', '.join(user_data['roles'])}")
    
    # Step 4: Verify Data
    print("\n4. Verifying RBAC Data...")
    
    # Count nodes separately
    users_result = graph.query("MATCH (u:User) RETURN count(u) as count")
    users_count = users_result.result_set[0][0] if users_result.result_set else 0
    
    roles_result = graph.query("MATCH (r:Role) RETURN count(r) as count")
    roles_count = roles_result.result_set[0][0] if roles_result.result_set else 0
    
    perms_result = graph.query("MATCH (p:Permission) RETURN count(p) as count")
    perms_count = perms_result.result_set[0][0] if perms_result.result_set else 0
    
    print(f"   ✓ Users: {users_count}")
    print(f"   ✓ Roles: {roles_count}")
    print(f"   ✓ Permissions: {perms_count}")
    
    # Verify relationships separately
    user_roles_result = graph.query("MATCH (:User)-[:HAS_ROLE]->(:Role) RETURN count(*) as count")
    user_roles = user_roles_result.result_set[0][0] if user_roles_result.result_set else 0
    
    role_perms_result = graph.query("MATCH (:Role)-[:HAS_PERMISSION]->(:Permission) RETURN count(*) as count")
    role_perms = role_perms_result.result_set[0][0] if role_perms_result.result_set else 0
    
    print(f"   ✓ User-Role assignments: {user_roles}")
    print(f"   ✓ Role-Permission assignments: {role_perms}")
    
    print("\n" + "="*60)
    print("RBAC Initialization Complete!")
    print("="*60)
    
    print("\nDemo User Credentials:")
    print("-" * 60)
    for user_data in demo_users:
        print(f"Username: {user_data['username']:20} Password: {user_data['password']:15} Role: {user_data['roles'][0]}")
    print("-" * 60)
    
    print("\n✅ RBAC system ready for use!")
    print("   You can now use these credentials to log in to the application.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Initialize RBAC data in FalkorDB')
    parser.add_argument('--graph', default=None, help='Graph name (default: from config)')
    args = parser.parse_args()
    
    init_rbac(args.graph)
