#!/usr/bin/env python3
"""
Fix emma_restricted France DENY permission filter.

The current filter checks country="France" but the France Geography node
actually has name="France" and country=None. This script updates the filter.
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


def main():
    """Main execution."""
    print("=" * 70)
    print("Fixing emma_restricted France DENY permission filter")
    print("=" * 70)
    
    # Load config and connect
    config = load_config()
    graph = connect_to_rbac_graph(config)
    
    # Check current permission
    print("\n1. Current DENY permission:")
    result = graph.query('''
    MATCH (p:Permission {name: 'node:deny:france'})
    RETURN p.name, p.property_filter, p.description
    ''')
    
    if not result.result_set:
        print("   ❌ Permission 'node:deny:france' not found!")
        print("   Run: python3 scripts/setup_example_permissions.py")
        return
    
    name, old_filter, desc = result.result_set[0]
    print(f"   Name: {name}")
    print(f"   Description: {desc}")
    print(f"   Current Filter: {old_filter}")
    
    # Update the filter
    print("\n2. Updating filter...")
    new_filter = '{"name": "France"}'
    
    update_query = '''
    MATCH (p:Permission {name: 'node:deny:france'})
    SET p.property_filter = $new_filter,
        p.description = 'Deny access to France geography node'
    RETURN p.property_filter
    '''
    
    result = graph.query(update_query, {'new_filter': new_filter})
    
    if result.result_set:
        updated_filter = result.result_set[0][0]
        print(f"   ✅ Updated filter to: {updated_filter}")
    else:
        print("   ❌ Failed to update filter")
        return
    
    # Verify
    print("\n3. Verifying update:")
    result = graph.query('''
    MATCH (u:User {username: 'emma_restricted'})-[:HAS_ROLE]->(r:Role)
          -[:HAS_PERMISSION]->(p:Permission {name: 'node:deny:france'})
    RETURN p.name, p.property_filter, p.node_label
    ''')
    
    if result.result_set:
        perm_name, filter_str, label = result.result_set[0]
        print(f"   Permission: {perm_name}")
        print(f"   Node Label: {label}")
        print(f"   Filter: {filter_str}")
        print()
        print("   ✅ emma_restricted will now be blocked from Geography nodes")
        print("      where name='France'")
    else:
        print("   ❌ Could not verify update")
        return
    
    print("\n" + "=" * 70)
    print("✅ Successfully updated France DENY filter!")
    print("=" * 70)
    print("\nWhat changed:")
    print(f"  Old filter: {old_filter}")
    print(f"  New filter: {new_filter}")
    print("\nWhy:")
    print("  The France Geography node has:")
    print("    - name: 'France'")
    print("    - country: None")
    print("  So the filter must check 'name' instead of 'country'")
    print("\nNext steps:")
    print("  1. Start the API server: python3 -m uvicorn api.main:app --port 8000")
    print("  2. Login as emma_restricted (see credentials in setup script output)")
    print("  3. Try to query Geography data - France should be filtered out")


if __name__ == "__main__":
    main()
