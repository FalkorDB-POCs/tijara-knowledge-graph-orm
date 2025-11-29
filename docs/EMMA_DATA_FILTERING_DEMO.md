# Emma Data-Level Security Filtering Demo

This document provides comprehensive test cases to demonstrate data-level security filtering for the `emma_restricted` user in the Tijara Knowledge Graph system.

## Overview

The `emma_restricted` user has the following data-level restrictions:

1. **Geography Filter**: Cannot view France-related data
2. **Commodity Filter**: Cannot view Cotton-related data
3. **Property Filter**: Cannot view `price` and `confidential_notes` fields (future)

All tests compare `emma_restricted` (restricted) vs `admin` (unrestricted) to show the filtering in action.

---

## Setup

### Login Credentials

```
Emma Restricted:
- Username: emma_restricted
- Password: emma123
- Role: restricted_analyst

Admin:
- Username: admin
- Password: admin123
- Role: superuser (no restrictions)
```

### Access the UI

1. Open browser: http://127.0.0.1:8080
2. Login with either user
3. Navigate to the appropriate tab for testing

---

## Test Category 1: Geography Filtering (France)

### Test 1.1: Direct Geography Query (Cypher)

**Test**: Query all top-level countries

**Location**: Discovery Tab → Custom Cypher Query

**Query**:
```cypher
MATCH (g:Geography {level: 0}) 
RETURN g.name 
ORDER BY g.name
```

**Expected Results**:

| User | Results | Rewritten Query |
|------|---------|----------------|
| emma_restricted | `["United States"]` | `MATCH (g:Geography {level: 0}) WHERE (NOT (g.name = 'France')) RETURN g.name ORDER BY g.name` |
| admin | `["France", "United States"]` | (no rewrite) |

**Verification**:
- ✅ Emma sees only "United States"
- ✅ Admin sees both "France" and "United States"
- ✅ Query is automatically rewritten to add `WHERE NOT (g.name = 'France')`

---

### Test 1.2: Natural Language Query - Countries

**Test**: Ask about countries in the system

**Location**: Trading Copilot Tab

**Query**: 
```
What countries are in the LDC system?
```

**Expected Results**:

| User | Answer Mentions |
|------|----------------|
| emma_restricted | Only "United States" | 
| admin | Both "United States" and "France" |

**Verification**:
- ✅ Emma's answer does NOT mention France
- ✅ Admin's answer mentions both countries
- ✅ Graphiti semantic results are post-filtered to remove France mentions

---

### Test 1.3: Geography Search

**Test**: Search for specific geography

**Location**: Discovery Tab → Custom Cypher Query

**Query**:
```cypher
MATCH (g:Geography) 
WHERE g.name CONTAINS 'Fran' OR g.name CONTAINS 'Unit'
RETURN g.name, g.level
ORDER BY g.name
```

**Expected Results**:

| User | Results |
|------|---------|
| emma_restricted | Only United States entries |
| admin | Both France and United States entries |

**Verification**:
- ✅ Emma sees only US geographies (even with 'Fran' search term)
- ✅ Admin sees all matching geographies including France

---

### Test 1.4: Complex Geography Query

**Test**: Query with relationships

**Location**: Discovery Tab → Custom Cypher Query

**Query**:
```cypher
MATCH (g:Geography)-[:PRODUCES]->(c:Commodity)
WHERE g.level = 0
RETURN g.name as country, COUNT(c) as commodity_count
ORDER BY country
```

**Expected Results**:

| User | Countries in Results |
|------|---------------------|
| emma_restricted | Only United States |
| admin | France and United States |

---

## Test Category 2: Commodity Filtering (Cotton)

### Test 2.1: Direct Commodity Query (Cypher)

**Test**: Query specific commodities

**Location**: Discovery Tab → Custom Cypher Query

**Query**:
```cypher
MATCH (c:Commodity) 
WHERE c.name IN ["Coffee", "Cotton", "Wheat", "Corn"]
RETURN c.name 
ORDER BY c.name
```

**Expected Results**:

| User | Results | Rewritten Query |
|------|---------|----------------|
| emma_restricted | `["Coffee", "Corn", "Wheat"]` | `... WHERE c.name IN [...] AND (NOT (c.name = 'Cotton')) ...` |
| admin | `["Coffee", "Corn", "Cotton", "Wheat"]` | (no rewrite) |

**Verification**:
- ✅ Emma sees Coffee, Corn, Wheat (NO Cotton)
- ✅ Admin sees all four commodities including Cotton
- ✅ Query adds `AND (NOT (c.name = 'Cotton'))` for Emma

---

### Test 2.2: Natural Language Query - Commodities

**Test**: Ask about tracked commodities

**Location**: Trading Copilot Tab

**Query**:
```
What commodities does the system track?
```

**Expected Results**:

| User | Answer Mentions Cotton? |
|------|------------------------|
| emma_restricted | ❌ No |
| admin | ✅ Yes |

**Verification**:
- ✅ Emma's answer lists commodities but NOT Cotton
- ✅ Admin's answer includes Cotton in the list

---

### Test 2.3: All Commodities Query

**Test**: List all commodities at any level

**Location**: Discovery Tab → Custom Cypher Query

**Query**:
```cypher
MATCH (c:Commodity)
RETURN c.name, c.level
ORDER BY c.name
LIMIT 20
```

**Expected Results**:

| User | Cotton in Results? |
|------|-------------------|
| emma_restricted | ❌ No |
| admin | ✅ Yes |

---

## Test Category 3: Combined Filters

### Test 3.1: Geography + Commodity Filter

**Test**: Query production relationships

**Location**: Discovery Tab → Custom Cypher Query

**Query**:
```cypher
MATCH (g:Geography)-[:PRODUCES]->(c:Commodity)
WHERE g.level = 0
RETURN g.name as country, c.name as commodity
ORDER BY country, commodity
LIMIT 10
```

**Expected Results**:

| User | Filters Applied |
|------|----------------|
| emma_restricted | ❌ No France rows, ❌ No Cotton rows |
| admin | ✅ All data visible |

**Verification**:
- ✅ Emma sees only United States countries
- ✅ Emma sees no Cotton commodities
- ✅ Both filters are applied simultaneously

---

### Test 3.2: Trade Flow with Filters

**Test**: Query trade relationships

**Location**: Discovery Tab → Custom Cypher Query

**Query**:
```cypher
MATCH (g1:Geography)-[t:TRADES_WITH]->(g2:Geography)
WHERE g1.level = 0 OR g2.level = 0
RETURN g1.name as from, g2.name as to, t.commodity
LIMIT 10
```

**Expected Results**:

| User | France in Results? |
|------|-------------------|
| emma_restricted | ❌ No (neither as 'from' nor 'to') |
| admin | ✅ Yes |

---

### Test 3.3: Natural Language - Complex Query

**Test**: Ask about specific country and commodity

**Location**: Trading Copilot Tab

**Query**:
```
What commodities does France produce?
```

**Expected Results**:

| User | Response |
|------|----------|
| emma_restricted | "No information available" or "Context not found" |
| admin | Lists French commodities |

**Verification**:
- ✅ Emma cannot access France data even when explicitly asked
- ✅ System correctly denies access without exposing that France exists

---

## Test Category 4: Property-Level Filtering (Future)

**Status**: ⏳ Property filtering not yet implemented

### Test 4.1: Price Field Filtering

**Query**:
```cypher
MATCH (b:BalanceSheet)
RETURN b.product_name, b.price, b.season
LIMIT 5
```

**Expected (when implemented)**:
- emma_restricted: price field returns NULL or is omitted
- admin: price field shows actual values

---

## Test Category 5: Analytics & Quick Queries

### Test 5.1: Quick Analytics Button

**Test**: Use pre-built analytics queries

**Location**: Analytics Tab → Quick Analytics Queries

**Action**: Click any quick query button (e.g., "Top Geographies")

**Expected**:
- ✅ Emma sees filtered results (no France)
- ✅ Admin sees complete results

---

### Test 5.2: Custom Analytics Query

**Test**: Run custom Cypher via analytics

**Location**: Analytics Tab → Quick Analytics

**Query**: Click "Top Geographies by Production" button

**Expected Results**:
- emma_restricted: Only US geographies in results
- admin: All geographies including France

---

## Test Verification Checklist

Use this checklist when demonstrating the system:

### Geography Filtering (France)
- [ ] Direct Cypher query filters France
- [ ] Natural language query doesn't mention France
- [ ] Search queries don't return France
- [ ] Relationship queries exclude France nodes

### Commodity Filtering (Cotton)
- [ ] Direct Cypher query filters Cotton
- [ ] Natural language query doesn't mention Cotton
- [ ] All commodity queries exclude Cotton
- [ ] Combined queries apply both filters

### Query Rewriting
- [ ] Rewritten query visible in `/cypher` endpoint response
- [ ] WHERE clause correctly adds NOT conditions
- [ ] Multiple filters combined with AND
- [ ] Admin queries remain unchanged (no rewriting)

### UI Consistency
- [ ] All tabs respect filtering (Discovery, Analytics, Copilot)
- [ ] Quick query buttons apply filters
- [ ] Results tables don't show filtered data
- [ ] Error messages don't expose filtered entities

---

## Troubleshooting

### If filters don't work:

1. **Check user is logged in as emma_restricted**
   ```javascript
   // In browser console
   console.log(localStorage.getItem('token'));
   ```

2. **Verify permissions are loaded**
   ```bash
   curl -H "Authorization: Bearer <token>" http://127.0.0.1:8080/auth/me
   ```
   Should show: `"permissions": ["analytics:read", "discovery:read", "discovery:execute", "node:deny:france", "node:deny:cotton"]`

3. **Check filters are active**
   ```bash
   curl -H "Authorization: Bearer <token>" "http://127.0.0.1:8080/debug/filters?label=Geography"
   ```
   Should show: `"row_filters": ["NOT (name = 'France')"]`

4. **Clear browser cache and re-login**
   - Hard refresh: Cmd/Ctrl + Shift + R
   - Logout and login again

---

## Quick Test Script

Run this script to quickly verify all filters are working:

```bash
#!/bin/bash

echo "=========================================="
echo "Emma Data Filtering Test Suite"
echo "=========================================="

# Get Emma token
EMMA_TOKEN=$(curl -s -X POST http://127.0.0.1:8080/auth/login \
  -d "username=emma_restricted&password=emma123" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Get Admin token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:8080/auth/login \
  -d "username=admin&password=admin123" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo ""
echo "Test 1: Geography Filtering (France)"
echo "--------------------------------------"

echo -n "Emma sees: "
curl -s -X POST http://127.0.0.1:8080/cypher \
  -H "Authorization: Bearer $EMMA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name"}' | \
  python3 -c "import sys, json; print([x[0] for x in json.load(sys.stdin)['results']])"

echo -n "Admin sees: "
curl -s -X POST http://127.0.0.1:8080/cypher \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name"}' | \
  python3 -c "import sys, json; print([x[0] for x in json.load(sys.stdin)['results']])"

echo ""
echo "Test 2: Commodity Filtering (Cotton)"
echo "--------------------------------------"

echo -n "Emma sees: "
curl -s -X POST http://127.0.0.1:8080/cypher \
  -H "Authorization: Bearer $EMMA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (c:Commodity) WHERE c.name IN [\"Coffee\", \"Cotton\", \"Wheat\"] RETURN c.name ORDER BY c.name"}' | \
  python3 -c "import sys, json; print([x[0] for x in json.load(sys.stdin)['results']])"

echo -n "Admin sees: "
curl -s -X POST http://127.0.0.1:8080/cypher \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (c:Commodity) WHERE c.name IN [\"Coffee\", \"Cotton\", \"Wheat\"] RETURN c.name ORDER BY c.name"}' | \
  python3 -c "import sys, json; print([x[0] for x in json.load(sys.stdin)['results']])"

echo ""
echo "=========================================="
echo "✅ Test suite completed"
echo "=========================================="
```

Save as `test_emma_filtering.sh`, make executable with `chmod +x test_emma_filtering.sh`, and run with `./test_emma_filtering.sh`.

---

## Summary

Emma's data-level security demonstrates:

1. ✅ **Row-level filtering** - Entire entities (France, Cotton) are hidden
2. ✅ **Query rewriting** - Cypher queries automatically modified
3. ✅ **Graphiti post-filtering** - Semantic search results cleaned
4. ✅ **Multi-layer enforcement** - Works in Cypher, RAG, and UI
5. ✅ **Transparent security** - Users unaware of filtered data
6. ✅ **Superuser bypass** - Admin sees everything

This provides comprehensive data-level security without requiring application-level filtering logic in each query.
