"""Test BFS algorithm on tijara_kg graph"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 80)
print("Testing BFS on Tijara Knowledge Graph")
print("=" * 80)

# First, check what data exists
print("\n1. Checking graph statistics...")
try:
    response = requests.get(f"{BASE_URL}/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"   Nodes: {stats.get('nodes', {})}")
        print(f"   Relationships: {stats.get('relationships', {})}")
except Exception as e:
    print(f"   Error: {e}")

# Check a sample Production node
print("\n2. Fetching a sample Production node...")
try:
    response = requests.post(
        f"{BASE_URL}/query/cypher",
        json={"query": "MATCH (p:Production) RETURN p, id(p) as node_id LIMIT 1"},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        result = response.json()
        if result.get('results'):
            node = result['results'][0]
            print(f"   Node ID: {node.get('node_id')}")
            print(f"   Properties: {node.get('p', {})}")
            node_id = node.get('node_id')
        else:
            print("   No Production nodes found!")
            node_id = None
    else:
        print(f"   Error: {response.status_code}")
        node_id = None
except Exception as e:
    print(f"   Error: {e}")
    node_id = None

# Test BFS with empty relationship type
if node_id:
    print(f"\n3. Testing BFS from node {node_id} with empty relationship type...")
    try:
        query = f"""
        MATCH (p)
        WHERE id(p) = {node_id}
        CALL algo.BFS(p, 2, '')
        YIELD nodes, edges
        RETURN nodes, edges
        """
        response = requests.post(
            f"{BASE_URL}/query/cypher",
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   BFS Results: {result}")
        else:
            print(f"   Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   Error: {e}")

# Check relationships from Production nodes
print("\n4. Checking relationships from Production nodes...")
try:
    response = requests.post(
        f"{BASE_URL}/query/cypher",
        json={"query": "MATCH (p:Production)-[r]->(n) RETURN type(r) as rel_type, labels(n)[0] as target_label, count(*) as count"},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   Relationships: {result.get('results', [])}")
except Exception as e:
    print(f"   Error: {e}")

# Try BFS from a Commodity node
print("\n5. Testing BFS from Commodity node...")
try:
    query = """
    MATCH (c:Commodity {name: "Corn"})
    WITH c LIMIT 1
    CALL algo.BFS(c, 2, '')
    YIELD nodes, edges
    RETURN size(nodes) as node_count, size(edges) as edge_count
    """
    response = requests.post(
        f"{BASE_URL}/query/cypher",
        json={"query": query},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   BFS from Commodity: {result}")
    else:
        print(f"   Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 80)
print("BFS Testing Complete")
print("=" * 80)
