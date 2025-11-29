#!/usr/bin/env python3
"""
Add comprehensive data-level filtering examples for emma_restricted user.

This script demonstrates various types of data-level security:
1. Geography filtering (already exists - deny France)
2. Commodity filtering - deny access to Cotton
3. Property-level filtering - hide price and confidential fields
4. Relationship filtering - hide certain trade relationships
"""

from falkordb import FalkorDB

def main():
    # Connect to RBAC graph
    db = FalkorDB(host='localhost', port=6379)
    rbac_graph = db.select_graph('tijara_rbac')
    
    print("=" * 60)
    print("Adding Data-Level Filtering Examples for emma_restricted")
    print("=" * 60)
    
    # 1. Verify existing France geography filter
    print("\n1. Checking existing Geography filter (France)...")
    check_france = """
    MATCH (u:User {username: 'emma_restricted'})-[:HAS_ROLE]->(r:Role)-[:HAS_PERMISSION]->(p:Permission)
    WHERE p.name = 'node:deny:france'
    RETURN p.name, p.resource, p.node_label, p.property_filter
    """
    result = rbac_graph.query(check_france)
    if result.result_set:
        print(f"   ✓ France geography filter exists: {result.result_set[0]}")
    else:
        print("   ✗ France filter not found!")
    
    # 2. Add Commodity filter - deny Cotton
    print("\n2. Adding Commodity filter (deny Cotton)...")
    
    # Create permission for denying Cotton commodity
    create_cotton_permission = """
    MERGE (p:Permission {name: 'node:deny:cotton'})
    SET p.resource = 'node',
        p.action = 'read',
        p.grant_type = 'DENY',
        p.node_label = 'Commodity',
        p.property_filter = '{"name": "Cotton"}',
        p.description = 'Deny access to Cotton commodity data'
    RETURN p.name
    """
    result = rbac_graph.query(create_cotton_permission)
    print(f"   ✓ Created permission: {result.result_set[0][0] if result.result_set else 'node:deny:cotton'}")
    
    # Assign to restricted_analyst role
    assign_cotton = """
    MATCH (r:Role {name: 'restricted_analyst'})
    MATCH (p:Permission {name: 'node:deny:cotton'})
    MERGE (r)-[:HAS_PERMISSION]->(p)
    RETURN r.name, p.name
    """
    result = rbac_graph.query(assign_cotton)
    print(f"   ✓ Assigned to role: {result.result_set[0][0] if result.result_set else 'restricted_analyst'}")
    
    # 3. Add Property-level filter - hide price fields
    print("\n3. Adding Property filter (deny 'price' field)...")
    
    create_price_permission = """
    MERGE (p:Permission {name: 'property:deny:price'})
    SET p.resource = 'property',
        p.action = 'read',
        p.grant_type = 'DENY',
        p.node_label = 'BalanceSheet',
        p.property_name = 'price',
        p.description = 'Hide price information from balance sheets'
    RETURN p.name
    """
    result = rbac_graph.query(create_price_permission)
    print(f"   ✓ Created permission: {result.result_set[0][0] if result.result_set else 'property:deny:price'}")
    
    assign_price = """
    MATCH (r:Role {name: 'restricted_analyst'})
    MATCH (p:Permission {name: 'property:deny:price'})
    MERGE (r)-[:HAS_PERMISSION]->(p)
    RETURN r.name, p.name
    """
    result = rbac_graph.query(assign_price)
    print(f"   ✓ Assigned to role: restricted_analyst")
    
    # 4. Add another property filter - hide confidential_notes
    print("\n4. Adding Property filter (deny 'confidential_notes')...")
    
    create_notes_permission = """
    MERGE (p:Permission {name: 'property:deny:confidential'})
    SET p.resource = 'property',
        p.action = 'read',
        p.grant_type = 'DENY',
        p.node_label = 'BalanceSheet',
        p.property_name = 'confidential_notes',
        p.description = 'Hide confidential notes from balance sheets'
    RETURN p.name
    """
    result = rbac_graph.query(create_notes_permission)
    print(f"   ✓ Created permission: {result.result_set[0][0] if result.result_set else 'property:deny:confidential'}")
    
    assign_notes = """
    MATCH (r:Role {name: 'restricted_analyst'})
    MATCH (p:Permission {name: 'property:deny:confidential'})
    MERGE (r)-[:HAS_PERMISSION]->(p)
    RETURN r.name, p.name
    """
    result = rbac_graph.query(assign_notes)
    print(f"   ✓ Assigned to role: restricted_analyst")
    
    # 5. Verify all permissions for emma_restricted
    print("\n5. Verifying all permissions for emma_restricted...")
    verify = """
    MATCH (u:User {username: 'emma_restricted'})-[:HAS_ROLE]->(r:Role)-[:HAS_PERMISSION]->(p:Permission)
    RETURN p.name, p.resource, p.action, p.grant_type, 
           p.node_label, p.property_name, p.property_filter
    ORDER BY p.name
    """
    result = rbac_graph.query(verify)
    
    if result.result_set:
        print("\n   Permissions for emma_restricted:")
        for row in result.result_set:
            name, resource, action, grant_type, node_label, prop_name, prop_filter = row
            print(f"   • {name}")
            print(f"     - Resource: {resource}, Action: {action}, Grant: {grant_type}")
            if node_label:
                print(f"     - Node Label: {node_label}")
            if prop_name:
                print(f"     - Property: {prop_name}")
            if prop_filter:
                print(f"     - Filter: {prop_filter}")
    else:
        print("   ✗ No permissions found!")
    
    print("\n" + "=" * 60)
    print("Filtering Examples Added Successfully!")
    print("=" * 60)
    
    # Print test queries
    print("\n📝 Test Queries (run as emma_restricted):\n")
    print("1. Geography filtering (should NOT see France):")
    print('   MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name\n')
    
    print("2. Commodity filtering (should NOT see Cotton):")
    print('   MATCH (c:Commodity) WHERE c.level = 1 RETURN c.name ORDER BY c.name\n')
    
    print("3. Combined filter (no France, no Cotton):")
    print('   MATCH (g:Geography)-[:PRODUCES]->(c:Commodity)')
    print('   RETURN g.name, c.name LIMIT 10\n')
    
    print("4. Property filtering (price should be hidden):")
    print('   MATCH (b:BalanceSheet) RETURN b.product_name, b.price LIMIT 5\n')
    
    print("\n💡 Compare results with admin user to see the difference!")

if __name__ == "__main__":
    main()
