# Manual UI Testing Checklist

This checklist is for visual verification of all UI tabs with the ORM library interface.

**Prerequisites:**
- API server running on http://localhost:8000
- FalkorDB with LDC data loaded
- Web browser open to http://localhost:8000

---

## ✅ Trading Copilot Tab (Bonus - Not originally requested)

**Status:** Verified by automated tests ✅

### Actions to Test:
- [ ] Click "What countries are in the LDC system?" quick question
- [ ] Verify answer appears with sources
- [ ] Type custom question: "What commodities does France export?"
- [ ] Click Send button
- [ ] Verify response has confidence score and retrieved entities

**Expected Results:**
- Answers appear with proper formatting
- Sources are listed when "Show sources" is checked
- Confidence score is displayed (e.g., 0.60)
- No errors in console

---

## ✅ Data Analytics Tab

### Test 1: Quick Analytics - List Commodities
- [ ] Click "List All Commodities" button
- [ ] Verify table appears with commodity names
- [ ] Check that results show ~10+ commodities (Wheat, Corn, etc.)

### Test 2: Quick Analytics - List Countries
- [ ] Click "List Countries" button
- [ ] Verify table shows countries with GID codes
- [ ] Check that USA (USA) and France (FRA) appear

### Test 3: Quick Analytics - Trade Flows
- [ ] Click "Trade Flows Between Countries" button
- [ ] Verify table shows trade relationships
- [ ] Check columns: from, to, commodity, flow_type

### Test 4: Quick Analytics - Production Areas
- [ ] Click "Production Areas by Commodity" button
- [ ] Verify table shows production areas and their commodities

### Test 5: Quick Analytics - Balance Sheets
- [ ] Click "Balance Sheets" button
- [ ] Verify table shows balance sheet records with IDs

### Test 6: Quick Analytics - Node Distribution
- [ ] Click "Node Distribution" button
- [ ] Verify table shows node types and counts
- [ ] Check that Geography, Commodity, BalanceSheet appear

### Test 7: PageRank Algorithm
- [ ] Select "PageRank (Importance)" algorithm
- [ ] Click "Fill Trade Network PageRank" button to auto-fill parameters
- [ ] Verify parameters JSON appears: `{"node_label": "Geography", "relationship_type": "TRADES_WITH"}`
- [ ] Click "Run Analysis" button
- [ ] Wait for ~30 seconds
- [ ] Verify results table appears with PageRank scores
- [ ] Check "Export CSV" button works

### Test 8: Node Finder (for Pathfinding)
- [ ] Select "Geography (Countries, Regions)" node type
- [ ] Enter "France" in search term
- [ ] Click "Find Nodes" button
- [ ] Verify table shows nodes with IDs, names, types, properties
- [ ] Click "Copy" button next to a node ID
- [ ] Verify ID is copied to clipboard

### Test 9: Extract Dimensional Data
- [ ] Select "Geography" entity type
- [ ] Keep default dimensions: "name, gid_code, level"
- [ ] Leave filters empty or add: `{"level": 0}` for countries only
- [ ] Click "Extract Data" button
- [ ] Verify table appears with extracted records
- [ ] Check "Export CSV" button works

**Expected Results for All Analytics:**
- No errors in console
- All queries return results in <10 seconds (except PageRank)
- Tables are formatted correctly
- Export buttons work

---

## ✅ Data Ingestion Tab

### Test 1: Sample CSV - Commodity Hierarchy
- [ ] Click "Commodity Hierarchy CSV" sample button
- [ ] Verify CSV content populates in textarea
- [ ] Check that "Commodity Hierarchy" data type is selected
- [ ] Click "Ingest Data" button
- [ ] Verify success message appears

### Test 2: Sample CSV - Trade Flows
- [ ] Click "Trade Flows CSV" sample button
- [ ] Verify CSV content populates
- [ ] Check that "Trade Flows" data type is selected
- [ ] Click "Ingest Data" button
- [ ] Verify success message and statistics

### Test 3: Custom JSON Trade Flow
- [ ] Clear textarea
- [ ] Paste JSON:
  ```json
  [
    {
      "source_country": "France",
      "destination_country": "Germany",
      "commodity": "Wheat",
      "flow_type": "export"
    }
  ]
  ```
- [ ] Select "Trade Flows" data type
- [ ] Uncheck "Validate against ontology"
- [ ] Click "Ingest Data" button
- [ ] Verify success message

### Test 4: Document Ingestion - Sample Market Report
- [ ] Scroll to "Ingest Unstructured Documents" card
- [ ] Click "Market Report" sample button
- [ ] Verify document text populates
- [ ] Check "Test Market Report" appears in source field
- [ ] Click "Extract & Ingest with Graphiti" button
- [ ] Wait up to 60 seconds (AI processing)
- [ ] Verify success message with extracted entities count
- [ ] Check that entity badges appear showing extracted entities

### Test 5: Custom Document Ingestion
- [ ] Clear document textarea
- [ ] Paste custom text:
  ```
  Brazil's soybean production in 2024 was exceptional. The country exported 
  record volumes to China. Meanwhile, corn production in the United States 
  faced challenges due to drought in the Midwest region.
  ```
- [ ] Enter source: "Custom Report"
- [ ] Click "Extract & Ingest with Graphiti" button
- [ ] Verify entities are extracted (Brazil, China, United States, Soybean, Corn)

**Expected Results for Ingestion:**
- CSV parsing works automatically
- JSON is accepted and parsed
- Document processing with Graphiti extracts entities
- Success messages show ingestion statistics
- No errors in console

---

## ✅ Data Discovery Tab

### Test 1: Schema Explorer
- [ ] Navigate to "Data Discovery" tab
- [ ] Scroll to Schema Explorer section (if present)
- [ ] Verify schema information displays
- [ ] Check that concepts/node types are listed
- [ ] Verify entity relationships are shown

### Test 2: Entity Search - Commodities
- [ ] Find entity search section
- [ ] Enter "wheat" in search box
- [ ] Select "Commodity" entity type filter
- [ ] Click Search button
- [ ] Verify results show wheat-related commodities
- [ ] Check that ~6+ results appear

### Test 3: Entity Search - Geographies
- [ ] Clear search
- [ ] Enter "France" in search box
- [ ] Select "Geography" entity type filter
- [ ] Click Search button
- [ ] Verify results show France and related geographies
- [ ] Check that ~3+ results appear

### Test 4: Statistics Display
- [ ] Navigate to "Statistics" tab in sidebar (if separate)
- [ ] Or scroll to statistics section
- [ ] Verify node count is displayed (should be 3,444+)
- [ ] Verify relationship count is displayed (should be 22,612+)
- [ ] Check that node type distribution is shown

### Test 5: Natural Language Query (Trading Copilot)
- [ ] Go back to Trading Copilot tab
- [ ] Ask: "What balance sheets are available?"
- [ ] Verify answer lists available balance sheets
- [ ] Check that sources are cited
- [ ] Verify no errors

**Expected Results for Discovery:**
- Search returns relevant results
- Schema is properly displayed
- Statistics match expected graph size
- Natural language queries work
- All operations complete in <10 seconds

---

## ✅ Impact Analysis Tab

### Test 1: Geographic Impact - France Drought
- [ ] Navigate to "Impact Analysis" tab
- [ ] Select event type: "drought" (or type it in if text field)
- [ ] Enter GeoJSON for France bounding box:
  ```json
  {
    "type": "Polygon",
    "coordinates": [[
      [-5.0, 42.0],
      [10.0, 42.0],
      [10.0, 51.0],
      [-5.0, 51.0],
      [-5.0, 42.0]
    ]]
  }
  ```
- [ ] Set max_hops: 3
- [ ] Set impact_threshold: 0.1
- [ ] Click "Analyze Impact" button
- [ ] Verify results show affected entities
- [ ] Check that production areas, commodities are listed
- [ ] Verify impact visualization (if present)

### Test 2: Geographic Impact - Custom Region
- [ ] Change coordinates to a different region (e.g., USA)
- [ ] USA bounding box:
  ```json
  {
    "type": "Polygon",
    "coordinates": [[
      [-125.0, 24.0],
      [-66.0, 24.0],
      [-66.0, 49.0],
      [-125.0, 49.0],
      [-125.0, 24.0]
    ]]
  }
  ```
- [ ] Select event type: "flood"
- [ ] Click "Analyze Impact" button
- [ ] Verify different set of affected entities

**Expected Results for Impact Analysis:**
- GeoJSON parsing works correctly
- Impact analysis completes in <30 seconds
- Affected entities are listed with impact scores
- Relationship traversal works (max_hops)
- No geometry errors

---

## Overall UI Checks

### Performance
- [ ] All pages load in <2 seconds
- [ ] No lag when switching tabs
- [ ] Queries return results quickly (<10s, except PageRank)
- [ ] No browser console errors

### Visual Design
- [ ] Layout is responsive and clean
- [ ] Tables are formatted correctly
- [ ] Buttons are styled and clickable
- [ ] Icons display correctly
- [ ] Color theme is consistent

### Error Handling
- [ ] Invalid queries show error messages (not crashes)
- [ ] Network errors are handled gracefully
- [ ] Empty results show "No data" messages
- [ ] Loading spinners appear during operations

### ORM Integration
- [ ] All operations use ORM under the hood
- [ ] Entity properties display correctly
- [ ] Relationships load properly
- [ ] No raw Cypher visible to user (unless in analytics tab)

---

## Test Summary Template

**Date:** _____________  
**Tester:** _____________  
**ORM Version:** 1.1.1  
**API Status:** Running ✅ / Not Running ❌

### Results:
- Trading Copilot: ☐ Pass ☐ Fail
- Data Analytics: ☐ Pass ☐ Fail
- Data Ingestion: ☐ Pass ☐ Fail
- Data Discovery: ☐ Pass ☐ Fail
- Impact Analysis: ☐ Pass ☐ Fail

### Issues Found:
```
[List any issues or bugs discovered]
```

### Notes:
```
[Additional observations]
```

---

## Quick Commands

**Start API:**
```bash
cd /Users/shaharbiron/Documents/FalkorDB/Poc/LDC/tijara-knowledge-graph-orm
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Open Browser:**
```bash
open http://localhost:8000
```

**Run Automated Tests:**
```bash
python3 test_ui_tabs_orm.py
```

**Check API Health:**
```bash
curl http://localhost:8000/health | python3 -m json.tool
```
