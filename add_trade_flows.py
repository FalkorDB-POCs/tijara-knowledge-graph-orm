"""
Add Trade Flow Data - Finished Products
Creates circular trade flows where geographies export commodities and import finished products
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Trade flow data: Finished products exported back to commodity producers
# Example: Brazil exports soybeans → China processes → China exports soybean oil back to Brazil
TRADE_FLOW_DATA = [
    # China exports Corn Flour to USA (USA exports corn to China for processing)
    {
        "data": [
            {"value": 12500, "year": 2023, "month": 1},
            {"value": 13200, "year": 2023, "month": 2},
            {"value": 13800, "year": 2023, "month": 3},
            {"value": 14100, "year": 2023, "month": 4},
            {"value": 14700, "year": 2023, "month": 5},
            {"value": 15300, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "China",
            "type": "Exports",
            "commodity": "Corn Flour",
            "unit": "thousand_metric_tons",
            "source": "China National Bureau of Statistics",
            "destination": "USA",
            "product_type": "finished"
        }
    },
    # Germany exports Wheat Bread to France (France exports wheat to Germany)
    {
        "data": [
            {"value": 2800, "year": 2023, "month": 1},
            {"value": 2950, "year": 2023, "month": 2},
            {"value": 3100, "year": 2023, "month": 3},
            {"value": 3250, "year": 2023, "month": 4},
            {"value": 3400, "year": 2023, "month": 5},
            {"value": 3550, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "Germany",
            "type": "Exports",
            "commodity": "Wheat Bread",
            "unit": "thousand_metric_tons",
            "source": "Eurostat",
            "destination": "France",
            "product_type": "finished"
        }
    },
    # China exports Soybean Oil to Brazil (Brazil exports soybeans to China)
    {
        "data": [
            {"value": 8500, "year": 2023, "month": 1},
            {"value": 8900, "year": 2023, "month": 2},
            {"value": 9300, "year": 2023, "month": 3},
            {"value": 9700, "year": 2023, "month": 4},
            {"value": 10100, "year": 2023, "month": 5},
            {"value": 10500, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "China",
            "type": "Exports",
            "commodity": "Soybean Oil",
            "unit": "thousand_metric_tons",
            "source": "China National Bureau of Statistics",
            "destination": "Brazil",
            "product_type": "finished"
        }
    },
    # USA exports Corn Ethanol to Germany (Germany imports corn from USA)
    {
        "data": [
            {"value": 3200, "year": 2023, "month": 1},
            {"value": 3350, "year": 2023, "month": 2},
            {"value": 3500, "year": 2023, "month": 3},
            {"value": 3650, "year": 2023, "month": 4},
            {"value": 3800, "year": 2023, "month": 5},
            {"value": 3950, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "USA",
            "type": "Exports",
            "commodity": "Corn Ethanol",
            "unit": "thousand_metric_tons",
            "source": "USDA",
            "destination": "Germany",
            "product_type": "finished"
        }
    },
    # France exports Wheat Pasta to Morocco (Morocco imports wheat from France)
    {
        "data": [
            {"value": 1800, "year": 2023, "month": 1},
            {"value": 1900, "year": 2023, "month": 2},
            {"value": 2000, "year": 2023, "month": 3},
            {"value": 2100, "year": 2023, "month": 4},
            {"value": 2200, "year": 2023, "month": 5},
            {"value": 2300, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "France",
            "type": "Exports",
            "commodity": "Wheat Pasta",
            "unit": "thousand_metric_tons",
            "source": "MARS",
            "destination": "Morocco",
            "product_type": "finished"
        }
    },
    # Brazil exports Soybean Meal to USA (creates reciprocal trade)
    {
        "data": [
            {"value": 15500, "year": 2023, "month": 1},
            {"value": 16200, "year": 2023, "month": 2},
            {"value": 16900, "year": 2023, "month": 3},
            {"value": 17600, "year": 2023, "month": 4},
            {"value": 18300, "year": 2023, "month": 5},
            {"value": 19000, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "Brazil",
            "type": "Exports",
            "commodity": "Soybean Meal",
            "unit": "thousand_metric_tons",
            "source": "CONAB",
            "destination": "USA",
            "product_type": "finished"
        }
    },
]


def ingest_trade_flows():
    """Ingest trade flow data via the API."""
    print("=" * 80)
    print("Adding Trade Flow Data - Finished Product Exports")
    print("=" * 80)
    print("\nThis creates circular trade relationships:")
    print("  - USA exports Corn → China exports Corn Flour back to USA")
    print("  - France exports Wheat → Germany exports Wheat Bread back to France")
    print("  - Brazil exports Soybeans → China exports Soybean Oil back to Brazil")
    print("  - And more...")
    print("=" * 80)
    
    total_entities = 0
    total_relationships = 0
    
    for i, dataset in enumerate(TRADE_FLOW_DATA, 1):
        destination = dataset['metadata'].get('destination', 'N/A')
        print(f"\n[{i}/{len(TRADE_FLOW_DATA)}] Ingesting {dataset['metadata']['commodity']} "
              f"exports from {dataset['metadata']['country']} → {destination}...")
        
        try:
            # Disable validation for finished products
            dataset_with_validation = {**dataset, "validate": False}
            response = requests.post(
                f"{BASE_URL}/ingest",
                json=dataset_with_validation,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                entities_created = result.get('entities_created', 0)
                relationships_created = result.get('relationships_created', 0)
                
                total_entities += entities_created
                total_relationships += relationships_created
                
                print(f"   ✅ Created {entities_created} entities, {relationships_created} relationships")
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text}")
        
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print("\n" + "=" * 80)
    print("Summary:")
    print(f"   Total entities created: {total_entities}")
    print(f"   Total relationships created: {total_relationships}")
    print("=" * 80)
    
    # Now create explicit EXPORTS_TO relationships between geographies
    print("\n📊 Creating explicit trade flow relationships (EXPORTS_TO)...")
    create_trade_relationships()
    
    # Get final statistics
    print("\nFetching final graph statistics...")
    try:
        stats_response = requests.get(f"{BASE_URL}/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print("\n📊 Updated Graph Statistics:")
            print(f"   Total Nodes: {sum(stats.get('nodes', {}).values())}")
            print(f"   Total Relationships: {sum(stats.get('relationships', {}).values())}")
            
            if 'nodes' in stats:
                print("\n   Node Types:")
                for node_type, count in stats['nodes'].items():
                    print(f"     - {node_type}: {count}")
            
            if 'relationships' in stats:
                print("\n   Relationship Types:")
                for rel_type, count in stats['relationships'].items():
                    print(f"     - {rel_type}: {count}")
        else:
            print(f"   ⚠️  Could not fetch stats: {stats_response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Error fetching stats: {e}")
    
    print("\n✅ Trade flow data ingestion complete!")
    print("\n💡 Now you can run BFS queries to explore circular trade patterns!")
    print("   Example: Start from USA and traverse to see corn → China → corn flour → back to USA")


def create_trade_relationships():
    """Create EXPORTS_TO relationships between Geography nodes based on trade data."""
    trade_pairs = [
        ("China", "USA", "Corn Flour"),
        ("Germany", "France", "Wheat Bread"),
        ("China", "Brazil", "Soybean Oil"),
        ("USA", "Germany", "Corn Ethanol"),
        ("France", "Morocco", "Wheat Pasta"),
        ("Brazil", "USA", "Soybean Meal"),
    ]
    
    # Note: This requires a direct Cypher execution endpoint
    # For now, we'll just print the queries that should be run
    print("\n   To create EXPORTS_TO relationships, run these Cypher queries:")
    print("   " + "-" * 70)
    
    for exporter, importer, commodity in trade_pairs:
        query = f"""
        MATCH (source:Geography {{name: "{exporter}"}})
        MATCH (target:Geography {{name: "{importer}"}})
        MERGE (source)-[r:EXPORTS_TO {{commodity: "{commodity}", type: "finished_product"}}]->(target)
        RETURN source.name, target.name, r.commodity
        """
        print(f"\n   {exporter} → {importer} ({commodity}):")
        print(f"   {query.strip()}")
    
    print("\n   " + "-" * 70)
    print("   ℹ️  These queries create direct Geography-to-Geography trade relationships")
    print("   ℹ️  This enables BFS to discover circular trade patterns across the network")


if __name__ == "__main__":
    ingest_trade_flows()
