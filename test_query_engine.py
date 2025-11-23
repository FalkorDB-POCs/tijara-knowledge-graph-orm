"""Test query engine search directly"""

import sys
import asyncio
sys.path.insert(0, '/Users/shaharbiron/Documents/FalkorDB/Poc/LDC/tijara-knowledge-graph')

from src.core.falkordb_client import FalkorDBClient
from src.rag.query_engine import QueryEngine

# Create minimal mock objects
class MockGraphiti:
    def is_ready(self):
        return False

config_falkordb = {
    'host': 'localhost',
    'port': 6379,
    'graph_name': 'tijara_kg'
}

falkordb_client = FalkorDBClient(config_falkordb)
graphiti = MockGraphiti()
query_engine = QueryEngine(falkordb_client, graphiti, {})

# Test the entity extraction
question = "What is corn production in Germany?"
entities = query_engine._extract_entities(question)
print(f"Extracted entities: {entities}")

# Test direct search for one entity
entity = "Germany"
entity_variations = [entity.capitalize(), entity.upper(), entity.lower(), entity.title()]
entity_variations = list(set(entity_variations))

print(f"\nSearching for variations of '{entity}': {entity_variations}")

for entity_var in entity_variations:
    query = f'MATCH (n) WHERE n.country = "{entity_var}" RETURN n.commodity, n.country, n.region, n.indicator_type, n.value, n.year, n.month, n.unit LIMIT 2'
    print(f"\nQuery: {query}")
    results = falkordb_client.execute_query(query)
    print(f"Results ({len(results)}): {results}")
    if results:
        break

# Now test the full process_query
print("\n" + "="*80)
print("Testing full process_query:")
print("="*80)

async def test_query():
    result = await query_engine.process_query(
        question="What is corn production in Germany?",
        context={},
        return_sources=True
    )
    print(f"Answer: {result['answer'][:200]}...")
    print(f"Entities: {result.get('retrieved_entities', [])}")
    print(f"Subgraph data points: {len(result.get('subgraph', []))}")
    if result.get('subgraph'):
        print(f"First result: {result['subgraph'][0]}")

asyncio.run(test_query())
