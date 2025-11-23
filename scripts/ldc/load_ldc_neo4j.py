"""
Load LDC Dataset into Neo4j
Parallel loader that creates the same graph structure in Neo4j as in FalkorDB
"""

import csv
import os
import sys
from typing import Dict, List, Any
from neo4j import GraphDatabase
import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.yaml')
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

# Input data directory
INPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'ldc', 'input')

# Neo4j configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "six666six"
NEO4J_DATABASE = "neo4j"


class Neo4jLDCLoader:
    """Loads LDC commodity data from CSV files into Neo4j."""
    
    def __init__(self):
        """Initialize connection to Neo4j."""
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        print(f"✓ Connected to Neo4j at {NEO4J_URI}")
        
        # Track created entities for relationship linking
        self.entities = {
            'commodities': {},      # commodity_name -> node_id
            'geographies': {},      # gid_code -> node_id
            'balance_sheets': {},   # balance_sheet_id -> node_id
            'components': {},       # component_id -> node_id
            'indicators': {},       # indicator_id -> node_id
            'production_areas': {}  # production_area_id -> node_id
        }
    
    def close(self):
        """Close Neo4j connection."""
        self.driver.close()
    
    def clear_graph(self):
        """Clear the existing graph data."""
        print(f"\n🗑️  Clearing existing data in Neo4j...")
        with self.driver.session(database=NEO4J_DATABASE) as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("✓ Graph cleared")
    
    def read_csv(self, filename: str) -> List[Dict[str, str]]:
        """Read CSV file and return list of dictionaries."""
        filepath = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(filepath):
            print(f"⚠️  Warning: {filename} not found")
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    
    def load_commodity_hierarchy(self):
        """Load commodity hierarchy from CSV."""
        print("\n📦 Loading commodity hierarchy...")
        rows = self.read_csv('commodity_hierarchy.csv')
        
        if not rows:
            print("⚠️  No commodity data found")
            return
        
        with self.driver.session(database=NEO4J_DATABASE) as session:
            # Create hierarchy: Level0 -> Level1 -> Level2 -> Level3
            for row in rows:
                level0 = row['Level0'].strip() if row.get('Level0') else ''
                level1 = row['Level1'].strip() if row.get('Level1') else ''
                level2 = row['Level2'].strip() if row.get('Level2') else ''
                level3 = row['Level3'].strip() if row.get('Level3') else ''
                
                # Create or get Level0 (root category)
                if level0 and level0 not in self.entities['commodities']:
                    result = session.run("""
                        MERGE (c:Commodity:Category {name: $name})
                        SET c.level = 0, c.category = $name
                        RETURN id(c) as node_id
                    """, name=level0)
                    self.entities['commodities'][level0] = result.single()['node_id']
                
                # Create Level1 (main commodity)
                if level1 and level1 not in self.entities['commodities']:
                    result = session.run("""
                        MERGE (c:Commodity {name: $name})
                        SET c.level = 1, c.category = $category
                        RETURN id(c) as node_id
                    """, name=level1, category=level0)
                    node_id = result.single()['node_id']
                    self.entities['commodities'][level1] = node_id
                    
                    # Link to parent
                    if level0:
                        session.run("""
                            MATCH (parent:Commodity {name: $parent_name})
                            MATCH (child:Commodity {name: $child_name})
                            MERGE (child)-[:SUBCLASS_OF]->(parent)
                        """, parent_name=level0, child_name=level1)
                
                # Create Level2 (variety)
                if level2 and level2 not in self.entities['commodities']:
                    result = session.run("""
                        MERGE (c:Commodity:Variety {name: $name})
                        SET c.level = 2, c.category = $category, c.parent_commodity = $parent
                        RETURN id(c) as node_id
                    """, name=level2, category=level0, parent=level1)
                    node_id = result.single()['node_id']
                    self.entities['commodities'][level2] = node_id
                    
                    # Link to parent
                    if level1:
                        session.run("""
                            MATCH (parent:Commodity {name: $parent_name})
                            MATCH (child:Commodity {name: $child_name})
                            MERGE (child)-[:SUBCLASS_OF]->(parent)
                        """, parent_name=level1, child_name=level2)
                
                # Create Level3 (specific type)
                if level3 and level3 not in self.entities['commodities']:
                    result = session.run("""
                        MERGE (c:Commodity:Type {name: $name})
                        SET c.level = 3, c.category = $category, c.parent_commodity = $parent
                        RETURN id(c) as node_id
                    """, name=level3, category=level0, parent=level2 or level1)
                    node_id = result.single()['node_id']
                    self.entities['commodities'][level3] = node_id
                    
                    # Link to parent
                    parent_name = level2 or level1
                    if parent_name:
                        session.run("""
                            MATCH (parent:Commodity {name: $parent_name})
                            MATCH (child:Commodity {name: $child_name})
                            MERGE (child)-[:SUBCLASS_OF]->(parent)
                        """, parent_name=parent_name, child_name=level3)
        
        print(f"✓ Loaded {len(self.entities['commodities'])} commodity nodes")
    
    def load_geometries(self):
        """Load geographic hierarchy from CSV."""
        print("\n🌍 Loading geographic hierarchy...")
        rows = self.read_csv('geometries.csv')
        
        if not rows:
            print("⚠️  No geometry data found")
            return
        
        # Sort by level to ensure parents are created first
        rows_sorted = sorted(rows, key=lambda x: int(x['level']))
        
        with self.driver.session(database=NEO4J_DATABASE) as session:
            for row in rows_sorted:
                gid_code = row['gid_code'].strip()
                level = int(row['level'])
                name = row['name'].strip()
                parent_gid = row['parent_gid_code'].strip() if row['parent_gid_code'] else None
                
                # Determine geography type based on level
                if level == 0:
                    geo_type = "Country"
                elif level == 1:
                    geo_type = "Region"
                elif level == 2:
                    geo_type = "SubRegion"
                else:
                    geo_type = "Geography"
                
                # Create geography node
                result = session.run(f"""
                    MERGE (g:Geography:{geo_type} {{gid_code: $gid_code}})
                    SET g.name = $name, g.level = $level
                    RETURN id(g) as node_id
                """, gid_code=gid_code, name=name, level=level)
                node_id = result.single()['node_id']
                self.entities['geographies'][gid_code] = node_id
                
                # Link to parent geography
                if parent_gid and parent_gid in self.entities['geographies']:
                    session.run("""
                        MATCH (parent:Geography {gid_code: $parent_gid})
                        MATCH (child:Geography {gid_code: $child_gid})
                        MERGE (child)-[:LOCATED_IN]->(parent)
                    """, parent_gid=parent_gid, child_gid=gid_code)
        
        print(f"✓ Loaded {len(self.entities['geographies'])} geography nodes")
    
    def load_indicator_definitions(self):
        """Load weather indicator definitions from CSV."""
        print("\n🌡️  Loading weather indicator definitions...")
        rows = self.read_csv('indicator_definition.csv')
        
        if not rows:
            print("⚠️  No indicator definitions found")
            return
        
        with self.driver.session(database=NEO4J_DATABASE) as session:
            for row in rows:
                indicator_id = row['id'].strip()
                
                session.run("""
                    MERGE (i:Indicator:WeatherIndicator {indicator_id: $indicator_id})
                    SET i.name = $name,
                        i.indicator_type = $indicator_type,
                        i.source_name = $source_name,
                        i.forecast_days = $forecast_days,
                        i.forecast_type = $forecast_type,
                        i.unit = $unit
                    RETURN id(i) as node_id
                """, 
                    indicator_id=indicator_id,
                    name=row['name'].strip(),
                    indicator_type=row['indicator'].strip(),
                    source_name=row['sourceName'].strip(),
                    forecast_days=int(row['forecastDays']) if row['forecastDays'] else 0,
                    forecast_type=row['forecastType'].strip(),
                    unit=row['unit'].strip()
                )
                self.entities['indicators'][indicator_id] = indicator_id
        
        print(f"✓ Loaded {len(self.entities['indicators'])} indicator definitions")
    
    def load_production_areas(self):
        """Load production areas from CSV."""
        print("\n🌾 Loading production areas...")
        rows = self.read_csv('production_areas.csv')
        
        if not rows:
            print("⚠️  No production area data found")
            return
        
        unique_areas = {}
        
        with self.driver.session(database=NEO4J_DATABASE) as session:
            for row in rows:
                prod_area_id = row['production_area_id'].strip()
                crop_mask_id = row['crop_mask_id'].strip()
                gid_code = row['gid_code'].strip()
                commodity_name = row['commodity_name'].strip()
                season = row['season'].strip() if row['season'] else None
                
                # Create production area node (once per unique ID)
                if prod_area_id not in unique_areas:
                    session.run("""
                        MERGE (p:ProductionArea {production_area_id: $prod_area_id})
                        SET p.crop_mask_id = $crop_mask_id,
                            p.commodity = $commodity,
                            p.season = $season
                    """,
                        prod_area_id=prod_area_id,
                        crop_mask_id=crop_mask_id,
                        commodity=commodity_name,
                        season=season
                    )
                    unique_areas[prod_area_id] = True
                    self.entities['production_areas'][prod_area_id] = prod_area_id
                    
                    # Link to commodity
                    if commodity_name in self.entities['commodities']:
                        session.run("""
                            MATCH (p:ProductionArea {production_area_id: $prod_id})
                            MATCH (c:Commodity {name: $commodity_name})
                            MERGE (p)-[:PRODUCES]->(c)
                        """, prod_id=prod_area_id, commodity_name=commodity_name)
                
                # Link production area to geography
                if gid_code in self.entities['geographies']:
                    session.run("""
                        MATCH (p:ProductionArea {production_area_id: $prod_id})
                        MATCH (g:Geography {gid_code: $gid_code})
                        MERGE (p)-[:LOCATED_IN]->(g)
                    """, prod_id=prod_area_id, gid_code=gid_code)
        
        print(f"✓ Loaded {len(unique_areas)} unique production areas")
    
    def load_balance_sheets(self):
        """Load balance sheets from CSV."""
        print("\n📊 Loading balance sheets...")
        rows = self.read_csv('balance_sheet.csv')
        
        if not rows:
            print("⚠️  No balance sheet data found")
            return
        
        with self.driver.session(database=NEO4J_DATABASE) as session:
            for row in rows:
                bs_id = row['id'].strip()
                gid = row['gid'].strip()
                product_name = row['product_name'].strip()
                season = row['product_season'].strip() if row['product_season'] else None
                
                session.run("""
                    MERGE (b:BalanceSheet {balance_sheet_id: $bs_id})
                    SET b.gid = $gid,
                        b.product_name = $product_name,
                        b.season = $season
                """, bs_id=bs_id, gid=gid, product_name=product_name, season=season)
                self.entities['balance_sheets'][bs_id] = bs_id
                
                # Link to geography
                if gid in self.entities['geographies']:
                    session.run("""
                        MATCH (b:BalanceSheet {balance_sheet_id: $bs_id})
                        MATCH (g:Geography {gid_code: $gid})
                        MERGE (b)-[:FOR_GEOGRAPHY]->(g)
                    """, bs_id=bs_id, gid=gid)
                
                # Link to commodity
                if product_name in self.entities['commodities']:
                    session.run("""
                        MATCH (b:BalanceSheet {balance_sheet_id: $bs_id})
                        MATCH (c:Commodity {name: $product_name})
                        MERGE (b)-[:FOR_COMMODITY]->(c)
                    """, bs_id=bs_id, product_name=product_name)
        
        print(f"✓ Loaded {len(self.entities['balance_sheets'])} balance sheets")
    
    def load_balance_sheet_components(self):
        """Load balance sheet components from CSV."""
        print("\n📈 Loading balance sheet components...")
        rows = self.read_csv('balance_sheet_component.csv')
        
        if not rows:
            print("⚠️  No balance sheet component data found")
            return
        
        with self.driver.session(database=NEO4J_DATABASE) as session:
            for row in rows:
                bs_id = row['balancesheet_id'].strip()
                component_id = row['component_id'].strip()
                component_type = row['component_type'].strip()
                
                # Create component node
                session.run("""
                    MERGE (c:Component {component_id: $component_id})
                    SET c.component_type = $component_type
                """, component_id=component_id, component_type=component_type)
                self.entities['components'][component_id] = component_id
                
                # Link component to balance sheet
                if bs_id in self.entities['balance_sheets']:
                    session.run("""
                        MATCH (b:BalanceSheet {balance_sheet_id: $bs_id})
                        MATCH (c:Component {component_id: $component_id})
                        MERGE (b)-[:HAS_COMPONENT]->(c)
                    """, bs_id=bs_id, component_id=component_id)
        
        print(f"✓ Loaded {len(self.entities['components'])} balance sheet components")
    
    def load_flows(self):
        """Load trade flows from CSV."""
        print("\n🔄 Loading trade flows...")
        rows = self.read_csv('flows.csv')
        
        if not rows:
            print("⚠️  No flow data found")
            return
        
        flow_count = 0
        with self.driver.session(database=NEO4J_DATABASE) as session:
            for row in rows:
                source_country = row['source_country'].strip()
                dest_country = row['destination_country'].strip()
                commodity = row['commodity'].strip()
                season = row['commodity_season'].strip() if row['commodity_season'] else None
                source_ts_id = row['source_country_ts_id'].strip()
                dest_ts_id = row['destination_country_ts_id'].strip()
                
                # Create flow relationship
                if source_country in self.entities['geographies'] and dest_country in self.entities['geographies']:
                    session.run("""
                        MATCH (source:Geography {gid_code: $source_country})
                        MATCH (dest:Geography {gid_code: $dest_country})
                        MERGE (source)-[f:TRADES_WITH]->(dest)
                        SET f.commodity = $commodity,
                            f.season = $season,
                            f.source_ts_id = $source_ts_id,
                            f.destination_ts_id = $dest_ts_id,
                            f.flow_type = 'export_import'
                    """,
                        source_country=source_country,
                        dest_country=dest_country,
                        commodity=commodity,
                        season=season,
                        source_ts_id=source_ts_id,
                        dest_ts_id=dest_ts_id
                    )
                    flow_count += 1
        
        print(f"✓ Loaded {flow_count} trade flows")
    
    def create_indexes(self):
        """Create indexes for better query performance."""
        print("\n🔍 Creating indexes...")
        
        with self.driver.session(database=NEO4J_DATABASE) as session:
            indexes = [
                "CREATE INDEX commodity_name IF NOT EXISTS FOR (c:Commodity) ON (c.name)",
                "CREATE INDEX geography_gid IF NOT EXISTS FOR (g:Geography) ON (g.gid_code)",
                "CREATE INDEX geography_name IF NOT EXISTS FOR (g:Geography) ON (g.name)",
                "CREATE INDEX production_area_id IF NOT EXISTS FOR (p:ProductionArea) ON (p.production_area_id)",
                "CREATE INDEX balance_sheet_id IF NOT EXISTS FOR (b:BalanceSheet) ON (b.balance_sheet_id)",
                "CREATE INDEX indicator_id IF NOT EXISTS FOR (i:Indicator) ON (i.indicator_id)",
            ]
            
            for idx_query in indexes:
                try:
                    session.run(idx_query)
                except Exception as e:
                    # Index might already exist
                    pass
        
        print("✓ Indexes created")
    
    def print_statistics(self):
        """Print graph statistics."""
        print("\n" + "="*60)
        print("📊 Neo4j Graph Statistics")
        print("="*60)
        
        with self.driver.session(database=NEO4J_DATABASE) as session:
            # Node counts
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as type, count(n) as count
                ORDER BY count DESC
            """)
            
            print("\nNodes:")
            total_nodes = 0
            for record in result:
                node_type = record['type']
                count = record['count']
                total_nodes += count
                print(f"  {node_type}: {count}")
            print(f"  TOTAL: {total_nodes}")
            
            # Relationship counts
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            
            print("\nRelationships:")
            total_rels = 0
            for record in result:
                rel_type = record['type']
                count = record['count']
                total_rels += count
                print(f"  {rel_type}: {count}")
            print(f"  TOTAL: {total_rels}")
        
        print("\n" + "="*60)
    
    def load_all(self):
        """Load all data from CSV files."""
        print("\n" + "="*60)
        print("🚀 Neo4j LDC Data Loader")
        print("="*60)
        print(f"Input directory: {INPUT_DIR}")
        print(f"Target database: {NEO4J_DATABASE}")
        
        # Clear existing data
        self.clear_graph()
        
        # Load data in order (respecting dependencies)
        self.load_commodity_hierarchy()
        self.load_geometries()
        self.load_indicator_definitions()
        self.load_production_areas()
        self.load_balance_sheets()
        self.load_balance_sheet_components()
        self.load_flows()
        
        # Create indexes
        self.create_indexes()
        
        # Print statistics
        self.print_statistics()
        
        print("\n✅ Neo4j LDC data loading complete!")
        print(f"Database '{NEO4J_DATABASE}' is ready for use.")


if __name__ == "__main__":
    loader = Neo4jLDCLoader()
    try:
        loader.load_all()
    finally:
        loader.close()
