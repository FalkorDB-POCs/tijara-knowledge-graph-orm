# Data-Level Security Filtering

Comprehensive data-level access control using FalkorDB ORM 1.2.0's QueryRewriter capabilities.

## Overview

The Tijara Knowledge Graph implements fine-grained data access control at three levels:
- **Row-level filtering**: Users see only specific nodes (e.g., only French geography data)
- **Property-level filtering**: Sensitive properties are redacted (e.g., price, confidential notes)
- **Relationship-level filtering**: Certain edges are hidden (e.g., specific trade flows)

## Architecture

### Components

1. **PolicyManager** (`src/security/policy_manager.py`)
   - Loads Permission entities from graph
   - Converts to PolicyRules for QueryRewriter
   - Handles GRANT vs DENY precedence

2. **Enhanced SecurityContext** (`src/security/context.py`)
   - Provides `get_row_filters()`, `get_denied_properties()`, `get_edge_filters()`
   - Caches permission lookups per entity type
   - Queries permissions from graph based on user roles

3. **EnhancedQueryRewriter** (`src/security/query_rewriter_enhanced.py`)
   - Rewrites Cypher queries to inject WHERE clauses
   - Removes denied properties from RETURN clauses
   - Adds relationship type restrictions

4. **SecureRepositoryWrapper** (`src/repositories/secure_repository_factory.py`)
   - Wraps repositories with security filtering
   - Intercepts query execution
   - Filters results post-query

5. **ORMKnowledgeGraph Integration** (`src/core/orm_knowledge_graph.py`)
   - Accepts SecurityContext parameter
   - Initializes SecurityPolicy
   - Wraps all repositories with secure versions

## Permission Configuration

### Permission Entity Fields

```python
@node("Permission")
class Permission:
    name: str                    # e.g., "node:read:france_only"
    resource: str                # "node", "edge", "property"
    action: str                  # "read", "write", "execute"
    node_label: Optional[str]    # e.g., "Geography", "Commodity"
    edge_type: Optional[str]     # e.g., "TRADES_WITH", "PRODUCES"
    property_name: Optional[str] # e.g., "price", "confidential_notes"
    property_filter: Optional[str]      # JSON: {"country": "France"}
    attribute_conditions: Optional[str] # Cypher: "n.value > 1000000"
    grant_type: str              # "GRANT" or "DENY"
```

### Permission Examples

#### Row-Level Filtering (Geography)
```python
# User sees only French geography nodes
Permission(
    name="node:read:france_only",
    resource="node",
    action="read",
    node_label="Geography",
    property_filter='{"country": "France"}',
    grant_type="GRANT"
)
```

#### Property-Level Filtering (Price Denial)
```python
# User cannot see price property
Permission(
    name="property:deny:price",
    resource="property",
    action="read",
    property_name="price",
    grant_type="DENY"
)
```

#### Attribute-Based Filtering (High-Value Trades)
```python
# User sees only trades above $1M
Permission(
    name="node:read:high_value_trades",
    resource="node",
    action="read",
    node_label="Trade",
    attribute_conditions="n.value > 1000000",
    grant_type="GRANT"
)
```

#### Edge-Level Filtering (Wheat Trades Only)
```python
# User sees only wheat trading relationships
Permission(
    name="edge:read:wheat_trades",
    resource="edge",
    action="read",
    edge_type="TRADES_WITH",
    property_filter='{"commodity": "Wheat"}',
    grant_type="GRANT"
)
```

## Query Rewriting Examples

### Original Query
```cypher
MATCH (g:Geography) WHERE g.level = 0 RETURN g ORDER BY g.name
```

### With Row-Level Filter (France Only)
```cypher
MATCH (g:Geography) WHERE g.level = 0 AND (g.country = 'France') RETURN g ORDER BY g.name
```

### With Property Filter (Price Denied)
Original:
```cypher
MATCH (bs:BalanceSheet) RETURN bs.product_name, bs.price, bs.season
```

Rewritten:
```cypher
MATCH (bs:BalanceSheet) RETURN bs.product_name, bs.season
```

Post-query filtering also sets `bs.price = None` on returned entities.

## Usage

### API Integration

```python
from fastapi import Depends
from src.security.context import SecurityContext
from api.dependencies import get_security_context

@app.get("/geographies")
async def get_geographies(
    security_context: SecurityContext = Depends(get_security_context)
):
    # Create knowledge graph with security context
    kg = ORMKnowledgeGraph(config, security_context=security_context)
    
    # Queries are automatically filtered based on user permissions
    countries = kg.geography_repo.find_all_countries()
    
    return {"countries": countries}
```

### Direct Usage

```python
from src.security.context import SecurityContext
from src.core.orm_knowledge_graph import ORMKnowledgeGraph

# Without security (admin)
kg = ORMKnowledgeGraph(config)
all_countries = kg.geography_repo.find_all()  # Returns all

# With security (restricted user)
user_data = {'username': 'analyst1', 'roles': ['french_analyst']}
context = SecurityContext(user_data=user_data, graph=graph)
kg_secure = ORMKnowledgeGraph(config, security_context=context)
filtered_countries = kg_secure.geography_repo.find_all()  # Returns only France
```

## DENY vs GRANT Precedence

**DENY always takes precedence over GRANT.**

If a user has both:
- `GRANT` permission for `node:read:geography`
- `DENY` permission for `property:read:confidential_notes`

Result: User can read Geography nodes but `confidential_notes` property will be `None`.

## Performance Considerations

### Caching
- **SecurityContext**: Caches permission lookups per entity type
- **PolicyManager**: Caches loaded PolicyRules
- **QueryRewriter**: Reuses parsed query structures

### Best Practices
1. **Create indexes** on filtered properties (e.g., `country`, `level`)
2. **Limit permission complexity**: Simple filters perform better than complex attribute_conditions
3. **Use property filtering sparingly**: Post-query property filtering is less efficient than row filtering
4. **Test at scale**: Benchmark with representative data volumes

### Performance Impact
Expected overhead with filtering enabled:
- Row-level filtering: ~5% (WHERE clause injection)
- Property filtering: ~10% (post-query processing)
- Combined: ~15%

## Security Model

### Authentication Flow
1. User authenticates with JWT token
2. Token contains username, user_id, is_superuser
3. FastAPI dependency extracts user from token
4. SecurityContext created with user data + graph connection
5. SecurityContext queries User → Role → Permission chain
6. Permissions cached for request duration

### Query Execution Flow
1. User calls `repo.find_all_countries()`
2. Repository generates base Cypher query
3. SecureRepositoryWrapper intercepts
4. EnhancedQueryRewriter modifies query:
   - Parses MATCH, WHERE, RETURN clauses
   - Injects row filters into WHERE
   - Removes denied properties from RETURN
5. Modified query executed
6. Results post-processed to set denied properties to None
7. Filtered results returned

## Limitations

### Complex Queries
Query rewriting works best with simple patterns:
- Single MATCH clause
- Simple WHERE conditions
- Direct RETURN of nodes/properties

Complex patterns may not be fully supported:
- UNION queries
- Multiple OPTIONAL MATCH
- Subqueries
- Variable-length paths

**Workaround**: Use custom `@query` methods with manual security checks for complex cases.

### Relationship Traversal
Edge filtering applies to explicit relationship patterns but not:
- Variable-length paths: `-[*]->` 
- Shortest paths: `shortestPath()`

### Aggregations
Property filtering doesn't apply to aggregations:
```cypher
RETURN count(bs.price)  # Not filtered even if price is denied
```

## Testing

### Unit Tests
```bash
pytest tests/security/test_policy_manager.py -v
pytest tests/security/test_query_rewriter_enhanced.py -v
```

### Integration Tests
```bash
pytest tests/security/test_security_integration.py -v
```

## Troubleshooting

### "Permission denied" errors
**Symptom**: 403 Forbidden on API calls

**Solution**: Check user's roles and permissions in graph:
```cypher
MATCH (u:User {username: 'analyst1'})-[:HAS_ROLE]->(r:Role)-[:HAS_PERMISSION]->(p:Permission)
RETURN r.name, collect(p.name)
```

### Empty results for queries
**Symptom**: Queries return no results even though data exists

**Solution**: Check row-level filters:
```python
context = SecurityContext(user_data={'username': 'analyst1'}, graph=graph)
filters = context.get_row_filters('Geography', 'read')
print(f"Active filters: {filters}")
```

### Properties showing as None
**Symptom**: Properties unexpectedly None

**Solution**: Check denied properties:
```python
denied = context.get_denied_properties('BalanceSheet', 'read')
print(f"Denied properties: {denied}")
```

## Future Enhancements

1. **Whitelist mode**: Only show explicitly granted properties
2. **Dynamic user context**: Inject user-specific parameters (e.g., `$user_country`)
3. **Audit logging**: Track all security-filtered queries
4. **Advanced query parsing**: Support more complex Cypher patterns
5. **Performance optimization**: Query result caching with security keys

## References

- [FalkorDB ORM Documentation](https://github.com/FalkorDB/falkordb-py-orm)
- [falkordb-orm v1.2.0 Security Module](https://github.com/FalkorDB/falkordb-py-orm/blob/main/docs/security.md)
- [RBAC Implementation Guide](../RBAC_IMPLEMENTATION_PLAN.md)
