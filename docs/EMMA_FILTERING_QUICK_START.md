# Emma Data Filtering - Quick Start Guide

## 🎯 What is This?

Emma (`emma_restricted`) is a restricted user in the Tijara Knowledge Graph who **cannot see**:
- 🚫 France (Geography)
- 🚫 Cotton (Commodity)

This demonstrates **data-level security** where entire entities are filtered out at the query level.

---

## ⚡ Quick Test (30 seconds)

### Run Automated Tests
```bash
./scripts/test_emma_filtering.sh
```
Expected: All 5 tests pass ✅

---

## 🌐 Browser Demo

### 1. Login
- URL: http://127.0.0.1:8080
- User: `emma_restricted` / Password: `emma123`

### 2. Test in Discovery Tab
**Query:**
```cypher
MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name
```
**Emma sees:** `["United States"]` only  
**Admin sees:** `["France", "United States"]`

### 3. Test in Trading Copilot
**Ask:** "What countries are in the LDC system?"  
**Emma's answer:** Only mentions United States  
**Admin's answer:** Mentions both France and United States

---

## 📊 Test Results Summary

| Filter Type | Entity | Emma Sees? | Admin Sees? | Status |
|------------|--------|-----------|------------|---------|
| Geography | France | ❌ No | ✅ Yes | ✅ Working |
| Commodity | Cotton | ❌ No | ✅ Yes | ✅ Working |
| Combined | France + Cotton | ❌ No | ✅ Yes | ✅ Working |

---

## 🔍 How It Works

### 1. Query Rewriting
Original query:
```cypher
MATCH (g:Geography {level: 0}) RETURN g.name
```

Rewritten for Emma:
```cypher
MATCH (g:Geography {level: 0}) 
WHERE (NOT (g.name = 'France')) 
RETURN g.name
```

### 2. Graphiti Post-Filtering
- Natural language queries use Graphiti semantic search
- Results mentioning "France" are **filtered out** before LLM sees them
- Emma's answers never mention France or Cotton

### 3. Multi-Layer Enforcement
✅ Cypher queries (Discovery tab)  
✅ Natural language queries (Trading Copilot)  
✅ Analytics queries  
✅ Repository queries (ORM layer)

---

## 📝 Quick Test Queries

Copy-paste these in Discovery → Custom Cypher Query:

**Test 1 - Geography:**
```cypher
MATCH (g:Geography {level: 0}) RETURN g.name ORDER BY g.name
```
Emma: 1 result | Admin: 2 results

**Test 2 - Commodity:**
```cypher
MATCH (c:Commodity) WHERE c.name IN ["Coffee", "Cotton", "Wheat"] 
RETURN c.name ORDER BY c.name
```
Emma: 2 results | Admin: 3 results

**Test 3 - Combined:**
```cypher
MATCH (g:Geography)-[:PRODUCES]->(c:Commodity)
WHERE g.name IN ["France", "United States"] AND c.name IN ["Coffee", "Cotton"]
RETURN g.name, c.name
```
Emma: Only US/Coffee pairs | Admin: All combinations

---

## 🎓 Understanding the Security Model

### Permission Structure
```
User: emma_restricted
 └─ Role: restricted_analyst
     ├─ Permission: node:deny:france
     │   ├─ Resource: node
     │   ├─ Action: read
     │   ├─ Grant Type: DENY
     │   └─ Filter: {"name": "France"}
     │
     └─ Permission: node:deny:cotton
         ├─ Resource: node
         ├─ Action: read
         ├─ Grant Type: DENY
         └─ Filter: {"name": "Cotton"}
```

### Enforcement Points
1. **SecurityContext** - Loads user permissions from RBAC graph
2. **QueryRewriter** - Injects WHERE clauses into Cypher queries
3. **QueryEngine** - Post-filters Graphiti semantic search results
4. **Repository Layer** - All ORM queries go through secure wrapper

---

## 🐛 Troubleshooting

### Emma can still see France/Cotton?

**Check permissions:**
```bash
curl -H "Authorization: Bearer <token>" \
  http://127.0.0.1:8080/auth/me | jq .permissions
```
Should include: `"node:deny:france"` and `"node:deny:cotton"`

**Check filters are active:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://127.0.0.1:8080/debug/filters?label=Geography"
```
Should show: `"row_filters": ["NOT (name = 'France')"]`

**Re-add permissions:**
```bash
python3 scripts/add_emma_filtering_examples.py
```

### Clear browser cache
- Hard refresh: **Cmd/Ctrl + Shift + R**
- Or: Logout → Clear cache → Login

---

## 📚 Full Documentation

- **Comprehensive Tests**: `docs/EMMA_DATA_FILTERING_DEMO.md`
- **Setup Script**: `scripts/add_emma_filtering_examples.py`
- **Test Script**: `scripts/test_emma_filtering.sh`

---

## 🚀 What's Next?

### Implemented ✅
- Row-level filtering (Geography, Commodity)
- Query rewriting (Cypher)
- Graphiti post-filtering (Natural Language)
- Multi-entity filtering (combined)

### Future Enhancements ⏳
- Property-level filtering (hide specific fields like `price`)
- Relationship-level filtering (hide certain edges)
- Attribute-based conditions (e.g., only trades > $1M)
- Time-based filtering (only recent data)

---

## 💡 Key Takeaways

1. **Transparent Security** - Emma doesn't know France exists
2. **Zero Trust** - Filtering at every query, not application layer
3. **Flexible Rules** - Easy to add new restrictions via RBAC graph
4. **Performance** - Minimal overhead with query rewriting
5. **Superuser Bypass** - Admin sees everything

**This is production-ready data-level security!** 🎉
