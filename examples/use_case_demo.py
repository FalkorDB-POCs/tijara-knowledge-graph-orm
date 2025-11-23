"""
Tijara Knowledge Graph - Use Case Demonstrations
Shows all 5 key use cases from the business document
"""

import asyncio
import yaml
from shapely.geometry import Polygon

from src.core.knowledge_graph import TijaraKnowledgeGraph


async def main():
    """Run all use case demonstrations."""
    
    # Load configuration
    with open('../config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize knowledge graph
    kg = TijaraKnowledgeGraph(config)
    
    print("=" * 80)
    print("Tijara Knowledge Graph - Use Case Demonstrations")
    print("=" * 80)
    
    # ========== Use Case 1: Trading Copilot - Quick Question Answering ==========
    print("\n📊 USE CASE 1: Trading Copilot - Quick Question Answering")
    print("-" * 80)
    
    questions = [
        "What commodities does France export to the United States?",
        "What commodities does USA export to France?",
        "What balance sheets are available in the system?",
        "Which commodities have production areas in France?"
    ]
    
    for question in questions:
        print(f"\nQ: {question}")
        result = await kg.query_natural_language(question)
        print(f"A: {result['answer']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Sources: {len(result['sources'])} references")
    
    # ========== Use Case 2: Data Science - Analytics & Exploration ==========
    print("\n\n🔬 USE CASE 2: Data Science - Analytics & Exploration")
    print("-" * 80)
    
    print("\n1. Finding most important trade network nodes (PageRank)...")
    try:
        exporters = kg.analyze_graph(
            algorithm="pagerank",
            filters=None,
            parameters={"node_label": "Geography", "relationship_type": "TRADES_WITH"}
        )
        print(f"   Top trade network nodes by importance:")
        for i, (node_id, score) in enumerate(list(exporters.items())[:5], 1):
            print(f"   {i}. Node {node_id}: {score:.4f}")
    except Exception as e:
        print(f"   Note: PageRank analysis requires backend implementation: {e}")
    
    print("\n2. Extracting geography data as table...")
    try:
        df = kg.extract_dimensions(
            entity_type="Geography",
            filters={"level": 0},  # Countries only
            dimensions=["name", "gid_code", "level"],
            as_dataframe=True
        )
        print(f"   Extracted {len(df)} country records")
        print(df.head())
    except Exception as e:
        print(f"   Note: Dimension extraction requires backend implementation: {e}")
    
    print("\n3. Community detection on trade networks...")
    try:
        communities = kg.analyze_graph(
            algorithm="community",
            filters=None,
            parameters={"relationship_type": "TRADES_WITH"}
        )
        print(f"   Found {len(communities)} trade communities")
    except Exception as e:
        print(f"   Note: Community detection requires backend implementation: {e}")
    
    # ========== Use Case 3: Data Storage & Reference ==========
    print("\n\n💾 USE CASE 3: Data Storage & Reference")
    print("-" * 80)
    
    print("\n1. Storing new trade flow data...")
    try:
        result = await kg.ingest_data(
            data=[
                {"flow_value": 15000, "year": 2024, "month": 1},
                {"flow_value": 16200, "year": 2024, "month": 2}
            ],
            metadata={
                "from_country": "France",
                "to_country": "United States",
                "commodity": "Wheat",
                "flow_type": "export_import",
                "source": "LDC"
            }
        )
        print(f"   ✅ Created {result['entities_created']} entities")
        print(f"   ✅ Created {result['relationships_created']} relationships")
        print(f"   Placement: {result['placement']['entity_type']}")
    except Exception as e:
        print(f"   Note: Data ingestion requires proper LDC schema mapping: {e}")
    
    print("\n2. Searching for French regions...")
    try:
        search_results = kg.search_entities(
            search_term="France",
            entity_types=["Geography"],
            limit=5
        )
        print(f"   Found {len(search_results)} related entities")
    except Exception as e:
        print(f"   Note: Entity search requires backend implementation: {e}")
    
    # ========== Use Case 4: Impact Analysis ==========
    print("\n\n🌍 USE CASE 4: Impact Analysis")
    print("-" * 80)
    
    print("\n1. Analyzing impact of weather event in French wheat region...")
    # Define weather event area (simplified polygon for northern France)
    try:
        france_wheat_polygon = Polygon([
            (2.0, 48.5), (4.0, 48.5), (4.0, 50.5), (2.0, 50.5), (2.0, 48.5)
        ])
        
        impacts = kg.find_impacts(
            event_geometry=france_wheat_polygon,
            event_type="drought",
            max_hops=5,
            impact_threshold=0.3
        )
        
        print(f"   Total impacted entities: {impacts['total_impacts']}")
        print(f"   Affected geographies: {len(impacts['affected_geographies'])}")
        print(f"\n   Top 5 impacted entities:")
        for i, entity in enumerate(impacts['impacted_entities'][:5], 1):
            print(f"   {i}. {entity['entity_type']}: Impact Score {entity['impact_score']:.2f}")
            print(f"      Path length: {len(entity['path'])} hops")
    except Exception as e:
        print(f"   Note: Impact analysis requires spatial capabilities: {e}")
    
    # ========== Use Case 5: Model Documentation & Discovery ==========
    print("\n\n📚 USE CASE 5: Model Documentation & Discovery")
    print("-" * 80)
    
    print("\n1. Exploring ontology schema...")
    schema = kg.explore_schema()
    print(f"   Concepts defined: {len(schema.get('concepts', {}))}")
    print(f"   Relationship types: {len(schema.get('relationships', {}))}")
    print(f"   Data sources: {len(schema.get('data_sources', {}))}")
    
    print("\n2. Checking LDC trade flow coverage...")
    # Query for trade flow coverage
    query = """
    MATCH (g1:Geography)-[t:TRADES_WITH]->(g2:Geography)
    RETURN g1.name as from_country, 
           g2.name as to_country,
           count(t) as flow_count,
           collect(DISTINCT t.commodity) as commodities
    ORDER BY flow_count DESC
    """
    try:
        coverage = kg.execute_cypher(query)
        print(f"   Trade routes in system: {len(coverage)}")
        for route in coverage[:5]:
            print(f"   - {route['from_country']} → {route['to_country']}: {route['flow_count']} flows")
    except Exception as e:
        print(f"   Note: Query execution requires backend implementation: {e}")
    
    print("\n3. Getting entity version history...")
    # Get history for a specific entity (example)
    entity_id = "12345"  # Would be actual entity ID
    # history = kg.get_entity_history(entity_id, include_relationships=True)
    print(f"   [Would show version history for entity {entity_id}]")
    
    # ========== Additional: Graph Statistics ==========
    print("\n\n📈 GRAPH STATISTICS")
    print("-" * 80)
    
    stats = kg.get_statistics()
    print(f"\nNode counts:")
    for node_type, count in stats.get('nodes', {}).items():
        print(f"   - {node_type}: {count:,}")
    
    print(f"\nRelationship counts:")
    for rel_type, count in stats.get('relationships', {}).items():
        print(f"   - {rel_type}: {count:,}")
    
    # ========== Health Check ==========
    print("\n\n❤️  HEALTH CHECK")
    print("-" * 80)
    health = kg.health_check()
    print(f"   FalkorDB: {'✅' if health['falkordb'] else '❌'}")
    print(f"   Graphiti: {'✅' if health['graphiti'] else '❌'}")
    print(f"   Overall: {'✅' if health['overall'] else '❌'}")
    
    print("\n" + "=" * 80)
    print("✅ All use cases demonstrated successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
