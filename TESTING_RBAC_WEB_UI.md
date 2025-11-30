# Testing RBAC Data Restrictions in Web UI

This guide demonstrates how to test data-level security by comparing the **restricted user** (`emma_restricted`) with the **admin user** (`admin`) in the web interface.

## Test Users

### Admin User (Full Access)
- **Username**: `admin`
- **Password**: `admin123`
- **Access**: Superuser - sees ALL data (no restrictions)

### Restricted User (Limited Access)
- **Username**: `emma_restricted`
- **Password**: `emma123`
- **Restrictions**:
  - ❌ Cannot see **France** (Geography nodes with name="France")
  - ❌ Cannot see **Cotton** (Commodity nodes with name="Cotton")
  - ❌ Cannot see **confidential** properties on BalanceSheet nodes
  - ❌ Cannot see **price** properties on BalanceSheet nodes

## Prerequisites

1. **Ensure API is running**:
   ```bash
   python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8080
   ```

2. **Load test users** (if not already loaded):
   ```bash
   python3 scripts/rbac/init_rbac.py
   python3 scripts/rbac/create_emma_user.py
   ```

3. **Open web interface**:
   ```
   http://localhost:8080
   ```

## Test Suite

### Test 1: Login as Each User

#### Step 1.1: Login as Admin
1. Navigate to `http://localhost:8080/login.html`
2. Enter credentials:
   - Username: `admin`
   - Password: `admin123`
3. Click **Login**
4. Verify: Redirected to main interface
5. Note: You're logged in as **admin** (superuser)

#### Step 1.2: Login as Restricted User
1. **Log out** from admin (use browser incognito/private window OR clear localStorage)
2. Navigate to `http://localhost:8080/login.html`
3. Enter credentials:
   - Username: `emma_restricted`
   - Password: `emma123`
4. Click **Login**
5. Verify: Redirected to main interface
6. Note: You're logged in as **emma_restricted**

---

### Test 2: Natural Language Queries (Trading Copilot Tab)

Navigate to **Tab 1: Trading Copilot**

#### Test 2.1: Query About Countries

**Query**: "What countries are in the LDC system?"

**Expected Results**:

| User | Result |
|------|--------|
| **admin** | Shows: **France, United States** |
| **emma_restricted** | Shows: **United States** only (France filtered out) |

**Steps**:
1. Click the quick question button: **"What countries are in the LDC system?"**
2. Wait for response
3. Check the answer text
4. Verify confidence score and sources

**Verification**:
- Admin sees both countries
- Emma does NOT see France mentioned anywhere in the response

---

#### Test 2.2: Query About Commodities

**Query**: "What commodities does USA export to France?"

**Expected Results**:

| User | Result |
|------|--------|
| **admin** | Lists: Yellow Corn, Hard Red Wheat (Spring), Soft Red Wheat (Winter), **Cotton**, Peas |
| **emma_restricted** | Lists: Yellow Corn, Hard Red Wheat (Spring), Soft Red Wheat (Winter), Peas (Cotton filtered out) |

**Steps**:
1. Type query in chat: "What commodities does USA export to France?"
2. Press Enter or click Send
3. Review the list of commodities in the response

**Verification**:
- Admin sees Cotton in the list
- Emma does NOT see Cotton mentioned

---

### Test 3: Data Discovery (Cypher Queries)

Navigate to **Tab 5: Data Discovery**

#### Test 3.1: List All Countries

**Query**:
```cypher
MATCH (g:Geography {level: 0})
RETURN g.name ORDER BY g.name
```

**Expected Results**:

| User | Countries Returned |
|------|-------------------|
| **admin** | France, United States |
| **emma_restricted** | United States |

**Steps**:
1. Go to "Custom Cypher Queries" section
2. Enter the query above
3. Click **Execute**
4. Check the results table

**Verification**:
- Admin table shows 2 rows: France, United States
- Emma table shows 1 row: United States only

---

#### Test 3.2: List All Commodities

**Query**:
```cypher
MATCH (c:Commodity)
WHERE c.level = 2
RETURN c.name ORDER BY c.name
```

**Expected Results**:

| User | Commodities |
|------|-------------|
| **admin** | Coffee, Corn, **Cotton**, Wheat (4 commodities) |
| **emma_restricted** | Coffee, Corn, Wheat (3 commodities, Cotton filtered) |

**Steps**:
1. Enter the query in Cypher editor
2. Click **Execute**
3. Count the rows in results

**Verification**:
- Admin sees Cotton in results
- Emma does NOT see Cotton

---

#### Test 3.3: France-USA Trade Flows

**Query**:
```cypher
MATCH (g1:Geography {name: "France"})-[t:TRADES_WITH]->(g2:Geography {name: "United States"})
RETURN t.commodity as commodity, t.flow_type as type
ORDER BY commodity
```

**Expected Results**:

| User | Result |
|------|--------|
| **admin** | Shows 4 trade flows (Common Wheat, Durum Wheat, etc.) |
| **emma_restricted** | Shows 0 results (France node is filtered out) |

**Steps**:
1. Enter the query
2. Click **Execute**
3. Check if any results are returned

**Verification**:
- Admin sees trade flows
- Emma sees **empty results** (because France is restricted)

---

#### Test 3.4: USA-France Trade Flows (Reverse)

**Query**:
```cypher
MATCH (g1:Geography {name: "United States"})-[t:TRADES_WITH]->(g2:Geography {name: "France"})
RETURN t.commodity as commodity, t.flow_type as type
ORDER BY commodity
```

**Expected Results**:

| User | Result |
|------|--------|
| **admin** | Shows 5 flows including Cotton |
| **emma_restricted** | Shows 0 results (France node is filtered, Cotton filtered) |

**Steps**:
1. Enter the query
2. Click **Execute**
3. Check results

**Verification**:
- Admin sees all USA→France flows
- Emma sees **no results** (France restriction applies)

---

#### Test 3.5: Combined Filter Test

**Query**:
```cypher
MATCH (g:Geography {name: "France"})-[:PRODUCES]->(c:Commodity {name: "Cotton"})
RETURN g.name as geography, c.name as commodity
```

**Expected Results**:

| User | Result |
|------|--------|
| **admin** | May return results if data exists |
| **emma_restricted** | 0 results (both France AND Cotton are restricted) |

**Steps**:
1. Enter the query
2. Click **Execute**

**Verification**:
- Emma has 0 results (double restriction)
- Admin may have results (depends on data)

---

### Test 4: Data Analytics Tab

Navigate to **Tab 2: Data Analytics**

#### Test 4.1: Extract Geography Dimensions

**Steps**:
1. Select entity type: **Geography**
2. Click **Extract Data**
3. Review results table

**Expected Results**:

| User | Geographies |
|------|-------------|
| **admin** | Includes France and French regions |
| **emma_restricted** | NO France or French regions |

**Verification**:
- Admin sees all geographies including France
- Emma's table excludes any Geography node with France in the name

---

#### Test 4.2: Extract Commodity Dimensions

**Steps**:
1. Select entity type: **Commodity**
2. Click **Extract Data**
3. Review results table

**Expected Results**:

| User | Commodities |
|------|-------------|
| **admin** | Includes Cotton |
| **emma_restricted** | NO Cotton |

**Verification**:
- Admin table includes Cotton
- Emma's table does not have Cotton

---

### Test 5: Quick Analytics Buttons

Navigate to **Tab 2: Data Analytics** → **Quick Analytics**

#### Test 5.1: "List All Countries"

**Steps**:
1. Click **List All Countries** button
2. Review results

**Expected Results**:

| User | Countries |
|------|-----------|
| **admin** | France, United States |
| **emma_restricted** | United States only |

---

#### Test 5.2: "List All Commodities"

**Steps**:
1. Click **List All Commodities** button
2. Review results

**Expected Results**:

| User | Result |
|------|--------|
| **admin** | Full commodity list including Cotton |
| **emma_restricted** | Commodity list WITHOUT Cotton |

---

## Summary of Restrictions

### What Emma CANNOT See:

1. **Geography Nodes**: France (and French regions/sub-regions)
2. **Commodity Nodes**: Cotton
3. **Properties**: `confidential` and `price` on BalanceSheet nodes
4. **Derived Data**: Any query results that would expose France or Cotton

### What Emma CAN See:

1. ✅ United States geography
2. ✅ Other commodities (Corn, Wheat, Coffee, etc.)
3. ✅ USA→France flows are blocked (because France is restricted)
4. ✅ Other trade flows not involving France or Cotton

---

## Verification Checklist

Use this checklist to confirm RBAC is working:

- [ ] Admin sees France, Emma does not
- [ ] Admin sees Cotton, Emma does not
- [ ] Natural language queries filter France for Emma
- [ ] Natural language queries filter Cotton for Emma
- [ ] Cypher queries return 0 results for France nodes (Emma)
- [ ] Cypher queries return 0 results for Cotton nodes (Emma)
- [ ] Data extraction excludes France for Emma
- [ ] Data extraction excludes Cotton for Emma
- [ ] Admin has full access (no filtering)

---

## Troubleshooting

### Issue: Emma sees France/Cotton

**Solution**: Check if query rewriter is enabled and permissions are loaded.

```bash
# Verify permissions exist
python3 -c "
from falkordb import FalkorDB
db = FalkorDB(host='localhost', port=6379)
graph = db.select_graph('rbac_graph')
result = graph.query('MATCH (u:User {username: \"emma_restricted\"})-[:HAS_ROLE]->(r:Role)-[:HAS_PERMISSION]->(p:Permission) RETURN p.name, p.grant_type')
for row in result.result_set:
    print(row)
"
```

### Issue: Admin sees restrictions

**Solution**: Admin should be superuser. Check:

```bash
python3 -c "
from falkordb import FalkorDB
db = FalkorDB(host='localhost', port=6379)
graph = db.select_graph('rbac_graph')
result = graph.query('MATCH (u:User {username: \"admin\"}) RETURN u.is_superuser')
print('Admin is_superuser:', result.result_set[0][0])
"
```

Should return `True`.

### Issue: Login fails

**Solution**: Recreate users:

```bash
python3 scripts/rbac/create_emma_user.py
```

---

## Advanced Testing

### Test Property-Level Filtering

**Query** (as admin):
```cypher
MATCH (b:BalanceSheet)
RETURN b.commodity, b.confidential, b.price
LIMIT 5
```

**Expected**:
- Admin: See `confidential` and `price` properties
- Emma: Properties `confidential` and `price` should be `null` or filtered

*(Note: Property filtering is planned but not fully implemented yet)*

---

## Test Script Reference

Automated test script: `scripts/test_emma_filtering.sh`

Run all tests:
```bash
bash scripts/test_emma_filtering.sh
```

Expected output:
```
✅ Test 1: Geography Filtering - PASSED
✅ Test 2: Commodity Filtering - PASSED
✅ Test 3: Combined Filters - PASSED
✅ Test 4: Natural Language Query - PASSED
✅ Test 5: Query Rewriting - PASSED
```

---

## Documentation Reference

- **Main README**: [README.md](README.md) - Security & RBAC section
- **Data Filtering Scripts**: `scripts/rbac/`
- **Permission Examples**: `scripts/add_emma_filtering_examples.py`

---

**Last Updated**: November 30, 2024  
**Version**: 0.5.1
