# Testing Guide: emma_restricted France Data Restriction

This guide explains how to test that the `emma_restricted` user is properly blocked from accessing France-related Geography data.

## Overview

The `emma_restricted` user has a **DENY** permission that blocks access to Geography nodes where `name='France'`. When this user queries the knowledge graph, any Geography nodes with the name "France" will be automatically filtered out by the data-level security system.

## Prerequisites

1. **Server Status**: The API server must be running
2. **User Setup**: The `emma_restricted` user must exist in the RBAC graph
3. **Permission Configuration**: The DENY permission filter must be correctly configured

## Step 1: Verify Security Configuration

### Check emma_restricted Permissions

```bash
python3 -c "
from falkordb import FalkorDB
import yaml

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Connect to RBAC graph
db = FalkorDB(host=config['rbac'].get('host', 'localhost'), port=config['rbac'].get('port', 6379))
rbac_graph = db.select_graph(config['rbac']['graph_name'])

# Check permissions
result = rbac_graph.query('''
MATCH (u:User {username: 'emma_restricted'})-[:HAS_ROLE]->(r:Role)
      -[:HAS_PERMISSION]->(p:Permission)
WHERE p.grant_type = 'DENY'
RETURN p.name, p.node_label, p.property_filter, p.grant_type
''')

print('emma_restricted DENY Permissions:')
for row in result.result_set:
    print(f'  🚫 {row[0]}')
    print(f'     Node Label: {row[1]}')
    print(f'     Filter: {row[2]}')
    print(f'     Grant Type: {row[3]}')
"
```

**Expected Output:**
```
emma_restricted DENY Permissions:
  🚫 node:deny:france
     Node Label: Geography
     Filter: {"name": "France"}
     Grant Type: DENY
```

### Verify France Geography Node Exists

```bash
python3 -c "
from falkordb import FalkorDB
import yaml

with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

db = FalkorDB(host=config['falkordb'].get('host', 'localhost'), port=config['falkordb'].get('port', 6379))
kg_graph = db.select_graph(config['falkordb']['graph_name'])

result = kg_graph.query('''
MATCH (g:Geography {name: 'France', level: 0})
RETURN g.name, g.country, g.level, id(g)
''')

if result.result_set:
    name, country, level, node_id = result.result_set[0]
    print(f'✅ France Geography node found:')
    print(f'   Name: {name}')
    print(f'   Country: {country}')
    print(f'   Level: {level}')
    print(f'   Node ID: {node_id}')
else:
    print('❌ France Geography node NOT found')
"
```

**Expected Output:**
```
✅ France Geography node found:
   Name: France
   Country: None
   Level: 0
   Node ID: 3406
```

## Step 2: Get emma_restricted Credentials

The credentials were created when running the setup script. Check the default password:

```bash
# Look in the setup_example_permissions.py script
grep -A 10 "emma_restricted" scripts/setup_example_permissions.py
```

**Default credentials:**
- Username: `emma_restricted`
- Password: Check the setup script output or documentation

If you don't know the password, you can reset it:
```bash
python3 scripts/reset_user_password.py emma_restricted newpassword123
```

## Step 3: Test via API (Recommended)

### Start the Server

```bash
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Test 1: Login as admin (Control Test)

```bash
# Login as admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Save the `access_token` from the response.

```bash
# Query Geography data as admin (should see France)
curl -X POST http://localhost:8000/cypher \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name",
    "parameters": {}
  }'
```

**Expected Result:** Should return both "France" and "United States"

### Test 2: Login as emma_restricted (Filtered Test)

```bash
# Login as emma_restricted
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emma_restricted&password=EMMA_PASSWORD_HERE"
```

Save the `access_token` from the response.

```bash
# Query Geography data as emma_restricted (should NOT see France)
curl -X POST http://localhost:8000/cypher \
  -H "Authorization: Bearer YOUR_EMMA_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name",
    "parameters": {}
  }'
```

**Expected Result:** Should return only "United States" (France is filtered out)

## Step 4: Test via Web UI

### 1. Open Browser
Navigate to: `http://localhost:8000/login.html`

### 2. Test as Admin (Control)
1. Login with: `admin` / `admin123`
2. You should see "System Administrator" in the top-right corner
3. Navigate to "Data Discovery" tab
4. Run query: `MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name`
5. **Expected:** Results include "France" and "United States"

### 3. Logout
Click the user menu (top-right) → Logout

### 4. Test as emma_restricted (Filtered)
1. Login with: `emma_restricted` / `[password]`
2. You should see "Emma Restricted" and role "restricted_analyst" in the top-right
3. Navigate to "Data Discovery" tab
4. Run query: `MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name`
5. **Expected:** Results include only "United States" (France is filtered out)

## Step 5: Verify Filtering Behavior

### Direct Python Test (Most Reliable)

Create a test script `test_emma_filtering.py`:

```python
#!/usr/bin/env python3
"""Test emma_restricted France filtering."""

import yaml
from src.core.orm_knowledge_graph import ORMKnowledgeGraph
from src.security.context import SecurityContext

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("=" * 70)
print("Testing France Data Filtering")
print("=" * 70)

# Test 1: Admin (no filtering)
print("\n1. Admin User (No Filtering):")
admin_context = SecurityContext(user_data={
    'sub': 'admin',
    'user_id': 1,
    'is_superuser': True
})
kg_admin = ORMKnowledgeGraph(config, security_context=admin_context)

result = kg_admin.falkordb.execute_query(
    'MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name'
)
print(f"   Found {len(result)} countries:")
for row in result:
    print(f"   - {row[0]}")

# Test 2: emma_restricted (with filtering)
print("\n2. emma_restricted User (With Filtering):")
emma_context = SecurityContext(user_data={
    'sub': 'emma_restricted',
    'user_id': 10,  # Adjust based on actual ID
    'is_superuser': False
})
kg_emma = ORMKnowledgeGraph(config, security_context=emma_context)

result = kg_emma.falkordb.execute_query(
    'MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name'
)
print(f"   Found {len(result)} countries:")
for row in result:
    print(f"   - {row[0]}")

print("\n3. Analysis:")
if len(result) == 1 and result[0][0] == 'United States':
    print("   ✅ SUCCESS: France was filtered out for emma_restricted!")
elif len(result) == 2:
    print("   ❌ FAILURE: France was NOT filtered out!")
    print("   Possible causes:")
    print("   - DENY permission not properly configured")
    print("   - QueryRewriter not being applied")
    print("   - Filter mismatch (check property_filter)")
else:
    print(f"   ⚠️  UNEXPECTED: Got {len(result)} results")

print("=" * 70)
```

Run it:
```bash
python3 test_emma_filtering.py
```

## Troubleshooting

### Issue: France is NOT filtered out for emma_restricted

**Possible Causes:**

1. **Filter Mismatch**
   ```bash
   # Check if filter matches data structure
   python3 scripts/fix_emma_france_filter.py
   ```

2. **DENY Permission Not Assigned**
   ```bash
   python3 -c "
   from falkordb import FalkorDB
   import yaml
   
   with open('config/config.yaml', 'r') as f:
       config = yaml.safe_load(f)
   
   db = FalkorDB(host=config['rbac'].get('host', 'localhost'), port=config['rbac'].get('port', 6379))
   rbac_graph = db.select_graph(config['rbac']['graph_name'])
   
   result = rbac_graph.query('''
   MATCH (u:User {username: 'emma_restricted'})-[:HAS_ROLE]->(r:Role)-[:HAS_PERMISSION]->(p:Permission {grant_type: 'DENY'})
   RETURN COUNT(p)
   ''')
   
   count = result.result_set[0][0]
   if count == 0:
       print('❌ No DENY permissions assigned to emma_restricted')
       print('Run: python3 scripts/setup_example_permissions.py')
   else:
       print(f'✅ emma_restricted has {count} DENY permission(s)')
   "
   ```

3. **SecurityContext Not Being Used**
   - Check that endpoints use `get_security_context()` dependency
   - Check that ORMKnowledgeGraph is created with `security_context` parameter

4. **QueryRewriter Not Applying Filters**
   - Check logs for query rewriting messages
   - Verify PolicyManager is loading permissions correctly

### Issue: Login hangs or fails

**Solution:**
- Ensure the global `kg` instance is created (already fixed in main.py)
- Check that FalkorDB is running: `redis-cli -h localhost -p 6379 ping`
- Verify RBAC graph connection in config.yaml

## Summary of Expected Behavior

| User | Query | Expected Result |
|------|-------|----------------|
| `admin` | `MATCH (g:Geography {level: 0}) RETURN g.name` | "France", "United States" |
| `emma_restricted` | `MATCH (g:Geography {level: 0}) RETURN g.name` | "United States" only |

The key difference:
- **admin**: Superuser bypass - sees all data
- **emma_restricted**: DENY rule applies - France is filtered out

## Technical Details

### How the Filter Works

1. **Permission Definition:**
   ```json
   {
     "name": "node:deny:france",
     "resource": "node",
     "action": "read",
     "node_label": "Geography",
     "property_filter": "{\"name\": \"France\"}",
     "grant_type": "DENY"
   }
   ```

2. **Query Rewriting:**
   ```cypher
   # Original Query
   MATCH (g:Geography {level: 0}) RETURN g.name
   
   # Rewritten Query (for emma_restricted)
   MATCH (g:Geography {level: 0})
   WHERE NOT (g.name = 'France')
   RETURN g.name
   ```

3. **Result:** The France node is excluded from the result set before it reaches the application layer.

## Files Involved

- **Security Setup:** `scripts/setup_example_permissions.py`
- **Filter Fix:** `scripts/fix_emma_france_filter.py`
- **Security Context:** `src/security/context.py`
- **Query Rewriter:** `src/security/query_rewriter_enhanced.py`
- **Policy Manager:** `src/security/policy_manager.py`
- **ORM Integration:** `src/core/orm_knowledge_graph.py`

## Next Steps

Once you've verified the filtering works:

1. Test with other users (alice_analyst, bob_trader, etc.)
2. Create additional DENY rules for different node labels
3. Test GRANT rules with property filters
4. Test edge filtering (relationship restrictions)
5. Test property filtering (column-level security)
