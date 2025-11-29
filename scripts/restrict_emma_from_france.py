#!/usr/bin/env python3
"""
Restrict emma user from accessing France-related data.

This script creates a DENY permission for France data and assigns it to emma.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from falkordb import FalkorDB


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


def create_france_deny_permission(graph):
    """
    Create a DENY permission that blocks access to France data.
    
    This uses DENY with a property_filter to block any Geography node
    where country = "France".
    """
    print("Creating France DENY permission...")
    
    permission_name = 'node:deny:france_data'
    
    # Check if permission already exists
    check_query = "MATCH (p:Permission {name: $name}) RETURN p"
    result = graph.query(check_query, {'name': permission_name})
    
    if result.result_set:
        print(f"  ✓ Permission '{permission_name}' already exists")
        return permission_name
    
    # Create DENY permission for France
    query = """
    CREATE (p:Permission {
        name: $name,
        resource: 'node',
        action: 'read',
        description: 'Deny access to France geography data',
        node_label: 'Geography',
        property_filter: '{"country": "France"}',
        grant_type: 'DENY',
        created_at: datetime()
    })
    RETURN p
    """
    
    graph.query(query, {'name': permission_name})
    print(f"  ✓ Created permission '{permission_name}'")
    print(f"    - Resource: node")
    print(f"    - Action: read")
    print(f"    - Node Label: Geography")
    print(f"    - Filter: country = 'France'")
    print(f"    - Grant Type: DENY")
    
    return permission_name


def create_no_france_role(graph, permission_name):
    """Create a role that blocks France data."""
    print("\nCreating 'no_france' role...")
    
    role_name = 'no_france'
    
    # Check if role exists
    check_query = "MATCH (r:Role {name: $name}) RETURN r"
    result = graph.query(check_query, {'name': role_name})
    
    if result.result_set:
        print(f"  ✓ Role '{role_name}' already exists")
    else:
        # Create role
        query = """
        CREATE (r:Role {
            name: $name,
            description: 'Role that blocks access to France data',
            is_system: false,
            created_at: datetime()
        })
        RETURN r
        """
        graph.query(query, {'name': role_name})
        print(f"  ✓ Created role '{role_name}'")
    
    # Link permission to role
    link_query = """
    MATCH (r:Role {name: $role_name})
    MATCH (p:Permission {name: $perm_name})
    MERGE (r)-[:HAS_PERMISSION]->(p)
    """
    graph.query(link_query, {'role_name': role_name, 'perm_name': permission_name})
    print(f"  ✓ Linked permission '{permission_name}' to role '{role_name}'")
    
    return role_name


def assign_role_to_emma(graph, role_name):
    """Assign the no_france role to emma user."""
    print("\nAssigning role to emma user...")
    
    username = 'emma'
    
    # Check if emma exists
    check_query = "MATCH (u:User {username: $username}) RETURN u"
    result = graph.query(check_query, {'username': username})
    
    if not result.result_set:
        print(f"  ⚠️  User '{username}' does not exist!")
        print(f"     You need to create the emma user first.")
        return False
    
    # Assign role to emma
    assign_query = """
    MATCH (u:User {username: $username})
    MATCH (r:Role {name: $role_name})
    MERGE (u)-[:HAS_ROLE]->(r)
    """
    graph.query(assign_query, {'username': username, 'role_name': role_name})
    print(f"  ✓ Assigned role '{role_name}' to user '{username}'")
    
    return True


def verify_emma_restrictions(graph):
    """Verify emma's permissions."""
    print("\nVerifying emma's restrictions...")
    
    query = """
    MATCH (u:User {username: 'emma'})-[:HAS_ROLE]->(r:Role)
          -[:HAS_PERMISSION]->(p:Permission)
    RETURN r.name as role, p.name as permission, p.grant_type as grant_type
    """
    result = graph.query(query)
    
    if not result.result_set:
        print("  ⚠️  No permissions found for emma")
        return
    
    print("  Emma's current permissions:")
    for row in result.result_set:
        role = row[0]
        permission = row[1]
        grant_type = row[2]
        icon = "🚫" if grant_type == "DENY" else "✓"
        print(f"    {icon} Role: {role} → {permission} ({grant_type})")


def main():
    """Main execution."""
    print("=" * 70)
    print("Restricting emma user from accessing France data")
    print("=" * 70)
    
    # Load config and connect
    config = load_config()
    graph = connect_to_rbac_graph(config)
    
    # Create France DENY permission
    permission_name = create_france_deny_permission(graph)
    
    # Create role with this permission
    role_name = create_no_france_role(graph, permission_name)
    
    # Assign role to emma
    success = assign_role_to_emma(graph, role_name)
    
    if success:
        # Verify
        verify_emma_restrictions(graph)
        
        print("\n" + "=" * 70)
        print("✅ Successfully restricted emma from France data!")
        print("=" * 70)
        print("\nHow it works:")
        print("  1. DENY permission blocks Geography nodes where country='France'")
        print("  2. 'no_france' role contains this DENY permission")
        print("  3. emma user has been assigned the 'no_france' role")
        print("  4. DENY rules take precedence over any GRANT rules")
        print("\nResult:")
        print("  - Emma can access all Geography data EXCEPT France")
        print("  - Queries will automatically filter out France nodes")
        print("  - This works for all repository methods (find_all, search, etc.)")
    else:
        print("\n" + "=" * 70)
        print("⚠️  Could not complete setup - emma user not found")
        print("=" * 70)
        print("\nTo create emma user first, run:")
        print("  python3 scripts/create_user.py --username emma")


if __name__ == "__main__":
    main()
