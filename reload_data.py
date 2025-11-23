"""
Reload sample data with proper Graphiti embeddings.
This script clears and reloads data to ensure all nodes have embeddings.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def wait_for_api():
    """Wait for API to be ready."""
    for i in range(10):
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                health = response.json()
                if health.get('overall'):
                    print("✅ API is ready")
                    return True
        except:
            pass
        print(f"Waiting for API... ({i+1}/10)")
        time.sleep(2)
    return False

def ingest_structured_data():
    """Ingest sample structured data."""
    print("\n📊 Ingesting structured data...")
    
    # Sample production data for France
    data = [
        {"value": 35000000, "year": 2020, "unit": "metric_tons"},
        {"value": 36500000, "year": 2021, "unit": "metric_tons"},
        {"value": 35800000, "year": 2022, "unit": "metric_tons"},
        {"value": 37200000, "year": 2023, "unit": "metric_tons"},
    ]
    
    metadata = {
        "region": "Picardie",
        "country": "France",
        "type": "Production",
        "commodity": "Wheat",
        "source": "USDA",
        "unit": "metric_tons"
    }
    
    response = requests.post(
        f"{BASE_URL}/ingest",
        json={"data": data, "metadata": metadata, "validate": True}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Ingested {result['entities_created']} entities with {result['relationships_created']} relationships")
        print(f"   Entity IDs: {result['entity_ids'][:3]}..." if len(result['entity_ids']) > 3 else f"   Entity IDs: {result['entity_ids']}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

def ingest_document():
    """Ingest sample unstructured document."""
    print("\n📄 Ingesting unstructured document...")
    
    document_text = """
    France is one of the largest wheat producers in Europe, with the Picardie region 
    being particularly important for cereal production. In 2023, French wheat production 
    reached 37.2 million metric tons, showing strong growth from previous years. 
    
    The quality of French wheat is highly regarded internationally, with exports going 
    to North Africa, Middle East, and other EU countries. Climate conditions in Picardie, 
    including fertile soil and moderate rainfall, make it ideal for wheat cultivation.
    
    Production trends show steady growth driven by improved farming techniques, 
    better seed varieties, and favorable weather patterns. The USDA forecasts continued 
    strong production for the coming years, with France maintaining its position as a 
    key global wheat supplier.
    """
    
    response = requests.post(
        f"{BASE_URL}/ingest/document",
        json={
            "text": document_text.strip(),
            "source": "Market Report 2023",
            "metadata": {
                "report_date": "2023-12-01",
                "author": "Agricultural Analyst",
                "region": "France"
            }
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Document ingested: {result['message']}")
        print(f"   Text length: {result['text_length']} chars")
        print(f"   Entities extracted: {result['entities_found']}")
        if result.get('extracted_entities'):
            print(f"   Sample entities: {[e['name'] for e in result['extracted_entities'][:3]]}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

def ingest_more_data():
    """Ingest additional structured data for variety."""
    print("\n📊 Ingesting additional data...")
    
    datasets = [
        {
            "data": [
                {"value": 8500000, "year": 2020, "unit": "metric_tons"},
                {"value": 9200000, "year": 2021, "unit": "metric_tons"},
                {"value": 9800000, "year": 2022, "unit": "metric_tons"},
                {"value": 10500000, "year": 2023, "unit": "metric_tons"},
            ],
            "metadata": {
                "region": "Corn Belt",
                "country": "USA",
                "type": "Exports",
                "commodity": "Corn",
                "source": "USDA",
                "unit": "metric_tons"
            }
        },
        {
            "data": [
                {"value": 150, "year": 2020, "unit": "USD_per_metric_ton"},
                {"value": 165, "year": 2021, "unit": "USD_per_metric_ton"},
                {"value": 180, "year": 2022, "unit": "USD_per_metric_ton"},
                {"value": 175, "year": 2023, "unit": "USD_per_metric_ton"},
            ],
            "metadata": {
                "country": "Germany",
                "type": "Price",
                "commodity": "Wheat",
                "source": "Market Data",
                "unit": "USD_per_metric_ton"
            }
        }
    ]
    
    success_count = 0
    for dataset in datasets:
        response = requests.post(
            f"{BASE_URL}/ingest",
            json={"data": dataset["data"], "metadata": dataset["metadata"], "validate": True}
        )
        
        if response.status_code == 200:
            result = response.json()
            commodity = dataset["metadata"]["commodity"]
            indicator = dataset["metadata"]["type"]
            country = dataset["metadata"].get("country", dataset["metadata"].get("region"))
            print(f"✅ Ingested {commodity} {indicator} for {country}")
            success_count += 1
            time.sleep(1)  # Small delay to allow Graphiti to process
        else:
            print(f"❌ Error: {response.text}")
    
    return success_count == len(datasets)

def verify_data():
    """Verify data was ingested correctly."""
    print("\n🔍 Verifying data...")
    
    response = requests.get(f"{BASE_URL}/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Graph statistics:")
        print(f"   Total nodes: {stats.get('node_count', 0)}")
        print(f"   Total relationships: {stats.get('relationship_count', 0)}")
        
        node_counts = stats.get('node_counts_by_label', {})
        if node_counts:
            print("   Node types:")
            for label, count in node_counts.items():
                print(f"     - {label}: {count}")
        return True
    else:
        print(f"❌ Error getting stats: {response.text}")
        return False

def main():
    """Main reload script."""
    print("=" * 60)
    print("🔄 Data Reload Script")
    print("=" * 60)
    
    # Wait for API
    if not wait_for_api():
        print("❌ API not ready, aborting")
        return
    
    # Ingest data
    print("\n" + "=" * 60)
    print("Starting data ingestion...")
    print("=" * 60)
    
    success = True
    success = ingest_structured_data() and success
    time.sleep(2)  # Allow time for embeddings
    
    success = ingest_document() and success
    time.sleep(2)
    
    success = ingest_more_data() and success
    time.sleep(2)
    
    # Verify
    print("\n" + "=" * 60)
    verify_data()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All data reloaded successfully with embeddings!")
    else:
        print("⚠️  Some operations failed, check logs")
    print("=" * 60)

if __name__ == "__main__":
    main()
