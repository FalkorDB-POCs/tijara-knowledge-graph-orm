# emma_restricted Security Profile Analysis

## Executive Summary

**Status:** ✅ **FIXED** - Security profile has been corrected and is now ready for testing

The `emma_restricted` user's France data restriction has been analyzed and corrected. The DENY permission filter was updated to match the actual data structure in the knowledge graph.

## Problem Identified

### Original Configuration (Incorrect)
```json
{
  "permission": "node:deny:france",
  "node_label": "Geography",
  "property_filter": "{\"country\": \"France\"}",
  "grant_type": "DENY"
}
```

### Actual Data Structure
```cypher
// France Geography node in the graph
(g:Geography {
  name: "France",
  country: None,    // ← This was the issue
  level: 0
})
```

### The Mismatch
- **Filter was checking:** `country = "France"`
- **Actual node has:** `name = "France"` and `country = None`
- **Result:** Filter would never match, so France data would **NOT** be blocked

## Solution Applied

### Updated Configuration (Correct)
```json
{
  "permission": "node:deny:france",
  "node_label": "Geography",
  "property_filter": "{\"name\": \"France\"}",  // ← Changed to check name
  "grant_type": "DENY"
}
```

### Fix Script
The fix was applied using: `scripts/fix_emma_france_filter.py`

```bash
python3 scripts/fix_emma_france_filter.py
```

**Output:**
```
✅ Successfully updated France DENY filter!

What changed:
  Old filter: {"country": "France"}
  New filter: {"name": "France"}

Why:
  The France Geography node has:
    - name: 'France'
    - country: None
  So the filter must check 'name' instead of 'country'
```

## Current Security Profile for emma_restricted

### User Information
- **Username:** `emma_restricted`
- **Full Name:** Emma Restricted
- **Role:** `restricted_analyst`
- **Is Superuser:** No
- **Is Active:** Yes

### Assigned Permissions

| Permission | Resource | Action | Node Label | Property Filter | Grant Type | Effect |
|------------|----------|--------|------------|-----------------|------------|--------|
| `analytics:read` | analytics | read | - | - | GRANT | ✅ Can read analytics |
| `discovery:read` | discovery | read | - | - | GRANT | ✅ Can read discovery data |
| `discovery:execute` | discovery | execute | - | - | GRANT | ✅ Can execute discovery queries |
| `node:deny:france` | node | read | Geography | `{"name": "France"}` | DENY | 🚫 Cannot see France Geography nodes |

### Behavior

When `emma_restricted` queries Geography data:

**Original Query:**
```cypher
MATCH (g:Geography {level: 0}) 
RETURN g.name 
ORDER BY g.name
```

**Rewritten Query (by QueryRewriter):**
```cypher
MATCH (g:Geography {level: 0})
WHERE NOT (g.name = 'France')  // ← DENY filter applied
RETURN g.name
ORDER BY g.name
```

**Result:**
- Admin sees: `["France", "United States"]`
- emma_restricted sees: `["United States"]` (France filtered out)

## Data in Knowledge Graph

### Geography Nodes (Level 0 - Countries)
```
🌍 France (id: 3406)
   - name: "France"
   - country: None
   - level: 0
   
🌍 United States (id: 3405)
   - name: "United States"
   - country: None
   - level: 0
```

Only these 2 country-level Geography nodes exist, making it easy to verify the restriction works.

## Testing Instructions

**Quick Test:**
```bash
# 1. Start server
python3 -m uvicorn api.main:app --port 8000

# 2. Login as admin
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=admin123"
# Save the token

# 3. Query as admin (should see both countries)
curl -X POST http://localhost:8000/cypher \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name"}'

# Expected: ["France", "United States"]

# 4. Login as emma_restricted
curl -X POST http://localhost:8000/auth/login \
  -d "username=emma_restricted&password=<EMMA_PASSWORD>"
# Save the token

# 5. Query as emma_restricted (should see only United States)
curl -X POST http://localhost:8000/cypher \
  -H "Authorization: Bearer <EMMA_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name"}'

# Expected: ["United States"] (France filtered out)
```

**Full Testing Guide:** See `docs/TESTING_EMMA_FRANCE_RESTRICTION.md`

## Files Modified

1. **scripts/fix_emma_france_filter.py** (NEW)
   - Script to update the DENY permission filter
   - Can be run multiple times safely

2. **RBAC Graph** (MODIFIED)
   - Permission `node:deny:france` property_filter updated
   - From: `{"country": "France"}`
   - To: `{"name": "France"}`

## Verification Checklist

- [x] emma_restricted user exists and is active
- [x] DENY permission exists and is assigned to emma_restricted via role
- [x] Permission filter matches actual data structure
- [x] France Geography node exists (id: 3406)
- [x] Filter fix script created and executed successfully
- [ ] **TODO:** Test via API that France is filtered out
- [ ] **TODO:** Test via Web UI that France is filtered out
- [ ] **TODO:** Verify other users (admin) can still see France

## Key Insights

### Why This Matters
This demonstrates a critical security principle: **data-level security filters must precisely match the actual data schema**. A mismatch renders the security control ineffective.

### Lessons Learned
1. **Always verify data structure** before creating security policies
2. **Test security rules** against actual data, not assumptions
3. **Provide diagnostic tools** to identify mismatches (like our analysis script)
4. **Document expected behavior** clearly for testing

### Architecture Strengths
The system correctly identified and fixed the issue because:
- Clear separation between RBAC graph and knowledge graph
- Flexible property_filter design allows JSON-based conditions
- QueryRewriter applies filters at query time
- PolicyManager converts Permission entities to runtime rules

## Next Steps

1. **Testing Phase**
   - Follow `docs/TESTING_EMMA_FRANCE_RESTRICTION.md`
   - Verify both API and Web UI behavior
   - Document test results

2. **Additional Security Rules** (Future)
   - Create DENY rules for other sensitive data
   - Test GRANT rules with property filters
   - Implement edge (relationship) filtering
   - Add column-level (property) filtering

3. **Production Considerations**
   - Add logging for filtered queries
   - Monitor performance impact of query rewriting
   - Create audit trail for DENY rule applications
   - Add alerts for permission mismatches

## References

- **Main Implementation:** `DATA_LEVEL_FILTERING_IMPLEMENTATION.md`
- **Testing Guide:** `TESTING_EMMA_FRANCE_RESTRICTION.md`
- **Security Documentation:** `SECURITY_FILTERING.md`
- **Setup Script:** `scripts/setup_example_permissions.py`
- **Fix Script:** `scripts/fix_emma_france_filter.py`
