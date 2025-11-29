"""
Comprehensive script to clear, reload, and validate both LDC and Graphiti graphs.

This script:
1. Clears both ldc_graph and graphiti_graph
2. Reloads data using ORM v1.1.1
3. Validates that NO nodes exist without edges (orphaned nodes)
4. Provides detailed statistics and validation reports
"""

import sys
import os
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from falkordb import FalkorDB
import yaml

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)


class GraphReloader:
    """Handles clearing, reloading, and validating graphs."""
    
    def __init__(self):
        """Initialize FalkorDB connection."""
        print("\n" + "=" * 80)
        print("🔄 GRAPH RELOAD AND VALIDATION TOOL")
        print("=" * 80)
        print(f"FalkorDB ORM Version: 1.1.1")
        print()
        
        falkordb_config = config['falkordb']
        
        self.client = FalkorDB(
            host=falkordb_config['host'],
            port=falkordb_config['port'],
            username=falkordb_config.get('username'),
            password=falkordb_config.get('password'),
            ssl=falkordb_config.get('ssl', False)
        )
        
        print(f"✓ Connected to FalkorDB at {falkordb_config['host']}:{falkordb_config['port']}")
    
    def clear_graph(self, graph_name: str):
        """Clear all data from a graph."""
        print(f"\n🗑️  Clearing graph: {graph_name}")
        print("-" * 80)
        
        graph = self.client.select_graph(graph_name)
        
        try:
            # Get counts before clearing
            result = graph.query("MATCH (n) RETURN count(n) as node_count")
            node_count = result.result_set[0][0] if result.result_set else 0
            
            result = graph.query("MATCH ()-[r]->() RETURN count(r) as rel_count")
            rel_count = result.result_set[0][0] if result.result_set else 0
            
            print(f"   Found: {node_count} nodes, {rel_count} relationships")
            
            # Clear the graph
            graph.query("MATCH (n) DETACH DELETE n")
            print(f"   ✓ Cleared {graph_name}")
            
        except Exception as e:
            print(f"   ⚠️  Warning: {e}")
    
    def load_ldc_graph(self):
        """Load LDC graph using the fixed ORM loader."""
        print(f"\n📦 Loading LDC Graph")
        print("-" * 80)
        
        script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'ldc', 'load_ldc_data_orm_fixed.py')
        
        if not os.path.exists(script_path):
            print(f"   ✗ Script not found: {script_path}")
            return False
        
        print(f"   Running: {script_path}")
        
        try:
            result = subprocess.run(
                ['python3', script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print("   ✓ LDC graph loaded successfully")
                # Print last few lines of output
                lines = result.stdout.strip().split('\n')
                for line in lines[-10:]:
                    if line.strip():
                        print(f"      {line}")
                return True
            else:
                print(f"   ✗ Failed to load LDC graph")
                print(f"      Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("   ✗ Timeout loading LDC graph (>5 minutes)")
            return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False
    
    def load_graphiti_graph(self):
        """Load Graphiti graph using the ORM loader."""
        print(f"\n🧠 Loading Graphiti Graph")
        print("-" * 80)
        
        script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'ldc', 'load_ldc_graphiti_orm.py')
        
        if not os.path.exists(script_path):
            print(f"   ✗ Script not found: {script_path}")
            return False
        
        print(f"   Running: {script_path}")
        
        try:
            result = subprocess.run(
                ['python3', script_path],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout (Graphiti can be slow)
            )
            
            if result.returncode == 0:
                print("   ✓ Graphiti graph loaded successfully")
                # Print last few lines of output
                lines = result.stdout.strip().split('\n')
                for line in lines[-10:]:
                    if line.strip():
                        print(f"      {line}")
                return True
            else:
                print(f"   ✗ Failed to load Graphiti graph")
                print(f"      Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("   ✗ Timeout loading Graphiti graph (>10 minutes)")
            return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False
    
    def validate_graph(self, graph_name: str) -> dict:
        """Validate a graph and return statistics."""
        print(f"\n✅ Validating Graph: {graph_name}")
        print("-" * 80)
        
        graph = self.client.select_graph(graph_name)
        
        stats = {
            'graph_name': graph_name,
            'total_nodes': 0,
            'total_relationships': 0,
            'orphaned_nodes': 0,
            'node_types': {},
            'relationship_types': {},
            'orphaned_node_details': []
        }
        
        # Get total nodes
        result = graph.query("MATCH (n) RETURN count(n) as count")
        stats['total_nodes'] = result.result_set[0][0] if result.result_set else 0
        
        # Get total relationships
        result = graph.query("MATCH ()-[r]->() RETURN count(r) as count")
        stats['total_relationships'] = result.result_set[0][0] if result.result_set else 0
        
        # Get node types
        result = graph.query("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(*) as count
            ORDER BY count DESC
        """)
        for record in result.result_set:
            label = record[0]
            count = record[1]
            stats['node_types'][label] = count
        
        # Get relationship types
        result = graph.query("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(*) as count
            ORDER BY count DESC
        """)
        for record in result.result_set:
            rel_type = record[0]
            count = record[1]
            stats['relationship_types'][rel_type] = count
        
        # Find orphaned nodes (nodes with no relationships)
        result = graph.query("""
            MATCH (n)
            WHERE NOT (n)-[]-()
            RETURN labels(n)[0] as label, id(n) as id, properties(n) as props
            LIMIT 100
        """)
        
        stats['orphaned_nodes'] = len(result.result_set)
        
        for record in result.result_set:
            label = record[0]
            node_id = record[1]
            props = record[2]
            stats['orphaned_node_details'].append({
                'label': label,
                'id': node_id,
                'name': props.get('name', props.get('product_name', 'N/A'))
            })
        
        # Print statistics
        print(f"\n   📊 Statistics:")
        print(f"      Total Nodes:         {stats['total_nodes']:,}")
        print(f"      Total Relationships: {stats['total_relationships']:,}")
        print(f"      Orphaned Nodes:      {stats['orphaned_nodes']:,}")
        
        print(f"\n   📦 Node Types:")
        for label, count in sorted(stats['node_types'].items(), key=lambda x: x[1], reverse=True):
            print(f"      {label:25s} {count:,}")
        
        print(f"\n   🔗 Relationship Types:")
        for rel_type, count in sorted(stats['relationship_types'].items(), key=lambda x: x[1], reverse=True):
            print(f"      {rel_type:25s} {count:,}")
        
        if stats['orphaned_nodes'] > 0:
            print(f"\n   ⚠️  ORPHANED NODES FOUND: {stats['orphaned_nodes']}")
            print(f"      First 10 orphaned nodes:")
            for node in stats['orphaned_node_details'][:10]:
                print(f"         [{node['label']}] ID={node['id']}, Name='{node['name']}'")
        else:
            print(f"\n   ✅ No orphaned nodes found!")
        
        return stats
    
    def run_full_reload(self):
        """Clear, reload, and validate both graphs."""
        print("\n" + "=" * 80)
        print("🚀 STARTING FULL GRAPH RELOAD")
        print("=" * 80)
        
        results = {
            'ldc_cleared': False,
            'ldc_loaded': False,
            'ldc_validated': False,
            'ldc_stats': None,
            'graphiti_cleared': False,
            'graphiti_loaded': False,
            'graphiti_validated': False,
            'graphiti_stats': None
        }
        
        # ===== LDC GRAPH =====
        print("\n" + "=" * 80)
        print("📦 LDC GRAPH")
        print("=" * 80)
        
        # Clear LDC graph
        try:
            self.clear_graph('ldc_graph')
            results['ldc_cleared'] = True
        except Exception as e:
            print(f"   ✗ Failed to clear LDC graph: {e}")
            return results
        
        # Load LDC graph
        results['ldc_loaded'] = self.load_ldc_graph()
        
        if results['ldc_loaded']:
            # Validate LDC graph
            try:
                results['ldc_stats'] = self.validate_graph('ldc_graph')
                results['ldc_validated'] = True
            except Exception as e:
                print(f"   ✗ Failed to validate LDC graph: {e}")
        
        # ===== GRAPHITI GRAPH =====
        print("\n" + "=" * 80)
        print("🧠 GRAPHITI GRAPH")
        print("=" * 80)
        
        # Clear Graphiti graph
        try:
            self.clear_graph('graphiti_graph')
            results['graphiti_cleared'] = True
        except Exception as e:
            print(f"   ✗ Failed to clear Graphiti graph: {e}")
            return results
        
        # Load Graphiti graph
        results['graphiti_loaded'] = self.load_graphiti_graph()
        
        if results['graphiti_loaded']:
            # Validate Graphiti graph
            try:
                results['graphiti_stats'] = self.validate_graph('graphiti_graph')
                results['graphiti_validated'] = True
            except Exception as e:
                print(f"   ✗ Failed to validate Graphiti graph: {e}")
        
        return results
    
    def print_final_summary(self, results: dict):
        """Print final summary of the reload process."""
        print("\n" + "=" * 80)
        print("📋 FINAL SUMMARY")
        print("=" * 80)
        
        # LDC Graph Summary
        print(f"\n📦 LDC Graph:")
        print(f"   Cleared:    {'✓' if results['ldc_cleared'] else '✗'}")
        print(f"   Loaded:     {'✓' if results['ldc_loaded'] else '✗'}")
        print(f"   Validated:  {'✓' if results['ldc_validated'] else '✗'}")
        
        if results['ldc_stats']:
            orphaned = results['ldc_stats']['orphaned_nodes']
            print(f"   Nodes:      {results['ldc_stats']['total_nodes']:,}")
            print(f"   Edges:      {results['ldc_stats']['total_relationships']:,}")
            print(f"   Orphaned:   {orphaned:,} {'✗ ISSUE!' if orphaned > 0 else '✓'}")
        
        # Graphiti Graph Summary
        print(f"\n🧠 Graphiti Graph:")
        print(f"   Cleared:    {'✓' if results['graphiti_cleared'] else '✗'}")
        print(f"   Loaded:     {'✓' if results['graphiti_loaded'] else '✗'}")
        print(f"   Validated:  {'✓' if results['graphiti_validated'] else '✗'}")
        
        if results['graphiti_stats']:
            orphaned = results['graphiti_stats']['orphaned_nodes']
            print(f"   Nodes:      {results['graphiti_stats']['total_nodes']:,}")
            print(f"   Edges:      {results['graphiti_stats']['total_relationships']:,}")
            print(f"   Orphaned:   {orphaned:,} {'✗ ISSUE!' if orphaned > 0 else '✓'}")
        
        # Overall Status
        print(f"\n" + "=" * 80)
        ldc_success = results['ldc_loaded'] and results['ldc_validated']
        graphiti_success = results['graphiti_loaded'] and results['graphiti_validated']
        
        ldc_clean = ldc_success and results['ldc_stats']['orphaned_nodes'] == 0
        graphiti_clean = graphiti_success and results['graphiti_stats']['orphaned_nodes'] == 0
        
        if ldc_clean and graphiti_clean:
            print("✅ SUCCESS: Both graphs loaded and validated with NO orphaned nodes!")
        else:
            print("⚠️  WARNING: Some issues detected:")
            if not ldc_clean:
                print(f"   - LDC Graph: {results['ldc_stats']['orphaned_nodes'] if results['ldc_stats'] else 'Failed'} orphaned nodes")
            if not graphiti_clean:
                print(f"   - Graphiti Graph: {results['graphiti_stats']['orphaned_nodes'] if results['graphiti_stats'] else 'Failed'} orphaned nodes")
        
        print("=" * 80)
        
        return ldc_clean and graphiti_clean


def main():
    """Main execution function."""
    reloader = GraphReloader()
    results = reloader.run_full_reload()
    success = reloader.print_final_summary(results)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
