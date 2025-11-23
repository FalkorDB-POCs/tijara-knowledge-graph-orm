"""
Populate Graphiti with LDC Data for Semantic Search (Neo4j Backend)
Creates episodes from structured LDC data for natural language queries
"""

import os
import sys
import yaml
from datetime import datetime
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.edges import EntityEdge
from neo4j import GraphDatabase

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.yaml')
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

# Set OpenAI API key from config
os.environ['OPENAI_API_KEY'] = config['openai']['api_key']

from src.core.falkordb_client import FalkorDBClient

print("\n" + "="*60)
print("🚀 LDC Graphiti Data Loader (Neo4j Backend)")
print("="*60)
print("Loading structured LDC data into Graphiti via Neo4j")
print()

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "six666six"
NEO4J_DATABASE = "neo4j"

# Initialize clients
print("📡 Connecting to databases...")
falkordb_client = FalkorDBClient(config['falkordb'])
print(f"✓ Connected to FalkorDB: {config['falkordb']['graph_name']}")

# Initialize Neo4j driver
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
print(f"✓ Connected to Neo4j at {NEO4J_URI}")

# Initialize Graphiti with Neo4j driver
from graphiti_core.llm_client import OpenAIClient
from graphiti_core.llm_client.config import LLMConfig

llm_config = LLMConfig(
    api_key=os.environ['OPENAI_API_KEY'],
    model='gpt-4o-mini',  # Use gpt-4o-mini for compatibility
    temperature=config['graphiti']['temperature'],
    max_tokens=config['graphiti']['max_tokens']
)

llm_client = OpenAIClient(config=llm_config, cache=False, reasoning='none', verbosity='low')

graphiti = Graphiti(
    uri=NEO4J_URI,
    user=NEO4J_USER,
    password=NEO4J_PASSWORD,
    llm_client=llm_client
)
print(f"✓ Initialized Graphiti with Neo4j backend")
print()

async def load_commodity_data():
    """Load commodity hierarchy as episodes."""
    print("📦 Loading commodity data into Graphiti...")
    
    query = """
    MATCH (c:Commodity)
    RETURN c.name as commodity, c.level as level, c.category as category
    ORDER BY c.level, c.name
    LIMIT 20
    """
    results = falkordb_client.execute_query(query)
    
    # Create one comprehensive text summary instead of individual episodes
    commodity_texts = []
    for row in results:
        commodity = row['commodity']
        level = row['level']
        category = row['category'] if row['category'] else 'general'
        
        if level == 0:
            commodity_texts.append(f"{commodity} is a major commodity category")
        elif level == 1:
            commodity_texts.append(f"{commodity} is in the {category} category")
        else:
            commodity_texts.append(f"{commodity} is a {category} variety")
    
    # Add as single episode with all commodity info
    if commodity_texts:
        text = "LDC commodities: " + ". ".join(commodity_texts) + "."
        await graphiti.add_episode(
            name="LDC_Commodities",
            episode_body=text,
            source=EpisodeType.text,
            source_description="LDC Commodity Hierarchy",
            reference_time=datetime.now()
        )
    
    print(f"✓ Loaded commodity data ({len(results)} commodities)")

async def load_geography_data():
    """Load geographic data as episodes."""
    print("🌍 Loading geography data into Graphiti...")
    
    # Countries
    query = """
    MATCH (c:Country)
    RETURN c.name as name, c.gid_code as code
    ORDER BY c.name
    """
    results = falkordb_client.execute_query(query)
    
    text_parts = []
    for row in results:
        text_parts.append(f"{row['name']} ({row['code']})")
    
    if text_parts:
        text = "LDC system covers " + " and ".join(text_parts) + " for commodity trading and production analysis."
        await graphiti.add_episode(
            name="LDC_Countries",
            episode_body=text,
            source=EpisodeType.text,
            source_description="LDC Geography",
            reference_time=datetime.now()
        )
    
    print(f"✓ Loaded geography data ({len(results)} countries)")

async def load_trade_flows():
    """Load trade flow data as episodes."""
    print("🔄 Loading trade flow data into Graphiti...")
    
    query = """
    MATCH (source:Country)-[f:TRADES_WITH]->(dest:Country)
    RETURN source.name as source, dest.name as destination, 
           f.commodity as commodity, f.season as season
    """
    results = falkordb_client.execute_query(query)
    
    flow_texts = []
    for row in results:
        season_str = f" ({row['season']} season)" if row['season'] else ""
        flow_texts.append(f"{row['source']} exports {row['commodity']}{season_str} to {row['destination']}")
    
    if flow_texts:
        text = "Trade flows: " + ". ".join(flow_texts) + "."
        await graphiti.add_episode(
            name="LDC_Trade_Flows",
            episode_body=text,
            source=EpisodeType.text,
            source_description="LDC Trade Flows",
            reference_time=datetime.now()
        )
    
    print(f"✓ Loaded trade flow data ({len(results)} flows)")

async def load_production_areas():
    """Load production area data as episodes."""
    print("🌾 Loading production area data into Graphiti...")
    
    query = """
    MATCH (p:ProductionArea)
    RETURN DISTINCT p.commodity as commodity, p.season as season
    ORDER BY commodity
    """
    results = falkordb_client.execute_query(query)
    
    prod_texts = []
    for row in results:
        season_str = f" ({row['season']} season)" if row['season'] else ""
        prod_texts.append(f"{row['commodity']}{season_str}")
    
    if prod_texts:
        text = "Production areas tracked for: " + ", ".join(prod_texts) + "."
        await graphiti.add_episode(
            name="LDC_Production_Areas",
            episode_body=text,
            source=EpisodeType.text,
            source_description="LDC Production Areas",
            reference_time=datetime.now()
        )
    
    print(f"✓ Loaded production area data ({len(results)} areas)")

async def load_balance_sheets():
    """Load balance sheet data as episodes."""
    print("📊 Loading balance sheet data into Graphiti...")
    
    query = """
    MATCH (b:BalanceSheet)-[:FOR_GEOGRAPHY]->(g:Geography)
    RETURN g.name as country, b.product_name as product, b.season as season
    """
    results = falkordb_client.execute_query(query)
    
    sheet_texts = []
    for row in results:
        season_str = f" ({row['season']} season)" if row['season'] else ""
        sheet_texts.append(f"{row['country']} - {row['product']}{season_str}")
    
    if sheet_texts:
        text = "Balance sheets available for: " + ", ".join(sheet_texts) + ". Each tracks Yield, HarvestedArea, CarryIn, CarryOut, and Consumption."
        await graphiti.add_episode(
            name="LDC_Balance_Sheets",
            episode_body=text,
            source=EpisodeType.text,
            source_description="LDC Balance Sheets",
            reference_time=datetime.now()
        )
    
    print(f"✓ Loaded balance sheet data ({len(results)} sheets)")

async def load_weather_indicators():
    """Load weather indicator data as episodes."""
    print("🌡️  Loading weather indicator data into Graphiti...")
    
    query = """
    MATCH (i:Indicator)
    RETURN i.name as name, i.type as type
    ORDER BY i.name
    """
    results = falkordb_client.execute_query(query)
    
    indicator_texts = []
    for row in results:
        indicator_texts.append(f"{row['name']} ({row['type']})")
    
    if indicator_texts:
        text = "Weather indicators available: " + ", ".join(indicator_texts) + ". These track temperature, precipitation, soil moisture, and vegetation conditions."
        await graphiti.add_episode(
            name="LDC_Weather_Indicators",
            episode_body=text,
            source=EpisodeType.text,
            source_description="LDC Weather Indicators",
            reference_time=datetime.now()
        )
    
    print(f"✓ Loaded weather indicator data ({len(results)} indicators)")

async def main():
    """Load all LDC data into Graphiti."""
    try:
        await load_commodity_data()
        await load_geography_data()
        await load_trade_flows()
        await load_production_areas()
        await load_balance_sheets()
        await load_weather_indicators()
        
        print("\n" + "="*60)
        print("✅ LDC data successfully loaded into Graphiti (Neo4j)!")
        print("="*60)
        print()
        print("Graphiti now has semantic embeddings for:")
        print("  - Commodity hierarchies")
        print("  - Geographic locations (countries, regions)")
        print("  - Trade flows between countries")
        print("  - Production areas")
        print("  - Balance sheets with components")
        print("  - Weather indicators")
        print()
        print("Natural language queries will now work via GraphRAG!")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j_driver.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
