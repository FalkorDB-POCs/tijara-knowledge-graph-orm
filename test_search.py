"""Test FalkorDB search directly"""

import sys
sys.path.insert(0, '/Users/shaharbiron/Documents/FalkorDB/Poc/LDC/tijara-knowledge-graph')

from src.core.falkordb_client import FalkorDBClient

config = {
    'host': 'localhost',
    'port': 6379,
    'graph_name': 'tijara_kg'
}

client = FalkorDBClient(config)

# Test simple query
print("Test 1: Simple count query")
result = client.execute_query('MATCH (n) RETURN count(n) as count')
print(f"Result: {result}")

# Test search for Germany
print("\nTest 2: Search for Germany")
result = client.execute_query('MATCH (n) WHERE n.country = "Germany" RETURN n.commodity, n.country, n.value LIMIT 3')
print(f"Result: {result}")

# Test the case-insensitive query
print("\nTest 3: Case-insensitive query for germany")
entity = "germany"
query = f'''
MATCH (n)
WHERE n.country = "{entity.capitalize()}" OR n.country = "{entity.upper()}" OR n.country = "{entity.lower()}"
RETURN n
LIMIT 3
'''
print(f"Query: {query}")
result = client.execute_query(query)
print(f"Found {len(result)} results")
if result:
    print(f"First result: {result[0]}")
