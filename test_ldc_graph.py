"""
Test LDC Graph Data through API
Validates that the ldc_graph data is accessible and queryable
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    """Test API health check."""
    print("\n🏥 Testing API health...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        health = response.json()
        print(f"✓ API is healthy")
        print(f"  FalkorDB: {'✓' if health.get('falkordb') else '✗'}")
        print(f"  Graphiti: {'✓' if health.get('graphiti') else '✗'}")
        return True
    else:
        print(f"✗ API health check failed: {response.status_code}")
        return False

def test_statistics():
    """Test graph statistics endpoint."""
    print("\n📊 Testing graph statistics...")
    response = requests.get(f"{BASE_URL}/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"✓ Statistics retrieved")
        
        if 'nodes' in stats:
            print(f"\n  Nodes:")
            for node_type, count in stats['nodes'].items():
                print(f"    {node_type}: {count}")
        
        if 'relationships' in stats:
            print(f"\n  Relationships:")
            for rel_type, count in stats['relationships'].items():
                print(f"    {rel_type}: {count}")
        return True
    else:
        print(f"✗ Statistics request failed: {response.status_code}")
        return False

def test_query_commodities():
    """Test querying commodity data."""
    print("\n🌾 Testing commodity queries...")
    
    # Use the knowledge_graph query endpoint via Cypher
    query = """
    MATCH (c:Commodity)
    WHERE c.level = 0
    RETURN c.name as category, c.level as level
    ORDER BY c.name
    """
    
    try:
        # Direct query through FalkorDB client
        from src.core.falkordb_client import FalkorDBClient
        import yaml
        
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        client = FalkorDBClient(config['falkordb'])
        results = client.execute_query(query)
        
        print(f"✓ Found {len(results)} commodity categories:")
        for row in results:
            print(f"    - {row['category']}")
        return True
    except Exception as e:
        print(f"✗ Commodity query failed: {e}")
        return False

def test_query_geographies():
    """Test querying geography data."""
    print("\n🌍 Testing geography queries...")
    
    query = """
    MATCH (g:Geography)
    WHERE g.level = 0
    RETURN g.name as country, g.gid_code as code
    ORDER BY g.name
    """
    
    try:
        from src.core.falkordb_client import FalkorDBClient
        import yaml
        
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        client = FalkorDBClient(config['falkordb'])
        results = client.execute_query(query)
        
        print(f"✓ Found {len(results)} countries:")
        for row in results:
            print(f"    - {row['country']} ({row['code']})")
        return True
    except Exception as e:
        print(f"✗ Geography query failed: {e}")
        return False

def test_query_production_areas():
    """Test querying production areas."""
    print("\n🌾 Testing production area queries...")
    
    query = """
    MATCH (p:ProductionArea)-[:PRODUCES]->(c:Commodity)
    RETURN DISTINCT p.commodity as commodity, count(p) as area_count
    ORDER BY area_count DESC
    """
    
    try:
        from src.core.falkordb_client import FalkorDBClient
        import yaml
        
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        client = FalkorDBClient(config['falkordb'])
        results = client.execute_query(query)
        
        print(f"✓ Found production areas for {len(results)} commodities:")
        for row in results:
            print(f"    - {row['commodity']}: {row['area_count']} areas")
        return True
    except Exception as e:
        print(f"✗ Production area query failed: {e}")
        return False

def test_query_trade_flows():
    """Test querying trade flows."""
    print("\n🔄 Testing trade flow queries...")
    
    query = """
    MATCH (source:Geography)-[f:TRADES_WITH]->(dest:Geography)
    RETURN source.name as source, dest.name as destination, 
           f.commodity as commodity, f.season as season
    ORDER BY f.commodity
    """
    
    try:
        from src.core.falkordb_client import FalkorDBClient
        import yaml
        
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        client = FalkorDBClient(config['falkordb'])
        results = client.execute_query(query)
        
        print(f"✓ Found {len(results)} trade flows:")
        for row in results:
            season_str = f" ({row['season']})" if row['season'] else ""
            print(f"    - {row['source']} → {row['destination']}: {row['commodity']}{season_str}")
        return True
    except Exception as e:
        print(f"✗ Trade flow query failed: {e}")
        return False

def test_query_balance_sheets():
    """Test querying balance sheets."""
    print("\n📊 Testing balance sheet queries...")
    
    query = """
    MATCH (b:BalanceSheet)-[:FOR_GEOGRAPHY]->(g:Geography)
    MATCH (b)-[:FOR_COMMODITY]->(c:Commodity)
    RETURN g.name as country, b.product_name as product, 
           b.season as season, b.balance_sheet_id as id
    ORDER BY g.name, b.product_name
    """
    
    try:
        from src.core.falkordb_client import FalkorDBClient
        import yaml
        
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        client = FalkorDBClient(config['falkordb'])
        results = client.execute_query(query)
        
        print(f"✓ Found {len(results)} balance sheets:")
        for row in results[:10]:  # Show first 10
            season_str = f" ({row['season']})" if row['season'] else ""
            print(f"    - {row['country']}: {row['product']}{season_str}")
        if len(results) > 10:
            print(f"    ... and {len(results) - 10} more")
        return True
    except Exception as e:
        print(f"✗ Balance sheet query failed: {e}")
        return False

def test_query_weather_indicators():
    """Test querying weather indicators."""
    print("\n🌡️  Testing weather indicator queries...")
    
    query = """
    MATCH (i:WeatherIndicator)
    RETURN i.indicator_type as type, count(i) as count
    ORDER BY count DESC
    """
    
    try:
        from src.core.falkordb_client import FalkorDBClient
        import yaml
        
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        client = FalkorDBClient(config['falkordb'])
        results = client.execute_query(query)
        
        print(f"✓ Found {len(results)} weather indicator types:")
        for row in results:
            print(f"    - {row['type']}: {row['count']} indicators")
        return True
    except Exception as e:
        print(f"✗ Weather indicator query failed: {e}")
        return False

def run_all_tests():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("🧪 LDC Graph Validation Tests")
    print("="*60)
    print(f"API URL: {BASE_URL}")
    print("Graph: ldc_graph")
    
    tests = [
        ("API Health", test_health),
        ("Graph Statistics", test_statistics),
        ("Commodity Data", test_query_commodities),
        ("Geography Data", test_query_geographies),
        ("Production Areas", test_query_production_areas),
        ("Trade Flows", test_query_trade_flows),
        ("Balance Sheets", test_query_balance_sheets),
        ("Weather Indicators", test_query_weather_indicators),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed! LDC graph is ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
