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


def init_rbac(graph_name='ldc_graph'):
    """Initialize RBAC data in the graph"""
    
    # Connect to FalkorDB
    print(f"Connecting to FalkorDB graph: {graph_name}")
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
            p.created_at = $created_at
        RETURN id(p) as id
        """
        params = {
            'name': perm_name,
            'resource': perm_def['resource'],
            'action': perm_def['action'],
            'description': perm_def['description'],
            'created_at': datetime.now().isoformat()
        }
        result = graph.query(query, params)
        perm_id = result.result_set[0][0] if result.result_set else None
        permission_map[perm_name] = perm_id
        print(f"   ✓ Created permission: {perm_name}")
    
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
    
    # Count nodes
    count_query = """
    MATCH (u:User) RETURN count(u) as users
    UNION ALL
    MATCH (r:Role) RETURN count(r) as roles
    UNION ALL
    MATCH (p:Permission) RETURN count(p) as permissions
    """
    result = graph.query(count_query)
    users_count = result.result_set[0][0] if len(result.result_set) > 0 else 0
    roles_count = result.result_set[1][0] if len(result.result_set) > 1 else 0
    perms_count = result.result_set[2][0] if len(result.result_set) > 2 else 0
    
    print(f"   ✓ Users: {users_count}")
    print(f"   ✓ Roles: {roles_count}")
    print(f"   ✓ Permissions: {perms_count}")
    
    # Verify relationships
    rel_query = """
    MATCH (:User)-[:HAS_ROLE]->(:Role) RETURN count(*) as user_roles
    UNION ALL
    MATCH (:Role)-[:HAS_PERMISSION]->(:Permission) RETURN count(*) as role_perms
    """
    result = graph.query(rel_query)
    user_roles = result.result_set[0][0] if len(result.result_set) > 0 else 0
    role_perms = result.result_set[1][0] if len(result.result_set) > 1 else 0
    
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
    parser.add_argument('--graph', default='ldc_graph', help='Graph name (default: ldc_graph)')
    args = parser.parse_args()
    
    init_rbac(args.graph)
