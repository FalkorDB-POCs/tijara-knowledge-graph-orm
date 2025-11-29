"""
Populate LDC Knowledge Graph from Input CSV Files (ORM Version)
Loads data using FalkorDB ORM entity models and repositories
"""

import csv
import os
import sys
import yaml
from typing import Dict, List
import falkordb

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.yaml')
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

# Import ORM components
from src.models import Geography, Commodity, ProductionArea, BalanceSheet, Component, Indicator
from src.repositories import GeographyRepository, CommodityRepository, BalanceSheetRepository
from falkordb_orm import Repository

# Input data directory
INPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'ldc', 'input')

# Graph name
LDC_GRAPH_NAME = "ldc_graph"


class ORMLDCDataLoader:
    """Loads LDC commodity data from CSV files using FalkorDB ORM."""
    
    def __init__(self):
        """Initialize connection and repositories."""
        print("\n" + "="*60)
        print("🚀 LDC Data Loader (ORM Version)")
        print("="*60)
        print(f"Using falkordb-py-orm with entity models and repositories")
        print()
        
        falkordb_config = config['falkordb']
        
        # Connect to FalkorDB
        self.client = falkordb.FalkorDB(
            host=falkordb_config['host'],
            port=falkordb_config['port'],
            username=falkordb_config.get('username'),
            password=falkordb_config.get('password'),
            ssl=falkordb_config.get('ssl', False)
        )
        
        self.graph = self.client.select_graph(LDC_GRAPH_NAME)
        print(f"✓ Connected to FalkorDB graph: {LDC_GRAPH_NAME}")
        
        # Initialize ORM repositories
        self.commodity_repo = CommodityRepository(self.graph, Commodity)
        self.geography_repo = GeographyRepository(self.graph, Geography)
        self.balance_sheet_repo = BalanceSheetRepository(self.graph, BalanceSheet)
        self.production_area_repo = Repository(self.graph, ProductionArea)
        self.component_repo = Repository(self.graph, Component)
        self.indicator_repo = Repository(self.graph, Indicator)
        
        print("✓ Initialized ORM repositories")
        
        # Track entities by name/code for relationship creation
        self.commodity_cache: Dict[str, Commodity] = {}
        self.geography_cache: Dict[str, Geography] = {}
    
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
        """Load commodity hierarchy using ORM entities."""
        print("\n📦 Loading commodity hierarchy...")
        rows = self.read_csv('commodity_hierarchy.csv')
        
        if not rows:
            print("⚠️  No commodity data found")
            return
        
        commodities_created = 0
        
        # Process hierarchy: Level0 -> Level1 -> Level2 -> Level3
        for row in rows:
            level0 = row['Level0'].strip() if row.get('Level0') else ''
            level1 = row['Level1'].strip() if row.get('Level1') else ''
            level2 = row['Level2'].strip() if row.get('Level2') else ''
            level3 = row['Level3'].strip() if row.get('Level3') else ''
            
            # Create Level0 (root category)
            if level0 and level0 not in self.commodity_cache:
                commodity = Commodity(
                    name=level0,
                    level=0,
                    category=level0
                )
                saved = self.commodity_repo.save(commodity)
                self.commodity_cache[level0] = saved
                commodities_created += 1
            
            # Create Level1 (main commodity)
            if level1 and level1 not in self.commodity_cache:
                commodity = Commodity(
                    name=level1,
                    level=1,
                    category=level0
                )
                # Set parent relationship
                if level0 in self.commodity_cache:
                    commodity.parent = self.commodity_cache[level0]
                
                saved = self.commodity_repo.save(commodity)
                self.commodity_cache[level1] = saved
                commodities_created += 1
            
            # Create Level2 (variety)
            if level2 and level2 not in self.commodity_cache:
                commodity = Commodity(
                    name=level2,
                    level=2,
                    category=level0
                )
                # Set parent relationship
                parent_name = level1 if level1 else level0
                if parent_name in self.commodity_cache:
                    commodity.parent = self.commodity_cache[parent_name]
                
                saved = self.commodity_repo.save(commodity)
                self.commodity_cache[level2] = saved
                commodities_created += 1
            
            # Create Level3 (specific type)
            if level3 and level3 not in self.commodity_cache:
                commodity = Commodity(
                    name=level3,
                    level=3,
                    category=level0
                )
                # Set parent relationship
                parent_name = level2 if level2 else (level1 if level1 else level0)
                if parent_name in self.commodity_cache:
                    commodity.parent = self.commodity_cache[parent_name]
                
                saved = self.commodity_repo.save(commodity)
                self.commodity_cache[level3] = saved
                commodities_created += 1
        
        print(f"✓ Loaded {commodities_created} commodity nodes using ORM")
    
    def load_geometries(self):
        """Load geographic hierarchy using ORM entities."""
        print("\n🌍 Loading geographic hierarchy...")
        rows = self.read_csv('geometries.csv')
        
        if not rows:
            print("⚠️  No geometry data found")
            return
        
        # Sort by level to ensure parents are created first
        rows_sorted = sorted(rows, key=lambda x: int(x['level']))
        
        geographies_created = 0
        
        for row in rows_sorted:
            gid_code = row['gid_code'].strip()
            level = int(row['level'])
            name = row['name'].strip()
            parent_gid = row['parent_gid_code'].strip() if row['parent_gid_code'] else None
            
            # Create geography entity
            geography = Geography(
                name=name,
                gid_code=gid_code,
                level=level
            )
            
            # Set parent relationship
            if parent_gid and parent_gid in self.geography_cache:
                geography.parent = self.geography_cache[parent_gid]
            
            saved = self.geography_repo.save(geography)
            self.geography_cache[gid_code] = saved
            geographies_created += 1
        
        print(f"✓ Loaded {geographies_created} geography nodes using ORM")
    
    def load_indicator_definitions(self):
        """Load weather indicator definitions using ORM entities."""
        print("\n🌡️  Loading weather indicator definitions...")
        rows = self.read_csv('indicator_definition.csv')
        
        if not rows:
            print("⚠️  No indicator definitions found")
            return
        
        indicators_created = 0
        
        for row in rows:
            indicator = Indicator(
                name=row['name'].strip(),
                indicator_type=row['indicator'].strip(),
                unit=row['unit'].strip() if row['unit'] else None
            )
            
            self.indicator_repo.save(indicator)
            indicators_created += 1
        
        print(f"✓ Loaded {indicators_created} indicator definitions using ORM")
    
    def load_production_areas(self):
        """Load production areas using ORM entities."""
        print("\n🌾 Loading production areas...")
        rows = self.read_csv('production_areas.csv')
        
        if not rows:
            print("⚠️  No production area data found")
            return
        
        # Track unique production areas
        unique_areas = {}
        areas_created = 0
        
        for row in rows:
            prod_area_id = row['production_area_id'].strip()
            gid_code = row['gid_code'].strip()
            commodity_name = row['commodity_name'].strip()
            season = row['season'].strip() if row['season'] else None
            
            # Create production area (once per unique ID)
            if prod_area_id not in unique_areas:
                production_area = ProductionArea(
                    name=f"{commodity_name}_{season}" if season else commodity_name
                )
                
                # Link to geography
                if gid_code in self.geography_cache:
                    production_area.geography = self.geography_cache[gid_code]
                
                # Link to commodity
                if commodity_name in self.commodity_cache:
                    production_area.commodities = [self.commodity_cache[commodity_name]]
                
                saved = self.production_area_repo.save(production_area)
                unique_areas[prod_area_id] = saved
                areas_created += 1
        
        print(f"✓ Loaded {areas_created} unique production areas using ORM")
    
    def load_balance_sheets(self):
        """Load balance sheets using ORM entities."""
        print("\n📊 Loading balance sheets...")
        rows = self.read_csv('balance_sheet.csv')
        
        if not rows:
            print("⚠️  No balance sheet data found")
            return
        
        sheets_created = 0
        
        for row in rows:
            gid_code = row['gid'].strip()
            product_name = row['product_name'].strip()
            season = row['product_season'].strip() if row['product_season'] else None
            
            balance_sheet = BalanceSheet(
                product_name=product_name,
                season=season,
                unit="thousand metric tons"  # Default unit
            )
            
            # Link to geography
            if gid_code in self.geography_cache:
                balance_sheet.geography = self.geography_cache[gid_code]
            
            # Link to commodity
            if product_name in self.commodity_cache:
                balance_sheet.commodity = self.commodity_cache[product_name]
            
            self.balance_sheet_repo.save(balance_sheet)
            sheets_created += 1
        
        print(f"✓ Loaded {sheets_created} balance sheets using ORM")
    
    def load_balance_sheet_components(self):
        """Load balance sheet components using ORM entities."""
        print("\n📈 Loading balance sheet components...")
        rows = self.read_csv('balance_sheet_component.csv')
        
        if not rows:
            print("⚠️  No component data found")
            return
        
        components_created = 0
        
        for row in rows:
            component = Component(
                name=row['component_id'].strip(),
                component_type=row.get('component_type', 'general')
            )
            
            self.component_repo.save(component)
            components_created += 1
        
        print(f"✓ Loaded {components_created} balance sheet components using ORM")
    
    def load_trade_flows(self):
        """Load trade flows by creating relationships with properties."""
        print("\n🔄 Loading trade flows...")
        rows = self.read_csv('flows.csv')
        
        if not rows:
            print("⚠️  No trade flow data found")
            return
        
        flows_created = 0
        
        for row in rows:
            source_code = row['source_country'].strip()
            dest_code = row['destination_country'].strip()
            commodity = row['commodity'].strip()
            season = row.get('commodity_season', '').strip() if row.get('commodity_season') else None
            
            # Get geography entities
            source_geo = self.geography_cache.get(source_code)
            dest_geo = self.geography_cache.get(dest_code)
            
            if source_geo and dest_geo:
                # Since ORM doesn't fully support relationship properties yet,
                # we use a raw query for TRADES_WITH with properties
                query = """
                MATCH (source:Geography {gid_code: $source_code})
                MATCH (dest:Geography {gid_code: $dest_code})
                CREATE (source)-[:TRADES_WITH {commodity: $commodity, season: $season}]->(dest)
                """
                self.graph.query(query, {
                    'source_code': source_code,
                    'dest_code': dest_code,
                    'commodity': commodity,
                    'season': season
                })
                flows_created += 1
        
        print(f"✓ Loaded {flows_created} trade flows")
    
    def create_indexes(self):
        """Create graph indexes for performance."""
        print("\n🔍 Creating indexes...")
        
        indexes = [
            "CREATE INDEX FOR (g:Geography) ON (g.gid_code)",
            "CREATE INDEX FOR (g:Geography) ON (g.name)",
            "CREATE INDEX FOR (c:Commodity) ON (c.name)",
            "CREATE INDEX FOR (b:BalanceSheet) ON (b.product_name)",
        ]
        
        for index_query in indexes:
            try:
                self.graph.query(index_query)
            except Exception as e:
                # Index might already exist
                pass
        
        print("✓ Indexes created")
    
    def get_statistics(self):
        """Get graph statistics."""
        print("\n" + "="*60)
        print("📊 LDC Graph Statistics")
        print("="*60)
        print()
        
        # Node counts
        print("Nodes:")
        node_query = "MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC"
        result = self.graph.query(node_query)
        
        total_nodes = 0
        for row in result.result_set:
            node_type = row[0]
            count = row[1]
            print(f"  {node_type}: {count}")
            total_nodes += count
        print(f"  TOTAL: {total_nodes}")
        
        # Relationship counts
        print("\nRelationships:")
        rel_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"
        result = self.graph.query(rel_query)
        
        total_rels = 0
        for row in result.result_set:
            rel_type = row[0]
            count = row[1]
            print(f"  {rel_type}: {count}")
            total_rels += count
        print(f"  TOTAL: {total_rels}")
        
        print("\n" + "="*60)
    
    def load_all(self):
        """Load all LDC data."""
        try:
            # Clear existing data
            self.clear_graph()
            
            # Load data in dependency order
            self.load_commodity_hierarchy()
            self.load_geometries()
            self.load_indicator_definitions()
            self.load_production_areas()
            self.load_balance_sheets()
            self.load_balance_sheet_components()
            self.load_trade_flows()
            self.create_indexes()
            
            # Show statistics
            self.get_statistics()
            
            print("\n✅ LDC data loading complete!")
            print(f"Graph '{LDC_GRAPH_NAME}' is ready for use.")
            print("✨ All data loaded using FalkorDB ORM entities and repositories!")
            print()
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    loader = ORMLDCDataLoader()
    loader.load_all()
