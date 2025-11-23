"""Test GraphRAG queries"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Test queries
queries = [
    "What are the relevant information on the demand of corn in Germany?",
    "What is corn production in the USA?",
    "Tell me about wheat yield in France",
    "What data do we have on soybeans from Brazil?"
]

print("=" * 80)
print("Testing GraphRAG Queries")
print("=" * 80)

for i, question in enumerate(queries, 1):
    print(f"\n[{i}/{len(queries)}] Query: {question}")
    print("-" * 80)
    
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={"question": question, "return_sources": True},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Answer: {result['answer'][:300]}...")
            print(f"Confidence: {result['confidence']}")
            print(f"Entities Found: {result.get('retrieved_entities', [])}")
            print(f"Data Points Retrieved: {len(result.get('subgraph', []))}")
            
            # Show some data if available
            if result.get('subgraph'):
                print("\nSample Data:")
                for item in result['subgraph'][:3]:
                    # Data is now in flat format with n. prefix
                    commodity = item.get('n.commodity', 'N/A')
                    indicator = item.get('n.indicator_type', 'N/A')
                    country = item.get('n.country', item.get('n.region', 'N/A'))
                    value = item.get('n.value', 'N/A')
                    year = item.get('n.year', 'N/A')
                    month = item.get('n.month', '')
                    unit = item.get('n.unit', '')
                    
                    time_str = f"{year}"
                    if month:
                        time_str = f"{month}/{year}"
                    print(f"  - {commodity} {indicator} in {country}: {value} {unit} ({time_str})")
        else:
            print(f"Error: {response.status_code}")
            print(response.text[:200])
    
    except Exception as e:
        print(f"Exception: {e}")

print("\n" + "=" * 80)
print("Testing Complete")
print("=" * 80)
