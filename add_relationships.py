"""
Add relationships/edges to existing nodes in the knowledge graph
This will create concept nodes and link data nodes to them
"""

import sys
sys.path.insert(0, '/Users/shaharbiron/Documents/FalkorDB/Poc/LDC/tijara-knowledge-graph')

from src.core.falkordb_client import FalkorDBClient
import yaml

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

client = FalkorDBClient(config['falkordb'])

print("=" * 80)
print("Adding Relationships to Tijara Knowledge Graph")
print("=" * 80)

# Step 1: Create concept nodes if they don't exist
print("\n1. Creating concept nodes...")

concepts = {
    'Commodity': ['Corn', 'Wheat', 'Soybeans', 'Rice'],
    'Geography': ['USA', 'Germany', 'France', 'Brazil', 'China', 'Morocco', 'Iowa', 'Bavaria', 'Picardie', 'Mato Grosso'],
    'Indicator': ['Production', 'Demand', 'Exports', 'Stocks', 'Yield'],
    'Source': ['USDA', 'Eurostat', 'MARS', 'FAO', 'CONAB', 'China National Bureau of Statistics']
}

concept_nodes = {}

for concept_type, names in concepts.items():
    concept_nodes[concept_type] = {}
    for name in names:
        # Check if exists
        query = f'MATCH (n:{concept_type} {{name: "{name}"}}) RETURN id(n) as id LIMIT 1'
        result = client.execute_query(query)
        
        if result:
            node_id = result[0]['id']
            print(f"   Found existing {concept_type}: {name} (ID: {node_id})")
        else:
            # Create it
            node_id = client.create_entity(
                concept_type,
                {'name': name, 'type': concept_type.lower()}
            )
            print(f"   Created {concept_type}: {name} (ID: {node_id})")
        
        concept_nodes[concept_type][name] = node_id

print(f"\nTotal concept nodes: {sum(len(v) for v in concept_nodes.values())}")

# Step 2: Create relationships from data nodes to concept nodes
print("\n2. Creating relationships from data nodes to concepts...")

relationships_created = 0

# Get all data nodes (Production, Demand, etc.)
data_node_types = ['Production', 'Demand', 'Exports', 'Stocks', 'Yield']

for node_type in data_node_types:
    print(f"\n   Processing {node_type} nodes...")
    
    # Get all nodes of this type
    query = f'MATCH (n:{node_type}) RETURN id(n) as id, n.commodity as commodity, n.country as country, n.region as region, n.data_source as source LIMIT 100'
    nodes = client.execute_query(query)
    
    print(f"   Found {len(nodes)} {node_type} nodes")
    
    for node in nodes:
        node_id = node['id']
        
        # Create HAS_COMMODITY relationship
        if node['commodity'] and node['commodity'] in concept_nodes['Commodity']:
            try:
                rel_id = client.create_relationship(
                    source_id=str(node_id),
                    target_id=concept_nodes['Commodity'][node['commodity']],
                    relationship_type='HAS_COMMODITY'
                )
                relationships_created += 1
            except Exception as e:
                pass  # May already exist
        
        # Create HAS_GEOGRAPHY relationship (country or region)
        geo_name = node['region'] if node['region'] else node['country']
        if geo_name and geo_name in concept_nodes['Geography']:
            try:
                rel_id = client.create_relationship(
                    source_id=str(node_id),
                    target_id=concept_nodes['Geography'][geo_name],
                    relationship_type='HAS_GEOGRAPHY'
                )
                relationships_created += 1
            except Exception as e:
                pass
        
        # Create HAS_INDICATOR relationship
        if node_type in concept_nodes['Indicator']:
            try:
                rel_id = client.create_relationship(
                    source_id=str(node_id),
                    target_id=concept_nodes['Indicator'][node_type],
                    relationship_type='HAS_INDICATOR'
                )
                relationships_created += 1
            except Exception as e:
                pass
        
        # Create HAS_SOURCE relationship
        if node['source'] and node['source'] in concept_nodes['Source']:
            try:
                rel_id = client.create_relationship(
                    source_id=str(node_id),
                    target_id=concept_nodes['Source'][node['source']],
                    relationship_type='HAS_SOURCE'
                )
                relationships_created += 1
            except Exception as e:
                pass

print(f"\n✅ Created {relationships_created} relationships")

# Step 3: Verify relationships
print("\n3. Verifying relationships...")

rel_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count"
rel_counts = client.execute_query(rel_query)

print("\nRelationship counts:")
for rel in rel_counts:
    print(f"   {rel['type']}: {rel['count']}")

# Get updated stats
print("\n4. Updated graph statistics...")
stats = client.get_graph_statistics()

print("\nNode counts:")
for node_type, count in stats['nodes'].items():
    print(f"   {node_type}: {count}")

print("\nTotal relationships:", sum(stats['relationships'].values()))

print("\n" + "=" * 80)
print("✅ Relationships successfully added to the knowledge graph!")
print("=" * 80)
