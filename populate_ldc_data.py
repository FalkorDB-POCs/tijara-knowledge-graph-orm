"""
Populate LDC Knowledge Graph from Input CSV Files
Loads data from ../input-files-from-ldc/ into a new FalkorDB graph
"""

import csv
import os
import sys
from typing import Dict, List, Any
import falkordb
import yaml

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

# Input data directory
INPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'input-files-from-ldc')

# New graph name for LDC data
LDC_GRAPH_NAME = "ldc_graph"


class LDCDataLoader:
    """Loads LDC commodity data from CSV files into FalkorDB."""
    
    def __init__(self):
        """Initialize connection to FalkorDB."""
        falkordb_config = config['falkordb']
        
        self.client = falkordb.FalkorDB(
            host=falkordb_config['host'],
            port=falkordb_config['port'],
            username=falkordb_config.get('username'),
            password=falkordb_config.get('password'),
            ssl=falkordb_config.get('ssl', False)
        )
        
        self.graph = self.client.select_graph(LDC_GRAPH_NAME)
        print(f"✓ Connected to FalkorDB graph: {LDC_GRAPH_NAME}")
        
        # Track created entities for relationship linking
        self.entities = {
            'commodities': {},      # commodity_name -> node_id
            'geographies': {},      # gid_code -> node_id
            'balance_sheets': {},   # balance_sheet_id -> node_id
            'components': {},       # component_id -> node_id
            'indicators': {},       # indicator_id -> node_id
            'production_areas': {}  # production_area_id -> node_id
        }
    
    def clear_graph(self):
        """Clear the existing graph data."""
        print(f"\n🗑️  Clearing existing data in {LDC_GRAPH_NAME}...")
        try:
            self.graph.query("MATCH (n) DETACH DELETE n")
            print("✓ Graph cleared")
        except Exception as e:
            print(f"⚠️  Warning clearing graph: {e}")
    
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
        
        # Create hierarchy: Level0 -> Level1 -> Level2 -> Level3
        for row in rows:
            level0 = row['Level0'].strip() if row.get('Level0') else ''
            level1 = row['Level1'].strip() if row.get('Level1') else ''
            level2 = row['Level2'].strip() if row.get('Level2') else ''
            level3 = row['Level3'].strip() if row.get('Level3') else ''
            
            # Create or get Level0 (root category)
            if level0 and level0 not in self.entities['commodities']:
                query = """
                CREATE (c:Commodity:Category {
                    name: $name,
                    level: 0,
                    category: $name
                })
                RETURN id(c) as node_id
                """
                result = self.graph.query(query, {'name': level0})
                self.entities['commodities'][level0] = result.result_set[0][0]
            
            # Create Level1 (main commodity)
            if level1 and level1 not in self.entities['commodities']:
                query = """
                CREATE (c:Commodity {
                    name: $name,
                    level: 1,
                    category: $category
                })
                RETURN id(c) as node_id
                """
                result = self.graph.query(query, {
                    'name': level1,
                    'category': level0
                })
                node_id = result.result_set[0][0]
                self.entities['commodities'][level1] = node_id
                
                # Link to parent
                if level0:
                    parent_id = self.entities['commodities'][level0]
                    self.graph.query("""
                        MATCH (parent), (child)
                        WHERE id(parent) = $parent_id AND id(child) = $child_id
                        CREATE (child)-[:SUBCLASS_OF]->(parent)
                    """, {'parent_id': parent_id, 'child_id': node_id})
            
            # Create Level2 (variety)
            if level2 and level2 not in self.entities['commodities']:
                query = """
                CREATE (c:Commodity:Variety {
                    name: $name,
                    level: 2,
                    category: $category,
                    parent_commodity: $parent
                })
                RETURN id(c) as node_id
                """
                result = self.graph.query(query, {
                    'name': level2,
                    'category': level0,
                    'parent': level1
                })
                node_id = result.result_set[0][0]
                self.entities['commodities'][level2] = node_id
                
                # Link to parent
                if level1:
                    parent_id = self.entities['commodities'][level1]
                    self.graph.query("""
                        MATCH (parent), (child)
                        WHERE id(parent) = $parent_id AND id(child) = $child_id
                        CREATE (child)-[:SUBCLASS_OF]->(parent)
                    """, {'parent_id': parent_id, 'child_id': node_id})
            
            # Create Level3 (specific type)
            if level3 and level3 not in self.entities['commodities']:
                query = """
                CREATE (c:Commodity:Type {
                    name: $name,
                    level: 3,
                    category: $category,
                    parent_commodity: $parent
                })
                RETURN id(c) as node_id
                """
                result = self.graph.query(query, {
                    'name': level3,
                    'category': level0,
                    'parent': level2 or level1
                })
                node_id = result.result_set[0][0]
                self.entities['commodities'][level3] = node_id
                
                # Link to parent
                parent_name = level2 or level1
                if parent_name:
                    parent_id = self.entities['commodities'][parent_name]
                    self.graph.query("""
                        MATCH (parent), (child)
                        WHERE id(parent) = $parent_id AND id(child) = $child_id
                        CREATE (child)-[:SUBCLASS_OF]->(parent)
                    """, {'parent_id': parent_id, 'child_id': node_id})
        
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
        
        for row in rows_sorted:
            gid_code = row['gid_code'].strip()
            level = int(row['level'])
            name = row['name'].strip()
            parent_gid = row['parent_gid_code'].strip() if row['parent_gid_code'] else None
            
            # Determine geography type based on level
            if level == 0:
                geo_type = "Country"
            elif level == 1:
                geo_type = "Region"  # State in USA, Region in France
            elif level == 2:
                geo_type = "SubRegion"  # County in USA, Department in France
            else:
                geo_type = "Geography"
            
            # Create geography node
            query = f"""
            CREATE (g:Geography:{geo_type} {{
                gid_code: $gid_code,
                name: $name,
                level: $level
            }})
            RETURN id(g) as node_id
            """
            result = self.graph.query(query, {
                'gid_code': gid_code,
                'name': name,
                'level': level
            })
            node_id = result.result_set[0][0]
            self.entities['geographies'][gid_code] = node_id
            
            # Link to parent geography
            if parent_gid and parent_gid in self.entities['geographies']:
                parent_id = self.entities['geographies'][parent_gid]
                self.graph.query("""
                    MATCH (parent), (child)
                    WHERE id(parent) = $parent_id AND id(child) = $child_id
                    CREATE (child)-[:LOCATED_IN]->(parent)
                """, {'parent_id': parent_id, 'child_id': node_id})
        
        print(f"✓ Loaded {len(self.entities['geographies'])} geography nodes")
    
    def load_indicator_definitions(self):
        """Load weather indicator definitions from CSV."""
        print("\n🌡️  Loading weather indicator definitions...")
        rows = self.read_csv('indicator_definition.csv')
        
        if not rows:
            print("⚠️  No indicator definitions found")
            return
        
        for row in rows:
            indicator_id = row['id'].strip()
            
            query = """
            CREATE (i:Indicator:WeatherIndicator {
                indicator_id: $indicator_id,
                name: $name,
                indicator_type: $indicator_type,
                source_name: $source_name,
                forecast_days: $forecast_days,
                forecast_type: $forecast_type,
                unit: $unit
            })
            RETURN id(i) as node_id
            """
            result = self.graph.query(query, {
                'indicator_id': indicator_id,
                'name': row['name'].strip(),
                'indicator_type': row['indicator'].strip(),
                'source_name': row['sourceName'].strip(),
                'forecast_days': int(row['forecastDays']) if row['forecastDays'] else 0,
                'forecast_type': row['forecastType'].strip(),
                'unit': row['unit'].strip()
            })
            node_id = result.result_set[0][0]
            self.entities['indicators'][indicator_id] = node_id
        
        print(f"✓ Loaded {len(self.entities['indicators'])} indicator definitions")
    
    def load_production_areas(self):
        """Load production areas from CSV."""
        print("\n🌾 Loading production areas...")
        rows = self.read_csv('production_areas.csv')
        
        if not rows:
            print("⚠️  No production area data found")
            return
        
        # Track unique production areas (many rows share the same production_area_id)
        unique_areas = {}
        
        for row in rows:
            prod_area_id = row['production_area_id'].strip()
            crop_mask_id = row['crop_mask_id'].strip()
            gid_code = row['gid_code'].strip()
            commodity_name = row['commodity_name'].strip()
            season = row['season'].strip() if row['season'] else None
            
            # Create production area node (once per unique ID)
            if prod_area_id not in unique_areas:
                query = """
                CREATE (p:ProductionArea {
                    production_area_id: $prod_area_id,
                    crop_mask_id: $crop_mask_id,
                    commodity: $commodity,
                    season: $season
                })
                RETURN id(p) as node_id
                """
                result = self.graph.query(query, {
                    'prod_area_id': prod_area_id,
                    'crop_mask_id': crop_mask_id,
                    'commodity': commodity_name,
                    'season': season
                })
                node_id = result.result_set[0][0]
                unique_areas[prod_area_id] = node_id
                self.entities['production_areas'][prod_area_id] = node_id
                
                # Link to commodity
                if commodity_name in self.entities['commodities']:
                    commodity_id = self.entities['commodities'][commodity_name]
                    self.graph.query("""
                        MATCH (p), (c)
                        WHERE id(p) = $prod_id AND id(c) = $comm_id
                        CREATE (p)-[:PRODUCES]->(c)
                    """, {'prod_id': node_id, 'comm_id': commodity_id})
            
            # Link production area to geography
            prod_node_id = unique_areas[prod_area_id]
            if gid_code in self.entities['geographies']:
                geo_id = self.entities['geographies'][gid_code]
                # Check if relationship already exists
                check_query = """
                MATCH (p)-[r:LOCATED_IN]->(g)
                WHERE id(p) = $prod_id AND id(g) = $geo_id
                RETURN count(r) as cnt
                """
                check_result = self.graph.query(check_query, {
                    'prod_id': prod_node_id,
                    'geo_id': geo_id
                })
                
                if check_result.result_set[0][0] == 0:
                    self.graph.query("""
                        MATCH (p), (g)
                        WHERE id(p) = $prod_id AND id(g) = $geo_id
                        CREATE (p)-[:LOCATED_IN]->(g)
                    """, {'prod_id': prod_node_id, 'geo_id': geo_id})
        
        print(f"✓ Loaded {len(unique_areas)} unique production areas")
    
    def load_balance_sheets(self):
        """Load balance sheets from CSV."""
        print("\n📊 Loading balance sheets...")
        rows = self.read_csv('balance_sheet.csv')
        
        if not rows:
            print("⚠️  No balance sheet data found")
            return
        
        for row in rows:
            bs_id = row['id'].strip()
            gid = row['gid'].strip()
            product_name = row['product_name'].strip()
            season = row['product_season'].strip() if row['product_season'] else None
            
            query = """
            CREATE (b:BalanceSheet {
                balance_sheet_id: $bs_id,
                gid: $gid,
                product_name: $product_name,
                season: $season
            })
            RETURN id(b) as node_id
            """
            result = self.graph.query(query, {
                'bs_id': bs_id,
                'gid': gid,
                'product_name': product_name,
                'season': season
            })
            node_id = result.result_set[0][0]
            self.entities['balance_sheets'][bs_id] = node_id
            
            # Link to geography (country level)
            if gid in self.entities['geographies']:
                geo_id = self.entities['geographies'][gid]
                self.graph.query("""
                    MATCH (b), (g)
                    WHERE id(b) = $bs_id AND id(g) = $geo_id
                    CREATE (b)-[:FOR_GEOGRAPHY]->(g)
                """, {'bs_id': node_id, 'geo_id': geo_id})
            
            # Link to commodity
            if product_name in self.entities['commodities']:
                commodity_id = self.entities['commodities'][product_name]
                self.graph.query("""
                    MATCH (b), (c)
                    WHERE id(b) = $bs_id AND id(c) = $comm_id
                    CREATE (b)-[:FOR_COMMODITY]->(c)
                """, {'bs_id': node_id, 'comm_id': commodity_id})
        
        print(f"✓ Loaded {len(self.entities['balance_sheets'])} balance sheets")
    
    def load_balance_sheet_components(self):
        """Load balance sheet components from CSV."""
        print("\n📈 Loading balance sheet components...")
        rows = self.read_csv('balance_sheet_component.csv')
        
        if not rows:
            print("⚠️  No balance sheet component data found")
            return
        
        for row in rows:
            bs_id = row['balancesheet_id'].strip()
            component_id = row['component_id'].strip()
            component_type = row['component_type'].strip()
            
            # Create component node
            query = """
            CREATE (c:Component {
                component_id: $component_id,
                component_type: $component_type
            })
            RETURN id(c) as node_id
            """
            result = self.graph.query(query, {
                'component_id': component_id,
                'component_type': component_type
            })
            node_id = result.result_set[0][0]
            self.entities['components'][component_id] = node_id
            
            # Link component to balance sheet
            if bs_id in self.entities['balance_sheets']:
                bs_node_id = self.entities['balance_sheets'][bs_id]
                self.graph.query("""
                    MATCH (b), (c)
                    WHERE id(b) = $bs_id AND id(c) = $comp_id
                    CREATE (b)-[:HAS_COMPONENT]->(c)
                """, {'bs_id': bs_node_id, 'comp_id': node_id})
        
        print(f"✓ Loaded {len(self.entities['components'])} balance sheet components")
    
    def load_flows(self):
        """Load trade flows from CSV."""
        print("\n🔄 Loading trade flows...")
        rows = self.read_csv('flows.csv')
        
        if not rows:
            print("⚠️  No flow data found")
            return
        
        flow_count = 0
        for row in rows:
            source_country = row['source_country'].strip()
            dest_country = row['destination_country'].strip()
            commodity = row['commodity'].strip()
            season = row['commodity_season'].strip() if row['commodity_season'] else None
            source_ts_id = row['source_country_ts_id'].strip()
            dest_ts_id = row['destination_country_ts_id'].strip()
            
            # Get geography node IDs
            source_geo_id = self.entities['geographies'].get(source_country)
            dest_geo_id = self.entities['geographies'].get(dest_country)
            
            if not source_geo_id or not dest_geo_id:
                print(f"⚠️  Skipping flow: missing geography {source_country} or {dest_country}")
                continue
            
            # Create flow relationship
            query = """
            MATCH (source), (dest)
            WHERE id(source) = $source_id AND id(dest) = $dest_id
            CREATE (source)-[f:TRADES_WITH {
                commodity: $commodity,
                season: $season,
                source_ts_id: $source_ts_id,
                destination_ts_id: $dest_ts_id,
                flow_type: 'export_import'
            }]->(dest)
            RETURN id(f) as flow_id
            """
            result = self.graph.query(query, {
                'source_id': source_geo_id,
                'dest_id': dest_geo_id,
                'commodity': commodity,
                'season': season,
                'source_ts_id': source_ts_id,
                'dest_ts_id': dest_ts_id
            })
            flow_count += 1
        
        print(f"✓ Loaded {flow_count} trade flows")
    
    def create_indexes(self):
        """Create indexes for better query performance."""
        print("\n🔍 Creating indexes...")
        
        indexes = [
            "CREATE INDEX FOR (c:Commodity) ON (c.name)",
            "CREATE INDEX FOR (g:Geography) ON (g.gid_code)",
            "CREATE INDEX FOR (g:Geography) ON (g.name)",
            "CREATE INDEX FOR (p:ProductionArea) ON (p.production_area_id)",
            "CREATE INDEX FOR (b:BalanceSheet) ON (b.balance_sheet_id)",
            "CREATE INDEX FOR (i:Indicator) ON (i.indicator_id)",
        ]
        
        for idx_query in indexes:
            try:
                self.graph.query(idx_query)
            except Exception as e:
                # Index might already exist
                pass
        
        print("✓ Indexes created")
    
    def print_statistics(self):
        """Print graph statistics."""
        print("\n" + "="*60)
        print("📊 LDC Graph Statistics")
        print("="*60)
        
        # Node counts
        node_query = "MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC"
        result = self.graph.query(node_query)
        
        print("\nNodes:")
        total_nodes = 0
        for row in result.result_set:
            node_type = row[0]
            count = row[1]
            total_nodes += count
            print(f"  {node_type}: {count}")
        print(f"  TOTAL: {total_nodes}")
        
        # Relationship counts
        rel_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"
        result = self.graph.query(rel_query)
        
        print("\nRelationships:")
        total_rels = 0
        for row in result.result_set:
            rel_type = row[0]
            count = row[1]
            total_rels += count
            print(f"  {rel_type}: {count}")
        print(f"  TOTAL: {total_rels}")
        
        print("\n" + "="*60)
    
    def load_all(self):
        """Load all data from CSV files."""
        print("\n" + "="*60)
        print("🚀 LDC Data Loader")
        print("="*60)
        print(f"Input directory: {INPUT_DIR}")
        print(f"Target graph: {LDC_GRAPH_NAME}")
        
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
        
        print("\n✅ LDC data loading complete!")
        print(f"Graph '{LDC_GRAPH_NAME}' is ready for use.")


if __name__ == "__main__":
    loader = LDCDataLoader()
    loader.load_all()
