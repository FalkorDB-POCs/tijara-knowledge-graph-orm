#!/usr/bin/env python3
"""
Switch between different FalkorDB graphs
Usage: python switch_graph.py [tijara_kg|ldc_graph]
"""

import sys
import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')

AVAILABLE_GRAPHS = {
    'tijara_kg': 'Demo data with sample global commodities',
    'ldc_graph': 'LDC-specific data (France & USA focus)'
}

def switch_graph(graph_name: str):
    """Switch to specified graph in config."""
    if graph_name not in AVAILABLE_GRAPHS:
        print(f"❌ Unknown graph: {graph_name}")
        print(f"\nAvailable graphs:")
        for name, desc in AVAILABLE_GRAPHS.items():
            print(f"  - {name}: {desc}")
        sys.exit(1)
    
    # Load config
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    
    # Update graph name
    old_graph = config['falkordb']['graph_name']
    config['falkordb']['graph_name'] = graph_name
    
    # Save config
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Switched graph: {old_graph} → {graph_name}")
    print(f"   {AVAILABLE_GRAPHS[graph_name]}")
    print("\n⚠️  Restart the API server for changes to take effect")

def show_current():
    """Show current graph configuration."""
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    
    current_graph = config['falkordb']['graph_name']
    print(f"Current graph: {current_graph}")
    print(f"Description: {AVAILABLE_GRAPHS.get(current_graph, 'Unknown')}")
    print(f"\nAvailable graphs:")
    for name, desc in AVAILABLE_GRAPHS.items():
        marker = "✓" if name == current_graph else " "
        print(f"  [{marker}] {name}: {desc}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_current()
        print("\nUsage: python switch_graph.py [graph_name]")
        sys.exit(0)
    
    graph_name = sys.argv[1]
    switch_graph(graph_name)
