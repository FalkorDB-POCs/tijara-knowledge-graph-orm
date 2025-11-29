# Attribute-Based Access Control (ABAC) in Tijara RBAC

## Overview

The Tijara Knowledge Graph ORM RBAC system supports fine-grained **Attribute-Based Access Control (ABAC)** using FalkorDB ORM v1.2.0. This allows you to control access not just at the API level, but at the **node, edge, and property levels** based on specific attribute values.

## Permission Model

Each `Permission` entity supports the following attribute-based fields:

```python
@node("Permission")
class Permission:
    # Standard fields
    name: str                           # Unique permission identifier
    resource: str                       # "node", "edge", "property", or API resource
    action: str                         # "read", "write", "execute", "traverse", etc.
    description: str                    # Human-readable description
    grant_type: str                     # "GRANT" or "DENY" (DENY takes precedence)
    
    # Attribute-based access control fields
    node_label: Optional[str]           # Specific node label (e.g., "Geography", "Commodity")
    edge_type: Optional[str]            # Specific relationship type (e.g., "TRADES_WITH")
    property_name: Optional[str]        # Specific property name for property-level security
    property_filter: Optional[str]      # JSON filter for property values
    attribute_conditions: Optional[str] # Cypher WHERE clause for complex conditions
```

## Permission Types

### 1. Node-Level Permissions

Control access to specific node types based on labels and attributes.

#### Example: Read All Geography Nodes
```python
{
    "name": "node:read:geography",
    "resource": "node",
    "action": "read",
    "node_label": "Geography",
    "grant_type": "GRANT"
}
```

#### Example: Read Only French Geography Nodes
```python
{
    "name": "node:read:france_only",
    "resource": "node",
    "action": "read",
    "node_label": "Geography",
    "property_filter": '{"country": "France"}',
    "grant_type": "GRANT"
}
```

#### Example: Read Recent Production Data Only
```python
{
    "name": "node:read:recent_data",
    "resource": "node",
    "action": "read",
    "node_label": "Production",
    "attribute_conditions": "n.year >= 2024",
    "grant_type": "GRANT"
}
```

### 2. Edge-Level Permissions

Control access to relationships and traversal patterns.

#### Example: Read All Trade Relationships
```python
{
    "name": "edge:read:trades",
    "resource": "edge",
    "action": "read",
    "edge_type": "TRADES_WITH",
    "grant_type": "GRANT"
}
```

#### Example: Read Only Wheat Trades
```python
{
    "name": "edge:read:wheat_trades",
    "resource": "edge",
    "action": "read",
    "edge_type": "TRADES_WITH",
    "property_filter": '{"commodity": "Wheat"}',
    "grant_type": "GRANT"
}
```

#### Example: Read Trades Between Specific Countries
```python
{
    "name": "edge:read:us_france_only",
    "resource": "edge",
    "action": "read",
    "edge_type": "TRADES_WITH",
    "attribute_conditions": "(startNode(r).country = 'USA' AND endNode(r).country = 'France') OR (startNode(r).country = 'France' AND endNode(r).country = 'USA')",
    "grant_type": "GRANT"
}
```

### 3. Property-Level Permissions

Control access to specific properties on nodes or edges.

#### Example: Deny Access to Sensitive Property
```python
{
    "name": "property:deny:sensitive",
    "resource": "property",
    "action": "read",
    "property_name": "confidential_notes",
    "grant_type": "DENY"
}
```

#### Example: Deny Access to Price Information
```python
{
    "name": "property:deny:price",
    "resource": "property",
    "action": "read",
    "property_name": "price",
    "grant_type": "DENY"
}
```

### 4. Complex Conditional Permissions

Use Cypher WHERE clauses for advanced filtering.

#### Example: High-Value Trades Only
```python
{
    "name": "node:read:high_value_trades",
    "resource": "node",
    "action": "read",
    "node_label": "Trade",
    "attribute_conditions": "n.value > 1000000",
    "grant_type": "GRANT"
}
```

## Grant vs Deny

The system supports both **GRANT** and **DENY** permissions:

- **GRANT**: Explicitly allows access to matching entities
- **DENY**: Explicitly denies access to matching entities
- **DENY takes precedence**: If any DENY permission matches, access is denied regardless of GRANT permissions

### Example: Role with Mixed Permissions
```python
# Trader role can read all trades
"edge:read:trades" → GRANT access to TRADES_WITH edges

# But deny access to price property
"property:deny:price" → DENY access to price property

# Result: Trader can see trades but not their prices
```

## Query Rewriting (ORM 1.2.0 Feature)

When a user with attribute-based permissions queries the graph, the ORM automatically rewrites queries to enforce access control:

### Original Query
```cypher
MATCH (g:Geography)-[t:TRADES_WITH]->(g2:Geography)
RETURN g, t, g2
```

### Rewritten Query (for user with `node:read:france_only`)
```cypher
MATCH (g:Geography)-[t:TRADES_WITH]->(g2:Geography)
WHERE g.country = 'France' OR g2.country = 'France'
RETURN g, t, g2
```

### Property Filtering
If a user has `property:deny:price`:

```cypher
// Original
RETURN g.name, g.country, g.price

// Rewritten
RETURN g.name, g.country, NULL as price
```

## Use Cases

### Use Case 1: Regional Data Analyst

**Requirement**: Analyst should only see data for their region (France).

**Permissions**:
```python
role_permissions = [
    "analytics:read",
    "analytics:execute",
    "node:read:france_only",        # Only French geography
    "edge:read:trades",             # All trade relationships
    "discovery:read"
]
```

### Use Case 2: Commodity-Specific Trader

**Requirement**: Trader only deals with wheat and should only see wheat-related data.

**Permissions**:
```python
role_permissions = [
    "analytics:read",
    {
        "name": "node:read:wheat_commodity",
        "node_label": "Commodity",
        "property_filter": '{"name": "Wheat"}',
        "grant_type": "GRANT"
    },
    {
        "name": "edge:read:wheat_trades",
        "edge_type": "TRADES_WITH",
        "property_filter": '{"commodity": "Wheat"}',
        "grant_type": "GRANT"
    }
]
```

### Use Case 3: Senior Analyst with Restrictions

**Requirement**: Can see all data except confidential notes and high-value trades.

**Permissions**:
```python
role_permissions = [
    "analytics:read",
    "analytics:execute",
    "node:read:geography",
    "node:read:commodity",
    "edge:read:trades",
    "property:deny:sensitive",      # DENY confidential_notes
    {
        "name": "node:deny:high_value",
        "node_label": "Trade",
        "attribute_conditions": "n.value > 10000000",
        "grant_type": "DENY"         # DENY trades over 10M
    }
]
```

## Implementation in ORM 1.2.0

### SecurityContext Class

The `SecurityContext` class manages user permissions and query rewriting:

```python
class SecurityContext:
    def __init__(self, user: User, graph):
        self.user = user
        self.effective_permissions = self._load_permissions()
    
    def can_access_node(self, node_label: str, node_properties: dict) -> bool:
        """Check if user can access a specific node"""
        for perm in self.effective_permissions:
            if perm.resource == 'node' and perm.node_label == node_label:
                if perm.grant_type == 'DENY':
                    if self._matches_filter(node_properties, perm):
                        return False
                elif perm.grant_type == 'GRANT':
                    if self._matches_filter(node_properties, perm):
                        return True
        return False
    
    def rewrite_query(self, cypher: str) -> str:
        """Rewrite Cypher query to enforce permissions"""
        # Add WHERE clauses based on attribute conditions
        # Filter properties based on property-level permissions
        # Return modified query
```

### Secure Repository

The `SecureRepository` automatically applies permissions:

```python
class SecureRepository(Repository[T]):
    def __init__(self, graph, entity_class, security_context):
        super().__init__(graph, entity_class)
        self.security_context = security_context
    
    def find_all(self) -> List[T]:
        # Apply node-level filters
        # Filter properties
        # Return filtered results
```

## Best Practices

1. **Start with Role-Level Permissions**: Use standard roles (admin, analyst, trader) first
2. **Add Attribute-Based When Needed**: Only add fine-grained permissions for specific use cases
3. **Use DENY Sparingly**: DENYs add complexity; prefer not granting access
4. **Test Permissions Thoroughly**: Verify both positive and negative cases
5. **Document Custom Permissions**: Always add clear descriptions
6. **Monitor Performance**: Complex attribute conditions may impact query performance
7. **Cache Permission Checks**: Use `SecurityContext` to cache evaluated permissions

## Performance Considerations

- **Query Rewriting Overhead**: ~5-10ms per query
- **Permission Evaluation**: O(n) where n = number of permissions
- **Caching**: Permission checks are cached in `SecurityContext`
- **Index Recommendations**: Add indexes on filtered properties (e.g., `country`, `year`)

## Future Enhancements

1. **Dynamic Policies**: Evaluate permissions based on graph relationships
2. **Row-Level Security**: Filter entities based on user context
3. **Temporal Permissions**: Time-based access control
4. **Audit Logging**: Track all permission checks and denials
5. **Permission Inheritance**: Hierarchical permission resolution

## API Integration

The admin panel allows creating attribute-based permissions through the UI:

1. Navigate to **Admin Panel** → **Permissions** tab
2. Create a new permission with:
   - Name: `node:read:my_custom_filter`
   - Resource: `node`
   - Action: `read`
   - Node Label: `Geography`
   - Property Filter: `{"country": "Germany"}`
   - Grant Type: `GRANT`

3. Assign the permission to a role
4. Users with that role will only see German geography nodes

## Examples in Practice

See `examples/security/attribute_based_permissions_demo.py` for runnable examples demonstrating:
- Node-level filtering
- Edge-level filtering
- Property-level security
- Complex conditional access
- GRANT vs DENY precedence
