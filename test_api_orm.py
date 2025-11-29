"""
Test script for API endpoints after ORM migration.
Tests key endpoints: /search, /stats, /query
"""

import sys
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health check endpoint."""
    print("Testing /health...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_stats():
    """Test statistics endpoint."""
    print("\nTesting /stats...")
    response = requests.get(f"{BASE_URL}/stats")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Nodes: {data.get('nodes', {})}")
    print(f"Relationships: {data.get('relationships', {})}")
    return response.status_code == 200

def test_search():
    """Test search endpoint with ORM."""
    print("\nTesting /search?q=wheat...")
    response = requests.get(f"{BASE_URL}/search", params={"q": "wheat", "limit": 5})
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Query: {data.get('query')}")
    print(f"Results count: {len(data.get('results', []))}")
    for result in data.get('results', [])[:3]:
        print(f"  - {result.get('type')}: {result.get('name')}")
    return response.status_code == 200

def test_search_france():
    """Test search for France."""
    print("\nTesting /search?q=france...")
    response = requests.get(f"{BASE_URL}/search", params={"q": "france", "limit": 5})
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Results count: {len(data.get('results', []))}")
    for result in data.get('results', []):
        print(f"  - {result.get('type')}: {result.get('name')}")
    return response.status_code == 200

def test_schema():
    """Test schema endpoint."""
    print("\nTesting /schema...")
    response = requests.get(f"{BASE_URL}/schema")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Relationships: {data.get('relationships', [])}")
    return response.status_code == 200

def test_query():
    """Test natural language query endpoint."""
    print("\nTesting /query (natural language)...")
    response = requests.post(
        f"{BASE_URL}/query",
        json={
            "question": "What commodities are related to wheat?",
            "return_sources": True
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Answer preview: {data.get('answer', '')[:200]}...")
        print(f"Confidence: {data.get('confidence')}")
        print(f"Entities: {data.get('retrieved_entities', [])}")
        print(f"Sources: {len(data.get('sources', []))} sources")
    else:
        print(f"Error: {response.text}")
    return response.status_code == 200

def main():
    """Run all tests."""
    print("=" * 60)
    print("API ORM Migration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health),
        ("Statistics", test_stats),
        ("Search - Wheat", test_search),
        ("Search - France", test_search_france),
        ("Schema", test_schema),
        ("Natural Language Query", test_query),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"ERROR: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    return 0 if passed_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())
