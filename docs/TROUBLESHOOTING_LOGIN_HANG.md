# Troubleshooting: Login Hangs with Restricted Users

## Problem

When trying to sign in with the "emma" user (or other restricted users), the system hangs or becomes very slow.

## Root Cause

The SecurityContext tries to load permissions from the RBAC graph immediately when created, which can cause delays if:
1. The graph query is slow
2. The graph connection is not properly initialized
3. There are many permissions to load
4. Network latency to the database

## Quick Fix

### Option 1: Run the Diagnostic Script

```bash
python3 scripts/diagnose_permission_loading.py emma
```

This will test:
- User exists
- User has roles
- Permission query performance
- SecurityContext creation time

### Option 2: Check if FalkorDB is Running

```bash
# Check if FalkorDB is accessible
redis-cli -h localhost -p 6379 ping
# Should return: PONG

# Check RBAC graph exists
redis-cli -h localhost -p 6379 GRAPH.LIST
# Should include your RBAC graph name
```

## Common Issues & Solutions

### Issue 1: Slow Permission Query

**Symptom**: Diagnostic shows query time > 2 seconds

**Solution**: Create indexes
```cypher
// In RBAC graph
GRAPH.QUERY rbac_graph "CREATE INDEX FOR (u:User) ON (u.username)"
GRAPH.QUERY rbac_graph "CREATE INDEX FOR (r:Role) ON (r.name)"
GRAPH.QUERY rbac_graph "CREATE INDEX FOR (p:Permission) ON (p.name)"
```

### Issue 2: Graph Not Connected

**Symptom**: Error "Connection refused" or timeout

**Solution**: Check configuration
```yaml
# In config/config.yaml
rbac:
  host: localhost  # Should match your FalkorDB host
  port: 6379       # Should match your FalkorDB port
  graph_name: rbac_graph  # Should match your graph name
```

### Issue 3: Circular Permissions

**Symptom**: Query never completes

**Solution**: Check for circular relationships
```cypher
// Check for circular role inheritance
MATCH path=(r:Role)-[:INHERITS_FROM*]->(r)
RETURN r.name, length(path)
```

### Issue 4: Too Many Permissions

**Symptom**: Slow but eventually completes

**Solution**: Reduce permission count or use caching
```python
# The SecurityContext now has lazy loading (already implemented)
# Permissions are only loaded when needed
```

## Code Fix (Already Applied)

The SecurityContext has been updated to:
1. **Lazy load** permissions (only when needed)
2. **Cache** loaded permissions
3. **Better error handling** with stack traces
4. **Timeout protection** (implicit through lazy loading)

```python
# In src/security/context.py
def __init__(self, user_data=None, graph=None, lazy_load=True):
    # lazy_load=True by default
    # Permissions only loaded when get_row_filters() is called
```

## Workaround: Disable Data-Level Filtering

If you need to log in urgently without waiting for the fix:

### Temporary: Skip SecurityContext

Modify the API endpoint temporarily:

```python
# In api/dependencies.py - TEMPORARY ONLY
async def get_security_context(
    request: Request,
    user: Optional[dict] = Depends(get_current_user_optional)
) -> SecurityContext:
    if not user:
        return ANONYMOUS_CONTEXT
    
    # Don't pass graph to avoid loading permissions
    context = SecurityContext(user_data=user, graph=None)  # graph=None
    return context
```

**Note**: This disables data-level filtering! Only use temporarily.

## Verification Steps

After applying fixes, verify:

1. **Login Speed**
   ```bash
   time curl -X POST http://localhost:8000/auth/login \
     -d "username=emma&password=yourpassword"
   ```
   Should complete in < 1 second

2. **Permission Loading**
   ```bash
   python3 scripts/diagnose_permission_loading.py emma
   ```
   Should show query time < 0.5s

3. **API Endpoint**
   ```bash
   # Get token
   TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
     -d "username=emma&password=yourpassword" | jq -r .access_token)
   
   # Test filtered endpoint
   time curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/geographies
   ```
   Should complete in < 2 seconds

## Performance Optimization

### Create Indexes (Recommended)

```bash
# Connect to Redis/FalkorDB
redis-cli -h localhost -p 6379

# Select RBAC graph and create indexes
GRAPH.QUERY rbac_graph "CREATE INDEX FOR (u:User) ON (u.username)"
GRAPH.QUERY rbac_graph "CREATE INDEX FOR (r:Role) ON (r.name)"
GRAPH.QUERY rbac_graph "CREATE INDEX FOR (p:Permission) ON (p.name)"
GRAPH.QUERY rbac_graph "CREATE INDEX FOR (p:Permission) ON (p.node_label)"
```

### Reduce Permission Count

If you have many permissions, consolidate them:

```python
# Instead of many specific permissions:
# - node:read:france_only
# - node:read:usa_only
# - node:read:germany_only
# ...

# Use parameterized permissions:
# - node:read:country_filter
#   With property_filter: {"country": "$user_country"}
```

### Use Connection Pooling

Ensure your FalkorDB connection uses pooling:

```python
# In api/main.py
from falkordb import FalkorDB

# Create single connection pool
db = FalkorDB(
    host=config['rbac']['host'],
    port=config['rbac']['port'],
    decode_responses=True  # Faster
)
```

## Debug Mode

Enable debug logging to see what's happening:

```python
# In src/security/context.py - already added
# Error messages now include stack traces

# Check server logs
tail -f server.log | grep "permission"
```

## Long-term Solution

The implementation now includes:
- ✅ Lazy loading of permissions
- ✅ Caching of loaded permissions
- ✅ Better error handling
- ✅ Diagnostic tools

**No code changes should be needed** if:
- FalkorDB is running
- RBAC graph is accessible
- Indexes are created
- Permission count is reasonable (< 100 per user)

## Still Having Issues?

Run the full diagnostic:

```bash
python3 scripts/diagnose_permission_loading.py emma
```

Check the output for specific issues and follow the recommendations provided.

## Summary

**The hanging is likely caused by:**
1. Slow permission query (needs indexes)
2. Graph connection issues
3. Too many permissions to load

**Quick fixes:**
1. Run diagnostic script
2. Create database indexes
3. Check graph connection
4. Verify emma user exists and has roles

**The implementation has been updated** to handle slow queries better through lazy loading and caching!
