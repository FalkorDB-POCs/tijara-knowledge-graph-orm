# Restricting Emma from France Data - Demo

## Overview

**Yes!** The system can now restrict the "emma" user from accessing France-related data using the data-level query filtering implementation.

## How It Works

### 1. DENY Permission
The system creates a DENY permission that blocks access to Geography nodes where `country = "France"`:

```python
Permission(
    name='node:deny:france_data',
    resource='node',
    action='read',
    node_label='Geography',
    property_filter='{"country": "France"}',
    grant_type='DENY'
)
```

### 2. Role Assignment
- A `no_france` role is created with this DENY permission
- The `emma` user is assigned the `no_france` role

### 3. Automatic Filtering
- When emma queries Geography data, the QueryRewriter automatically filters results
- **DENY rules take precedence** over any GRANT rules
- Emma sees all Geography data EXCEPT France

## Setup

### Option 1: Run the Script (Automated)

```bash
# Run the restriction script
python3 scripts/restrict_emma_from_france.py
```

**Expected Output:**
```
======================================================================
Restricting emma user from accessing France data
======================================================================
Creating France DENY permission...
  ✓ Created permission 'node:deny:france_data'
    - Resource: node
    - Action: read
    - Node Label: Geography
    - Filter: country = 'France'
    - Grant Type: DENY

Creating 'no_france' role...
  ✓ Created role 'no_france'
  ✓ Linked permission 'node:deny:france_data' to role 'no_france'

Assigning role to emma user...
  ✓ Assigned role 'no_france' to user 'emma'

Verifying emma's restrictions...
  Emma's current permissions:
    🚫 Role: no_france → node:deny:france_data (DENY)

======================================================================
✅ Successfully restricted emma from France data!
======================================================================
```

### Option 2: Manual Setup (Cypher Queries)

If you prefer to set this up manually:

```cypher
-- 1. Create the DENY permission
CREATE (p:Permission {
    name: 'node:deny:france_data',
    resource: 'node',
    action: 'read',
    description: 'Deny access to France geography data',
    node_label: 'Geography',
    property_filter: '{"country": "France"}',
    grant_type: 'DENY',
    created_at: datetime()
})

-- 2. Create the role
CREATE (r:Role {
    name: 'no_france',
    description: 'Role that blocks access to France data',
    is_system: false,
    created_at: datetime()
})

-- 3. Link permission to role
MATCH (r:Role {name: 'no_france'})
MATCH (p:Permission {name: 'node:deny:france_data'})
MERGE (r)-[:HAS_PERMISSION]->(p)

-- 4. Assign role to emma
MATCH (u:User {username: 'emma'})
MATCH (r:Role {name: 'no_france'})
MERGE (u)-[:HAS_ROLE]->(r)
```

## Testing

### Test 1: Admin User (No Restrictions)

```python
from src.security.context import SecurityContext
from src.core.orm_knowledge_graph import ORMKnowledgeGraph

# Admin sees everything
admin_context = SecurityContext(user_data={
    'username': 'admin',
    'is_superuser': True
})
kg_admin = ORMKnowledgeGraph(config, security_context=admin_context)

countries = kg_admin.geography_repo.find_all_countries()
print(f"Admin sees {len(countries)} countries")
# Output: Admin sees 50 countries (including France)
```

### Test 2: Emma User (France Blocked)

```python
# Emma cannot see France
emma_context = SecurityContext(user_data={
    'username': 'emma',
    'roles': ['no_france']
}, graph=rbac_graph)

kg_emma = ORMKnowledgeGraph(config, security_context=emma_context)

countries = kg_emma.geography_repo.find_all_countries()
print(f"Emma sees {len(countries)} countries")
# Output: Emma sees 49 countries (France filtered out)

# Try to find France specifically
france = kg_emma.geography_repo.find_by_name("France")
print(f"France result: {france}")
# Output: France result: None
```

### Test 3: API Integration

```bash
# Login as emma
curl -X POST http://localhost:8000/auth/login \
  -d "username=emma&password=<password>"

# Get JWT token from response
TOKEN="<jwt_token>"

# Query geographies (France will be filtered out)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/geographies

# Result: List of countries WITHOUT France
```

## Query Rewriting Example

### Original Query
```cypher
MATCH (g:Geography) 
WHERE g.level = 0 
RETURN g 
ORDER BY g.name
```

### Rewritten Query (for emma)
```cypher
MATCH (g:Geography) 
WHERE g.level = 0 
  AND NOT (g.country = 'France')  -- Added by QueryRewriter
RETURN g 
ORDER BY g.name
```

## How the Filtering Works

1. **SecurityContext Initialization**
   - Emma logs in → JWT token created
   - API extracts user data from token
   - SecurityContext created with emma's roles

2. **Permission Loading**
   ```python
   # SecurityContext queries:
   MATCH (u:User {username: 'emma'})-[:HAS_ROLE]->(r:Role)
         -[:HAS_PERMISSION]->(p:Permission)
   WHERE p.grant_type = 'DENY' AND p.node_label = 'Geography'
   RETURN p
   ```

3. **Query Rewriting**
   - ORMKnowledgeGraph creates repositories with SecurityContext
   - Repository methods generate base Cypher queries
   - SecureRepositoryWrapper intercepts queries
   - EnhancedQueryRewriter adds DENY filters:
     ```python
     # Adds: NOT (g.country = 'France')
     ```

4. **Automatic Filtering**
   - Modified query executed
   - France nodes excluded from results
   - Emma sees only non-France Geography data

## DENY vs GRANT Precedence

**Important**: DENY always wins!

Even if emma has a GRANT permission for Geography:

```python
# Emma has both:
- GRANT: node:read:geography (allows all Geography)
- DENY: node:deny:france_data (blocks France)

# Result: Emma can read Geography BUT NOT France
# DENY takes precedence!
```

## Verification

### Check Emma's Permissions
```cypher
MATCH (u:User {username: 'emma'})-[:HAS_ROLE]->(r:Role)
      -[:HAS_PERMISSION]->(p:Permission)
RETURN r.name as role, 
       p.name as permission, 
       p.grant_type as type,
       p.node_label as applies_to
```

**Expected Result:**
```
role        | permission              | type  | applies_to
------------|-------------------------|-------|------------
no_france   | node:deny:france_data   | DENY  | Geography
```

### Test Query Filtering
```python
# Get row filters for emma
emma_context.get_row_filters('Geography', 'read')
# Returns: ["NOT (country = 'France')"]  # or similar

# Check if France is denied
denied_filters = emma_context.get_denied_properties('Geography', 'read')
# This is for property-level, node-level uses row_filters
```

## Benefits

✅ **Automatic** - No manual query modification needed  
✅ **Consistent** - Works across all repository methods  
✅ **Secure** - Cannot be bypassed by emma  
✅ **Flexible** - Can restrict by any property or condition  
✅ **Centralized** - Managed through permissions in graph  

## Advanced: Multiple Restrictions

You can combine restrictions:

```python
# Block France AND recent data
emma_permissions = [
    'node:deny:france_data',           # No France
    'node:deny:recent_data',           # No data from 2024+
    'property:deny:confidential'        # No confidential properties
]

# Emma would see:
# - All countries except France
# - Only historical data (before 2024)
# - All properties except confidential ones
```

## Troubleshooting

### Emma still sees France?

**Check:**
1. Is emma user assigned the `no_france` role?
2. Is the permission properly linked?
3. Is SecurityContext being passed to ORMKnowledgeGraph?
4. Is the API using `get_security_context()` dependency?

**Verify:**
```python
# Check emma's roles
context = SecurityContext(user_data={'username': 'emma'}, graph=rbac_graph)
roles = context.get_roles()
print(f"Emma's roles: {roles}")  # Should include 'no_france'

# Check filters
filters = context.get_row_filters('Geography', 'read')
print(f"Filters: {filters}")  # Should include France filter
```

## Summary

**Yes, the system CAN and DOES restrict emma from France data!**

- ✅ Automated script provided
- ✅ Works automatically with all queries
- ✅ DENY rules enforce the restriction
- ✅ Cannot be bypassed
- ✅ Easy to manage and update

Run `python3 scripts/restrict_emma_from_france.py` to set it up!
