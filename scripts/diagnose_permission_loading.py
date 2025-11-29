#!/usr/bin/env python3
"""
Diagnostic script to test permission loading performance.

This helps identify if permission loading is causing slowdowns or hangs.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from falkordb import FalkorDB
from src.security.context import SecurityContext


def load_config():
    """Load configuration."""
    config_path = project_root / 'config' / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def connect_to_rbac_graph(config):
    """Connect to RBAC graph."""
    print("Connecting to RBAC graph...")
    start = time.time()
    
    db = FalkorDB(
        host=config['rbac'].get('host', 'localhost'),
        port=config['rbac'].get('port', 6379)
    )
    graph = db.select_graph(config['rbac']['graph_name'])
    
    elapsed = time.time() - start
    print(f"  ✓ Connected in {elapsed:.3f}s\n")
    
    return graph


def test_permission_query(graph, username):
    """Test permission loading query directly."""
    print(f"Testing permission query for user '{username}'...")
    start = time.time()
    
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
        
        result = graph.query(query, {'username': username})
        
        elapsed = time.time() - start
        
        if result.result_set:
            print(f"  ✓ Query completed in {elapsed:.3f}s")
            print(f"  ✓ Found {len(result.result_set)} permissions")
            
            for row in result.result_set:
                print(f"    - {row[0]} ({row[8] or 'GRANT'})")
            
            return True, elapsed
        else:
            print(f"  ⚠️  Query completed in {elapsed:.3f}s but found no permissions")
            print(f"     User '{username}' may not exist or has no roles")
            return False, elapsed
            
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ✗ Query FAILED after {elapsed:.3f}s")
        print(f"    Error: {e}")
        import traceback
        traceback.print_exc()
        return False, elapsed


def test_security_context_creation(graph, username):
    """Test SecurityContext creation."""
    print(f"\nTesting SecurityContext creation for '{username}'...")
    start = time.time()
    
    try:
        user_data = {
            'username': username,
            'sub': username,
            'is_superuser': False
        }
        
        context = SecurityContext(user_data=user_data, graph=graph)
        
        elapsed = time.time() - start
        print(f"  ✓ SecurityContext created in {elapsed:.3f}s")
        
        # Test lazy loading by accessing filters
        print(f"  Testing lazy loading of permissions...")
        filter_start = time.time()
        
        row_filters = context.get_row_filters('Geography', 'read')
        denied_props = context.get_denied_properties('Geography', 'read')
        
        filter_elapsed = time.time() - filter_start
        
        print(f"  ✓ Filters loaded in {filter_elapsed:.3f}s")
        print(f"    - Row filters: {len(row_filters)}")
        print(f"    - Denied properties: {len(denied_props)}")
        
        if row_filters:
            print(f"    Row filter examples:")
            for f in row_filters[:3]:
                print(f"      - {f}")
        
        if denied_props:
            print(f"    Denied properties: {denied_props}")
        
        return True, elapsed + filter_elapsed
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ✗ SecurityContext creation FAILED after {elapsed:.3f}s")
        print(f"    Error: {e}")
        import traceback
        traceback.print_exc()
        return False, elapsed


def test_user_exists(graph, username):
    """Check if user exists."""
    print(f"Checking if user '{username}' exists...")
    
    try:
        query = "MATCH (u:User {username: $username}) RETURN u.username, u.is_superuser"
        result = graph.query(query, {'username': username})
        
        if result.result_set:
            row = result.result_set[0]
            username_val = row[0]
            is_superuser = row[1]
            print(f"  ✓ User exists")
            print(f"    - Username: {username_val}")
            print(f"    - Superuser: {is_superuser}")
            return True
        else:
            print(f"  ✗ User '{username}' does NOT exist")
            return False
            
    except Exception as e:
        print(f"  ✗ Error checking user: {e}")
        return False


def test_user_roles(graph, username):
    """Check user's roles."""
    print(f"\nChecking roles for user '{username}'...")
    
    try:
        query = """
        MATCH (u:User {username: $username})-[:HAS_ROLE]->(r:Role)
        RETURN r.name, r.description
        """
        result = graph.query(query, {'username': username})
        
        if result.result_set:
            print(f"  ✓ Found {len(result.result_set)} roles:")
            for row in result.result_set:
                print(f"    - {row[0]}: {row[1]}")
            return True
        else:
            print(f"  ⚠️  User has NO roles assigned")
            return False
            
    except Exception as e:
        print(f"  ✗ Error checking roles: {e}")
        return False


def main():
    """Main diagnostic."""
    username = sys.argv[1] if len(sys.argv) > 1 else 'emma'
    
    print("=" * 70)
    print(f"Permission Loading Diagnostics for user: {username}")
    print("=" * 70)
    print()
    
    # Load config and connect
    config = load_config()
    graph = connect_to_rbac_graph(config)
    
    # Test 1: User exists
    user_exists = test_user_exists(graph, username)
    print()
    
    if not user_exists:
        print("=" * 70)
        print("⚠️  Cannot continue - user does not exist")
        print("=" * 70)
        print(f"\nCreate user first:")
        print(f"  python3 scripts/setup_example_permissions.py")
        return
    
    # Test 2: User roles
    has_roles = test_user_roles(graph, username)
    print()
    
    # Test 3: Direct permission query
    perms_ok, query_time = test_permission_query(graph, username)
    print()
    
    # Test 4: SecurityContext creation
    context_ok, context_time = test_security_context_creation(graph, username)
    print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"User exists:             {'✓' if user_exists else '✗'}")
    print(f"User has roles:          {'✓' if has_roles else '⚠️ No roles'}")
    print(f"Permission query works:  {'✓' if perms_ok else '✗'}")
    print(f"  - Query time:          {query_time:.3f}s")
    print(f"SecurityContext works:   {'✓' if context_ok else '✗'}")
    print(f"  - Total time:          {context_time:.3f}s")
    print()
    
    if query_time > 2.0:
        print("⚠️  WARNING: Permission query is SLOW (>2s)")
        print("   Consider:")
        print("   - Creating indexes on User.username, Role.name")
        print("   - Reducing number of permissions")
        print("   - Checking graph performance")
    elif query_time > 0.5:
        print("⚠️  Permission query is somewhat slow (>0.5s)")
        print("   This may cause noticeable delays")
    else:
        print("✓ Performance looks good!")
    
    print()
    print("If the system hangs, check:")
    print("  1. Is FalkorDB running and accessible?")
    print("  2. Is the RBAC graph name correct in config?")
    print("  3. Are there circular relationship patterns?")
    print("  4. Is the network connection stable?")


if __name__ == "__main__":
    main()
