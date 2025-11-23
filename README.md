# LDC Commodity Trading Knowledge Graph (ORM Implementation)

**ORM-based reimplementation** of the LDC Commodity Trading Knowledge Graph using [falkordb-py-orm](https://github.com/FalkorDB/falkordb-py-orm). This is a sister repository to [tijara-knowledge-graph](https://github.com/FalkorDB-POCs/tijara-knowledge-graph) demonstrating best practices with declarative entity mapping and repository patterns.

> 🔗 **Original Implementation**: [tijara-knowledge-graph](https://github.com/FalkorDB-POCs/tijara-knowledge-graph)  
> 📚 **ORM Framework**: [falkordb-py-orm](https://github.com/FalkorDB/falkordb-py-orm)

[![FalkorDB](https://img.shields.io/badge/FalkorDB-Graph%20Database-blue)](https://www.falkordb.com/)
[![Graphiti](https://img.shields.io/badge/Graphiti-GraphRAG-green)](https://github.com/getzep/graphiti)
[![OpenAI](https://img.shields.io/badge/OpenAI-Embeddings-orange)](https://openai.com/)
[![FalkorDB ORM](https://img.shields.io/badge/FalkorDB-ORM-purple)](https://github.com/FalkorDB/falkordb-py-orm)

## 🎯 Overview

This repository demonstrates **ORM-based graph development** using falkordb-py-orm for LDC's commodity trading system. The same functionality as the original implementation, but with:

### ✨ ORM Benefits
- **Declarative Entities**: Define graph nodes with `@node` and `@relationship` decorators
- **Type Safety**: Python type hints with automatic validation
- **Repository Pattern**: Clean CRUD operations without manual Cypher
- **Relationship Management**: Automatic cascade saves and lazy/eager loading
- **Less Boilerplate**: Auto-generated queries from method names (e.g., `find_by_name()`)
- **Better Testing**: Mock repositories easily for unit tests

### 🚀 Functional Capabilities
- **Natural Language Queries**: Ask questions in plain English about trade flows and production
- **Semantic Search**: Find relevant data through meaning, not just keywords
- **Graph Analytics**: Analyze trade networks, production areas, and commodity hierarchies
- **Impact Analysis**: Assess weather events and disruptions on supply chains
- **Data Discovery**: Explore 3,444 nodes and 14,714 relationships via Cypher queries

## 📊 Datasets

The system supports two distinct datasets:

### 1. LDC Production Dataset (`ldc_graph`)

Official LDC commodity trading data for France-USA bilateral trade analysis.

**Data Coverage:**
- **Countries**: France (FRA), United States (USA)
- **Geographic Entities**: 3,310 locations (countries, regions, sub-regions)
- **Commodities**: 37 commodities in 8 categories with 4-level hierarchy
- **Trade Flows**: 9 bilateral trade relationships
- **Production Areas**: 16 geographic production zones
- **Balance Sheets**: 12 supply/demand summaries
- **Weather Indicators**: 9 climate variables

**Use Cases:** Production analysis, trade flow queries, impact assessment

📖 **[Full LDC Dataset Documentation →](data/ldc/README.md)**

### 2. Demo Dataset (`tijara_graph`)

Synthetic sample data for testing, demonstrations, and training.

**Data Coverage:**
- **Geographic Scope**: Global (USA, Germany, France, Brazil, Morocco, China, India)
- **Commodities**: Corn, Wheat, Soybeans, Rice, Cotton, Coffee
- **Data Types**: Production, Exports, Demand, Yield, Price
- **Temporal Scope**: Monthly data for 2023

**Use Cases:** Development, testing, demos, training, integration testing

📖 **[Full Demo Dataset Documentation →](data/demo/README.md)**

### Key Statistics
```
Nodes: 3,444 total
├── Geography: 3,310 (2 countries, 13 FR regions, multiple US states, sub-regions)
├── Commodity: 37 (Grains, Cotton, Coffee, Cocoa, Oilseeds, Rice, Sugar, Citrus)
├── Component: 60 (balance sheet components)
├── ProductionArea: 16
├── BalanceSheet: 12
└── Indicator: 9

Relationships: 14,714 total
├── LOCATED_IN: 14,576 (geographic hierarchy)
├── HAS_COMPONENT: 60
├── SUBCLASS_OF: 29 (commodity hierarchy)
├── PRODUCES: 16 (area → commodity)
├── FOR_COMMODITY: 12
├── FOR_GEOGRAPHY: 12
└── TRADES_WITH: 9 (bilateral trade flows)
```

### Sample Trade Flows
**France → USA (4 flows)**
- Common Wheat
- Durum Wheat
- Dried Distillers Grains
- Barley

**USA → France (5 flows)**
- Yellow Corn
- Hard Red Wheat (Spring)
- Soft Red Wheat (Winter)
- Cotton
- Peas

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Web UI (Port 8000)                        │
│  Trading Copilot | Analytics | Ingestion | Impact | Discovery│
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────┐
│                   FastAPI REST API                           │
│   /query | /analytics | /ingest | /impact | /cypher | /stats│
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────┐
│              Dual Graph Engine Architecture                  │
│  ┌────────────────────┐     ┌─────────────────────────────┐ │
│  │   FalkorDB         │     │   Graphiti (GraphRAG)       │ │
│  │   ldc_graph        │     │   graphiti                  │ │
│  ├────────────────────┤     ├─────────────────────────────┤ │
│  │ 3,444 nodes        │     │ 6 episodes + embeddings     │ │
│  │ 14,714 relations   │     │ Semantic search (OpenAI)    │ │
│  │ Cypher queries     │     │ Natural language queries    │ │
│  │ Graph algorithms   │     │ Entity extraction           │ │
│  └────────────────────┘     └─────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────┐
│              LDC CSV Data Sources                            │
│  commodity_hierarchy.csv | flows.csv | geometries.csv        │
│  production_areas.csv | balance_sheet.csv | indicators.csv   │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- FalkorDB running on localhost:6379 (or configure in `config/config.yaml`)
- OpenAI API key (for Graphiti semantic search)

### Installation

```bash
# 1. Clone repository
cd tijara-knowledge-graph

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure OpenAI API key
cp config/config.example.yaml config/config.yaml
# Edit config/config.yaml and add your OpenAI API key

# 4. Load data (choose one):

# Option A: Load LDC production data
python3 scripts/ldc/load_ldc_data.py          # Load to FalkorDB (3,444 nodes)
python3 scripts/ldc/load_ldc_graphiti.py      # Load to Graphiti (embeddings)

# Option B: Load demo/sample data
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000  # Start API first
python3 scripts/demo/load_demo_data.py        # Load demo data via API

# 5. Start API server
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# 6. Open web interface
open http://localhost:8000
```

## 🌐 Web Interface Tabs

### Tab 1: 🤖 Trading Copilot
**Natural language question answering powered by GraphRAG with modern chat interface**

**Features:**
- **Chat-Style Interface**: Conversational experience with message history
- **Quick Questions**: 6 pre-configured buttons for common queries
  - What countries are in the LDC system?
  - What commodities does France export to the United States?
  - What commodities does USA export to France?
  - What balance sheets are available in the system?
  - What weather indicators are tracked for production areas?
  - Which commodities have production areas in France and USA?
- **Free-Form Questions**: Type any question and press Enter or click Send
- **Real-Time Confidence Scoring**: Visual badges showing 60-100% confidence
  - High (70-100%): Green badge
  - Medium (40-69%): Orange badge
  - Low (0-39%): Red badge
- **Source Attribution**: Toggle to show/hide source references (up to 3 displayed inline)
- **Entity Extraction**: Related entities displayed as tags
- **Conversation Management**: Clear chat button to start fresh
- **Auto-Scroll**: Messages automatically scroll to the latest response
- **Timestamps**: Each message shows the time it was sent

**Chat Interface Design:**
- User messages: Blue bubbles with user icon
- Assistant responses: White bubbles with robot icon, confidence badges, and optional sources
- System messages: Transparent welcome messages
- Error messages: Red icon with error details

**Example Questions:**
- "What commodities does France export to USA?"
- "What balance sheets are available in the system?"
- "Which commodities have production areas in France?"

**Performance:**
- 100% confidence on trade flow queries
- Up to 10 semantic sources per query
- Sub-2-second response time
- Smooth animations for message appearance

---

### Tab 2: 📈 Data Analytics
**Graph algorithms and dimensional data extraction**

**Section A: Graph Algorithms**
- **Algorithms**: PageRank, Centrality, Community Detection, Pathfinding
- **6 Quick Analytics**: List commodities, countries, trade flows, production areas, balance sheets, node distribution
- **Parameters**: Node labels (Geography, Commodity), relationships (TRADES_WITH, PRODUCES)
- **Output**: Tabular results with export to CSV

**Section B: Extract Dimensional Data**
- **Entity Types**: Geography, Commodity, ProductionArea, BalanceSheet, Indicator
- **Dimensions**: name, gid_code, level (configurable)
- **Filters**: JSON-based filtering by properties
- **Output**: Structured table view, exportable

---

### Tab 3: 📥 Data Ingestion
**Load data matching LDC CSV formats**

**Section A: CSV/JSON Data Upload**
- **5 Sample Datasets**: Commodity Hierarchy, Trade Flows, Balance Sheets, Production Areas, Geometries
- **Data Types**: Auto-detection or manual selection
- **Formats Supported**: 
  - CSV with headers (paste directly)
  - JSON arrays
- **Validation**: Optional ontology validation

**CSV Format Examples:**
```csv
# Trade Flows
source_country,destination_country,commodity,commodity_season
FRA,USA,Common Wheat,

# Commodity Hierarchy
Level0,Level1,Level2,Level3
Grains,Wheat,Common Wheat,Hard Red Wheat

# Geometries
GID_0,NAME_0,Level,GID_1,NAME_1
FRA,France,0,,
USA,United States,0,,
```

**Section B: Document Ingestion**
- **Unstructured Text Processing**: Market reports, news, analysis
- **Graphiti Integration**: Automatic entity extraction
- **3 Sample Documents**: LDC-focused market reports, trade news, production updates
- **Output**: Extracted entities with semantic embeddings

---

### Tab 4: 🌍 Impact Analysis
**Spatial impact analysis of weather events on trade**

**Features:**
- **Event Types**: Drought, Flood, Frost, Policy Change, Trade Disruption
- **Production Areas**: 8 pre-defined regions
  - **France**: Northern France, Picardie, Normandy, All France
  - **USA**: Midwest Corn Belt, Wheat Belt, Southern States, All USA
- **GeoJSON Support**: Auto-fill or custom polygon coordinates
- **Parameters**: Max hops (graph depth), impact threshold
- **Output**: Impacted entities table with scores and paths

**Example Scenarios:**
- Northern France drought → Impact on wheat exports to USA
- Midwest corn belt flood → Impact on Yellow Corn supply to France
- Simultaneous weather events → Bilateral trade disruption analysis

---

### Tab 5: 🔍 Data Discovery
**Explore and query the knowledge graph**

**Section A: Entity Search**
- **Search**: Free-text search (France, USA, commodities)
- **Entity Filters**: Geography, Commodity, ProductionArea, BalanceSheet
- **Results**: Matching entities with properties

**Section B: Custom Cypher Queries**
- **8 Sample Queries**: 
  - France → USA Trade Flows
  - USA → France Trade Flows
  - Commodity Hierarchies
  - Production Areas & Commodities
  - Balance Sheets
  - All Countries
  - French Regions
  - Weather Indicators
- **Query Editor**: Full Cypher support
- **Output**: Tabular results

**Example Cypher:**
```cypher
MATCH (g1:Geography {name: "France"})-[t:TRADES_WITH]->(g2:Geography {name: "United States"})
RETURN t.commodity as commodity, t.flow_type as type
ORDER BY commodity
```

---

### Tab 6: 🗺️ Schema Explorer
**Visualize ontology and data model**

- Node types and relationships
- Schema visualization
- Ontology documentation
- Refresh capability

---

### Tab 7: 📊 Graph Statistics
**Real-time knowledge graph metrics**

- Node counts by type
- Relationship distribution
- Graph health metrics
- Data completeness indicators

## 🔧 Configuration

### config/config.yaml
```yaml
falkordb:
  host: localhost
  port: 6379
  graph_name: ldc_graph          # Use 'ldc_graph' for production, 'tijara_graph' for demo

graphiti:
  falkordb_connection:
    host: localhost
    port: 6379
    graph_name: graphiti

openai:
  api_key: "your-openai-api-key"
  model: "gpt-4-turbo-preview"
  temperature: 0.1

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["*"]
```

## 📁 Project Structure

```
tijara-knowledge-graph/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
│
├── config/
│   ├── config.yaml                    # System configuration
│   └── config.example.yaml            # Configuration template
│
├── api/
│   └── main.py                        # FastAPI application
│
├── src/
│   ├── core/
│   │   ├── knowledge_graph.py         # Main KG interface
│   │   ├── falkordb_client.py         # FalkorDB connection
│   │   └── graphiti_engine.py         # Graphiti GraphRAG engine
│   ├── rag/
│   │   ├── query_engine.py            # Natural language query processor
│   │   └── context_builder.py         # Context retrieval for LLM
│   ├── analytics/
│   │   ├── graph_algorithms.py        # PageRank, centrality, etc.
│   │   ├── spatial_ops.py             # Geographic operations
│   │   └── dimensional_extract.py     # Graph to table conversion
│   └── ontology/
│       └── schema.py                  # Ontology definitions
│
├── web/
│   ├── index.html                     # Main web UI (7 tabs)
│   └── static/
│       ├── css/styles.css             # UI styling
│       └── js/app.js                  # Frontend logic
│
├── data/                              # Datasets
│   ├── ldc/                           # LDC production dataset
│   │   ├── README.md                  # LDC dataset documentation
│   │   └── input/                     # CSV data files (place LDC CSVs here)
│   │       ├── commodity_hierarchy.csv
│   │       ├── flows.csv
│   │       ├── geometries.csv
│   │       ├── production_areas.csv
│   │       ├── balance_sheet.csv
│   │       ├── balance_sheet_component.csv
│   │       └── indicator_definition.csv
│   │
│   └── demo/                          # Demo/sample dataset
│       ├── README.md                  # Demo dataset documentation
│       └── input/                     # Sample data files (optional)
│
├── scripts/
│   ├── ldc/                           # LDC data loading scripts
│   │   ├── load_ldc_data.py           # Load LDC CSV data to FalkorDB
│   │   └── load_ldc_graphiti.py       # Load LDC data to Graphiti
│   ├── demo/                          # Demo data loading scripts
│   │   └── load_demo_data.py          # Load sample data via API
│   └── switch_graph.py                # Switch between graphs
│
└── docs/                              # Documentation
```

## 🔌 API Endpoints

### Query & Search
```bash
# Natural language query
POST /query
{
  "question": "What commodities does France export to USA?",
  "return_sources": true
}

# Cypher query
POST /cypher
{
  "query": "MATCH (g1)-[t:TRADES_WITH]->(g2) RETURN g1.name, g2.name, t.commodity"
}
```

### Analytics
```bash
# Graph algorithms
POST /analytics
{
  "algorithm": "pagerank",
  "parameters": {
    "node_label": "Geography",
    "relationship_type": "TRADES_WITH"
  }
}
```

### Data Ingestion
```bash
# Ingest structured data
POST /ingest
{
  "data": [...],
  "metadata": {...}
}

# Ingest document
POST /ingest/document
{
  "text": "France exported 2.5M tons of wheat...",
  "source": "LDC Market Report"
}
```

### System
```bash
# Health check
GET /health

# Graph statistics
GET /stats
```

## 🎯 Use Cases

### 1. Trade Flow Analysis
**Query**: "What commodities does France export to USA?"
- **Confidence**: 100%
- **Data Sources**: 21 subgraph items, 10 semantic sources
- **Response Time**: <1 second

### 2. Production Monitoring
**Query**: "Which commodities have production areas in France?"
- Lists all commodities with French production zones
- Links to weather indicators for impact analysis

### 3. Balance Sheet Review
**Query**: "What balance sheets are available?"
- Returns 12 balance sheets (6 USA, 6 France)
- Shows commodity and geography linkages
- Includes component breakdown

### 4. Impact Assessment
**Scenario**: Drought in Northern France wheat belt
- **Affected Area**: Hauts-de-France, Île-de-France regions
- **Impacted Commodities**: Common Wheat, Durum Wheat
- **Trade Impact**: France → USA export flows
- **Graph Hops**: 5-level impact propagation

## 📊 Performance Metrics

### Query Performance
- **Simple Queries**: <1 second (trade flows, entity lookup)
- **Complex NL Queries**: 1-2 seconds (with Graphiti semantic search)
- **Graph Analytics**: 2-5 seconds (PageRank, community detection)
- **Impact Analysis**: 3-10 seconds (spatial + multi-hop traversal)

### Data Quality
- **Completeness**: 100% of LDC CSV data loaded
- **Accuracy**: All trade flows validated
- **Freshness**: Data reloaded November 7, 2024
- **Confidence Scores**: 60-100% depending on query specificity

## 🔐 Security Notes

- API runs on localhost by default
- OpenAI API key required for Graphiti features
- FalkorDB access configurable (default: no authentication)
- CORS enabled for `localhost` origins

## 🐛 Troubleshooting

### Data not showing up?
```bash
# Verify FalkorDB has data
python3 -c "
from falkordb import FalkorDB
db = FalkorDB(host='localhost', port=6379)
graph = db.select_graph('ldc_graph')
result = graph.query('MATCH (n) RETURN count(n)')
print(f'Nodes: {result.result_set[0][0]}')
"
```

### API not responding?
```bash
# Check if API is running
curl http://localhost:8000/health

# Restart API with OpenAI key
export OPENAI_API_KEY="your-key"
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Low confidence scores?
- Ensure Graphiti data is loaded: `python3 populate_ldc_graphiti.py`
- Check OpenAI API key is configured
- Verify case-sensitive queries match data (use "France", not "france")

## 📚 Documentation

### Datasets
- **[LDC Dataset Guide](data/ldc/README.md)** - Production data structure, CSV formats, loading instructions
- **[Demo Dataset Guide](data/demo/README.md)** - Sample data for testing and demonstrations

## 🤝 Contributing

This is an internal LDC project. For questions or improvements:
1. Review existing documentation in `docs/`
2. Test changes with `test_ldc_graph.py`
3. Update relevant documentation
4. Contact the Data & Analytics team

## 📄 License

Internal LDC Project - All Rights Reserved

## 🎉 Acknowledgments

Built with:
- [FalkorDB](https://www.falkordb.com/) - High-performance graph database
- [Graphiti](https://github.com/getzep/graphiti) - GraphRAG framework
- [OpenAI](https://openai.com/) - Embedding models for semantic search
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework

---

**Version**: 1.0.0 (LDC Production Release)  
**Last Updated**: November 8, 2024  
**Status**: ✅ Production Ready
