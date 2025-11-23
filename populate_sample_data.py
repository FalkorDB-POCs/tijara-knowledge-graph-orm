"""
Populate Tijara Knowledge Graph with Sample Data
Adds comprehensive commodity trading data for testing and demos
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Sample data for multiple commodities, regions, and indicators
SAMPLE_DATA = [
    # Corn Production Data - USA
    {
        "data": [
            {"value": 384900, "year": 2023, "month": 1},
            {"value": 391200, "year": 2023, "month": 2},
            {"value": 398500, "year": 2023, "month": 3},
            {"value": 402300, "year": 2023, "month": 4},
            {"value": 407100, "year": 2023, "month": 5},
            {"value": 412800, "year": 2023, "month": 6},
        ],
        "metadata": {
            "region": "Iowa",
            "country": "USA",
            "type": "Production",
            "commodity": "Corn",
            "unit": "thousand_metric_tons",
            "source": "USDA"
        }
    },
    # Corn Production - Germany
    {
        "data": [
            {"value": 4200, "year": 2023, "month": 1},
            {"value": 4350, "year": 2023, "month": 2},
            {"value": 4480, "year": 2023, "month": 3},
            {"value": 4620, "year": 2023, "month": 4},
            {"value": 4750, "year": 2023, "month": 5},
            {"value": 4890, "year": 2023, "month": 6},
        ],
        "metadata": {
            "region": "Bavaria",
            "country": "Germany",
            "type": "Production",
            "commodity": "Corn",
            "unit": "thousand_metric_tons",
            "source": "Eurostat"
        }
    },
    # Corn Exports - USA
    {
        "data": [
            {"value": 52300, "year": 2023, "month": 1},
            {"value": 54100, "year": 2023, "month": 2},
            {"value": 56800, "year": 2023, "month": 3},
            {"value": 58200, "year": 2023, "month": 4},
            {"value": 59700, "year": 2023, "month": 5},
            {"value": 61400, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "USA",
            "type": "Exports",
            "commodity": "Corn",
            "unit": "thousand_metric_tons",
            "source": "USDA"
        }
    },
    # Corn Demand - Germany
    {
        "data": [
            {"value": 8500, "year": 2023, "month": 1},
            {"value": 8620, "year": 2023, "month": 2},
            {"value": 8740, "year": 2023, "month": 3},
            {"value": 8850, "year": 2023, "month": 4},
            {"value": 8970, "year": 2023, "month": 5},
            {"value": 9100, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "Germany",
            "type": "Demand",
            "commodity": "Corn",
            "unit": "thousand_metric_tons",
            "source": "Eurostat"
        }
    },
    # Wheat Production - France
    {
        "data": [
            {"value": 36500, "year": 2023, "month": 1},
            {"value": 37200, "year": 2023, "month": 2},
            {"value": 38100, "year": 2023, "month": 3},
            {"value": 38900, "year": 2023, "month": 4},
            {"value": 39600, "year": 2023, "month": 5},
            {"value": 40400, "year": 2023, "month": 6},
        ],
        "metadata": {
            "region": "Picardie",
            "country": "France",
            "type": "Production",
            "commodity": "Wheat",
            "unit": "thousand_metric_tons",
            "source": "MARS"
        }
    },
    # Wheat Production - Morocco
    {
        "data": [
            {"value": 7800, "year": 2023, "month": 1},
            {"value": 7950, "year": 2023, "month": 2},
            {"value": 8120, "year": 2023, "month": 3},
            {"value": 8290, "year": 2023, "month": 4},
            {"value": 8450, "year": 2023, "month": 5},
            {"value": 8620, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "Morocco",
            "type": "Production",
            "commodity": "Wheat",
            "unit": "thousand_metric_tons",
            "source": "FAO"
        }
    },
    # Wheat Yield - France
    {
        "data": [
            {"value": 7.2, "year": 2023, "month": 1},
            {"value": 7.3, "year": 2023, "month": 2},
            {"value": 7.4, "year": 2023, "month": 3},
            {"value": 7.5, "year": 2023, "month": 4},
            {"value": 7.6, "year": 2023, "month": 5},
            {"value": 7.7, "year": 2023, "month": 6},
        ],
        "metadata": {
            "region": "Picardie",
            "country": "France",
            "type": "Yield",
            "commodity": "Wheat",
            "unit": "metric_tons_per_hectare",
            "source": "MARS"
        }
    },
    # Wheat Yield - Morocco
    {
        "data": [
            {"value": 1.8, "year": 2023, "month": 1},
            {"value": 1.85, "year": 2023, "month": 2},
            {"value": 1.9, "year": 2023, "month": 3},
            {"value": 1.95, "year": 2023, "month": 4},
            {"value": 2.0, "year": 2023, "month": 5},
            {"value": 2.05, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "Morocco",
            "type": "Yield",
            "commodity": "Wheat",
            "unit": "metric_tons_per_hectare",
            "source": "FAO"
        }
    },
    # Soybeans Production - Brazil
    {
        "data": [
            {"value": 149500, "year": 2023, "month": 1},
            {"value": 151200, "year": 2023, "month": 2},
            {"value": 153000, "year": 2023, "month": 3},
            {"value": 154800, "year": 2023, "month": 4},
            {"value": 156500, "year": 2023, "month": 5},
            {"value": 158300, "year": 2023, "month": 6},
        ],
        "metadata": {
            "region": "Mato Grosso",
            "country": "Brazil",
            "type": "Production",
            "commodity": "Soybeans",
            "unit": "thousand_metric_tons",
            "source": "CONAB"
        }
    },
    # Soybeans Exports - Brazil
    {
        "data": [
            {"value": 89200, "year": 2023, "month": 1},
            {"value": 90500, "year": 2023, "month": 2},
            {"value": 91800, "year": 2023, "month": 3},
            {"value": 93100, "year": 2023, "month": 4},
            {"value": 94400, "year": 2023, "month": 5},
            {"value": 95700, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "Brazil",
            "type": "Exports",
            "commodity": "Soybeans",
            "unit": "thousand_metric_tons",
            "source": "CONAB"
        }
    },
    # Rice Production - China
    {
        "data": [
            {"value": 212500, "year": 2023, "month": 1},
            {"value": 214300, "year": 2023, "month": 2},
            {"value": 216100, "year": 2023, "month": 3},
            {"value": 217900, "year": 2023, "month": 4},
            {"value": 219700, "year": 2023, "month": 5},
            {"value": 221500, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "China",
            "type": "Production",
            "commodity": "Rice",
            "unit": "thousand_metric_tons",
            "source": "China National Bureau of Statistics"
        }
    },
    # Corn Stocks - USA
    {
        "data": [
            {"value": 32400, "year": 2023, "month": 1},
            {"value": 33100, "year": 2023, "month": 2},
            {"value": 33800, "year": 2023, "month": 3},
            {"value": 34500, "year": 2023, "month": 4},
            {"value": 35200, "year": 2023, "month": 5},
            {"value": 35900, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "USA",
            "type": "Stocks",
            "commodity": "Corn",
            "unit": "thousand_metric_tons",
            "source": "USDA"
        }
    },
    # Wheat Stocks - France
    {
        "data": [
            {"value": 5200, "year": 2023, "month": 1},
            {"value": 5350, "year": 2023, "month": 2},
            {"value": 5500, "year": 2023, "month": 3},
            {"value": 5650, "year": 2023, "month": 4},
            {"value": 5800, "year": 2023, "month": 5},
            {"value": 5950, "year": 2023, "month": 6},
        ],
        "metadata": {
            "country": "France",
            "type": "Stocks",
            "commodity": "Wheat",
            "unit": "thousand_metric_tons",
            "source": "MARS"
        }
    },
    
    # ========== 2024 EXPORTS DATA ==========
    
    # Wheat Exports - France to Morocco (2024)
    {
        "data": [
            {"value": 4850, "year": 2024, "month": 1, "destination": "Morocco"},
            {"value": 5120, "year": 2024, "month": 2, "destination": "Morocco"},
            {"value": 4980, "year": 2024, "month": 3, "destination": "Morocco"},
            {"value": 5340, "year": 2024, "month": 4, "destination": "Morocco"},
            {"value": 5210, "year": 2024, "month": 5, "destination": "Morocco"},
            {"value": 5480, "year": 2024, "month": 6, "destination": "Morocco"},
            {"value": 5650, "year": 2024, "month": 7, "destination": "Morocco"},
            {"value": 5320, "year": 2024, "month": 8, "destination": "Morocco"},
            {"value": 5890, "year": 2024, "month": 9, "destination": "Morocco"},
            {"value": 5740, "year": 2024, "month": 10, "destination": "Morocco"},
            {"value": 6120, "year": 2024, "month": 11, "destination": "Morocco"},
            {"value": 5980, "year": 2024, "month": 12, "destination": "Morocco"},
        ],
        "metadata": {
            "country": "France",
            "type": "Exports",
            "commodity": "Wheat",
            "unit": "thousand_metric_tons",
            "source": "MARS"
        }
    },
    # Corn Exports - USA to China (2024)
    {
        "data": [
            {"value": 58400, "year": 2024, "month": 1, "destination": "China"},
            {"value": 62100, "year": 2024, "month": 2, "destination": "China"},
            {"value": 59800, "year": 2024, "month": 3, "destination": "China"},
            {"value": 61500, "year": 2024, "month": 4, "destination": "China"},
            {"value": 63200, "year": 2024, "month": 5, "destination": "China"},
            {"value": 60900, "year": 2024, "month": 6, "destination": "China"},
            {"value": 64700, "year": 2024, "month": 7, "destination": "China"},
            {"value": 62800, "year": 2024, "month": 8, "destination": "China"},
            {"value": 61300, "year": 2024, "month": 9, "destination": "China"},
            {"value": 65400, "year": 2024, "month": 10, "destination": "China"},
            {"value": 63900, "year": 2024, "month": 11, "destination": "China"},
            {"value": 67200, "year": 2024, "month": 12, "destination": "China"},
        ],
        "metadata": {
            "country": "USA",
            "type": "Exports",
            "commodity": "Corn",
            "unit": "thousand_metric_tons",
            "source": "USDA"
        }
    },
    # Corn Exports - USA to Mexico (2024)
    {
        "data": [
            {"value": 12300, "year": 2024, "month": 1, "destination": "Mexico"},
            {"value": 13100, "year": 2024, "month": 2, "destination": "Mexico"},
            {"value": 12850, "year": 2024, "month": 3, "destination": "Mexico"},
            {"value": 13650, "year": 2024, "month": 4, "destination": "Mexico"},
            {"value": 13200, "year": 2024, "month": 5, "destination": "Mexico"},
            {"value": 14100, "year": 2024, "month": 6, "destination": "Mexico"},
            {"value": 13900, "year": 2024, "month": 7, "destination": "Mexico"},
            {"value": 12700, "year": 2024, "month": 8, "destination": "Mexico"},
            {"value": 14400, "year": 2024, "month": 9, "destination": "Mexico"},
            {"value": 13800, "year": 2024, "month": 10, "destination": "Mexico"},
            {"value": 14600, "year": 2024, "month": 11, "destination": "Mexico"},
            {"value": 14200, "year": 2024, "month": 12, "destination": "Mexico"},
        ],
        "metadata": {
            "country": "USA",
            "type": "Exports",
            "commodity": "Corn",
            "unit": "thousand_metric_tons",
            "source": "USDA"
        }
    },
    # Soybean Exports - Brazil to China (2024)
    {
        "data": [
            {"value": 97200, "year": 2024, "month": 1, "destination": "China"},
            {"value": 102500, "year": 2024, "month": 2, "destination": "China"},
            {"value": 99800, "year": 2024, "month": 3, "destination": "China"},
            {"value": 105300, "year": 2024, "month": 4, "destination": "China"},
            {"value": 101700, "year": 2024, "month": 5, "destination": "China"},
            {"value": 98600, "year": 2024, "month": 6, "destination": "China"},
            {"value": 106900, "year": 2024, "month": 7, "destination": "China"},
            {"value": 103400, "year": 2024, "month": 8, "destination": "China"},
            {"value": 100200, "year": 2024, "month": 9, "destination": "China"},
            {"value": 108700, "year": 2024, "month": 10, "destination": "China"},
            {"value": 104800, "year": 2024, "month": 11, "destination": "China"},
            {"value": 110500, "year": 2024, "month": 12, "destination": "China"},
        ],
        "metadata": {
            "country": "Brazil",
            "type": "Exports",
            "commodity": "Soybeans",
            "unit": "thousand_metric_tons",
            "source": "CONAB"
        }
    },
    # Soybean Exports - Brazil to EU (2024)
    {
        "data": [
            {"value": 8450, "year": 2024, "month": 1, "destination": "EU"},
            {"value": 9120, "year": 2024, "month": 2, "destination": "EU"},
            {"value": 8780, "year": 2024, "month": 3, "destination": "EU"},
            {"value": 9450, "year": 2024, "month": 4, "destination": "EU"},
            {"value": 8900, "year": 2024, "month": 5, "destination": "EU"},
            {"value": 9680, "year": 2024, "month": 6, "destination": "EU"},
            {"value": 9200, "year": 2024, "month": 7, "destination": "EU"},
            {"value": 8650, "year": 2024, "month": 8, "destination": "EU"},
            {"value": 9850, "year": 2024, "month": 9, "destination": "EU"},
            {"value": 9300, "year": 2024, "month": 10, "destination": "EU"},
            {"value": 10100, "year": 2024, "month": 11, "destination": "EU"},
            {"value": 9750, "year": 2024, "month": 12, "destination": "EU"},
        ],
        "metadata": {
            "country": "Brazil",
            "type": "Exports",
            "commodity": "Soybeans",
            "unit": "thousand_metric_tons",
            "source": "CONAB"
        }
    },
    # Wheat Exports - USA to Japan (2024)
    {
        "data": [
            {"value": 3250, "year": 2024, "month": 1, "destination": "Japan"},
            {"value": 3480, "year": 2024, "month": 2, "destination": "Japan"},
            {"value": 3320, "year": 2024, "month": 3, "destination": "Japan"},
            {"value": 3590, "year": 2024, "month": 4, "destination": "Japan"},
            {"value": 3420, "year": 2024, "month": 5, "destination": "Japan"},
            {"value": 3680, "year": 2024, "month": 6, "destination": "Japan"},
            {"value": 3550, "year": 2024, "month": 7, "destination": "Japan"},
            {"value": 3290, "year": 2024, "month": 8, "destination": "Japan"},
            {"value": 3750, "year": 2024, "month": 9, "destination": "Japan"},
            {"value": 3620, "year": 2024, "month": 10, "destination": "Japan"},
            {"value": 3890, "year": 2024, "month": 11, "destination": "Japan"},
            {"value": 3710, "year": 2024, "month": 12, "destination": "Japan"},
        ],
        "metadata": {
            "country": "USA",
            "type": "Exports",
            "commodity": "Wheat",
            "unit": "thousand_metric_tons",
            "source": "USDA"
        }
    },
    # Rice Exports - China to Africa (2024)
    {
        "data": [
            {"value": 2150, "year": 2024, "month": 1, "destination": "Africa"},
            {"value": 2380, "year": 2024, "month": 2, "destination": "Africa"},
            {"value": 2220, "year": 2024, "month": 3, "destination": "Africa"},
            {"value": 2490, "year": 2024, "month": 4, "destination": "Africa"},
            {"value": 2310, "year": 2024, "month": 5, "destination": "Africa"},
            {"value": 2560, "year": 2024, "month": 6, "destination": "Africa"},
            {"value": 2420, "year": 2024, "month": 7, "destination": "Africa"},
            {"value": 2190, "year": 2024, "month": 8, "destination": "Africa"},
            {"value": 2650, "year": 2024, "month": 9, "destination": "Africa"},
            {"value": 2480, "year": 2024, "month": 10, "destination": "Africa"},
            {"value": 2730, "year": 2024, "month": 11, "destination": "Africa"},
            {"value": 2580, "year": 2024, "month": 12, "destination": "Africa"},
        ],
        "metadata": {
            "country": "China",
            "type": "Exports",
            "commodity": "Rice",
            "unit": "thousand_metric_tons",
            "source": "China Customs"
        }
    },
    
    # ========== 2025 EXPORTS DATA ==========
    
    # Wheat Exports - France to Morocco (2025)
    {
        "data": [
            {"value": 6250, "year": 2025, "month": 1, "destination": "Morocco"},
            {"value": 6580, "year": 2025, "month": 2, "destination": "Morocco"},
            {"value": 6320, "year": 2025, "month": 3, "destination": "Morocco"},
            {"value": 6890, "year": 2025, "month": 4, "destination": "Morocco"},
            {"value": 6450, "year": 2025, "month": 5, "destination": "Morocco"},
            {"value": 7120, "year": 2025, "month": 6, "destination": "Morocco"},
        ],
        "metadata": {
            "country": "France",
            "type": "Exports",
            "commodity": "Wheat",
            "unit": "thousand_metric_tons",
            "source": "MARS"
        }
    },
    # Corn Exports - USA to China (2025)
    {
        "data": [
            {"value": 69500, "year": 2025, "month": 1, "destination": "China"},
            {"value": 72800, "year": 2025, "month": 2, "destination": "China"},
            {"value": 70200, "year": 2025, "month": 3, "destination": "China"},
            {"value": 68900, "year": 2025, "month": 4, "destination": "China"},
            {"value": 74300, "year": 2025, "month": 5, "destination": "China"},
            {"value": 71600, "year": 2025, "month": 6, "destination": "China"},
        ],
        "metadata": {
            "country": "USA",
            "type": "Exports",
            "commodity": "Corn",
            "unit": "thousand_metric_tons",
            "source": "USDA"
        }
    },
    # Corn Exports - USA to Mexico (2025)
    {
        "data": [
            {"value": 15200, "year": 2025, "month": 1, "destination": "Mexico"},
            {"value": 16100, "year": 2025, "month": 2, "destination": "Mexico"},
            {"value": 15450, "year": 2025, "month": 3, "destination": "Mexico"},
            {"value": 14800, "year": 2025, "month": 4, "destination": "Mexico"},
            {"value": 16700, "year": 2025, "month": 5, "destination": "Mexico"},
            {"value": 15900, "year": 2025, "month": 6, "destination": "Mexico"},
        ],
        "metadata": {
            "country": "USA",
            "type": "Exports",
            "commodity": "Corn",
            "unit": "thousand_metric_tons",
            "source": "USDA"
        }
    },
    # Soybean Exports - Brazil to China (2025)
    {
        "data": [
            {"value": 115400, "year": 2025, "month": 1, "destination": "China"},
            {"value": 118900, "year": 2025, "month": 2, "destination": "China"},
            {"value": 113200, "year": 2025, "month": 3, "destination": "China"},
            {"value": 121500, "year": 2025, "month": 4, "destination": "China"},
            {"value": 116800, "year": 2025, "month": 5, "destination": "China"},
            {"value": 119600, "year": 2025, "month": 6, "destination": "China"},
        ],
        "metadata": {
            "country": "Brazil",
            "type": "Exports",
            "commodity": "Soybeans",
            "unit": "thousand_metric_tons",
            "source": "CONAB"
        }
    },
    # Soybean Exports - Brazil to EU (2025)
    {
        "data": [
            {"value": 10500, "year": 2025, "month": 1, "destination": "EU"},
            {"value": 11200, "year": 2025, "month": 2, "destination": "EU"},
            {"value": 10750, "year": 2025, "month": 3, "destination": "EU"},
            {"value": 9980, "year": 2025, "month": 4, "destination": "EU"},
            {"value": 11650, "year": 2025, "month": 5, "destination": "EU"},
            {"value": 10900, "year": 2025, "month": 6, "destination": "EU"},
        ],
        "metadata": {
            "country": "Brazil",
            "type": "Exports",
            "commodity": "Soybeans",
            "unit": "thousand_metric_tons",
            "source": "CONAB"
        }
    },
    # Wheat Exports - USA to Japan (2025)
    {
        "data": [
            {"value": 4100, "year": 2025, "month": 1, "destination": "Japan"},
            {"value": 4380, "year": 2025, "month": 2, "destination": "Japan"},
            {"value": 4220, "year": 2025, "month": 3, "destination": "Japan"},
            {"value": 3950, "year": 2025, "month": 4, "destination": "Japan"},
            {"value": 4520, "year": 2025, "month": 5, "destination": "Japan"},
            {"value": 4290, "year": 2025, "month": 6, "destination": "Japan"},
        ],
        "metadata": {
            "country": "USA",
            "type": "Exports",
            "commodity": "Wheat",
            "unit": "thousand_metric_tons",
            "source": "USDA"
        }
    },
    # Rice Exports - China to Africa (2025)
    {
        "data": [
            {"value": 2950, "year": 2025, "month": 1, "destination": "Africa"},
            {"value": 3180, "year": 2025, "month": 2, "destination": "Africa"},
            {"value": 3020, "year": 2025, "month": 3, "destination": "Africa"},
            {"value": 2850, "year": 2025, "month": 4, "destination": "Africa"},
            {"value": 3340, "year": 2025, "month": 5, "destination": "Africa"},
            {"value": 3150, "year": 2025, "month": 6, "destination": "Africa"},
        ],
        "metadata": {
            "country": "China",
            "type": "Exports",
            "commodity": "Rice",
            "unit": "thousand_metric_tons",
            "source": "China Customs"
        }
    },
    # Soybean Exports - Argentina to China (2025)
    {
        "data": [
            {"value": 4820, "year": 2025, "month": 1, "destination": "China"},
            {"value": 5150, "year": 2025, "month": 2, "destination": "China"},
            {"value": 4930, "year": 2025, "month": 3, "destination": "China"},
            {"value": 4680, "year": 2025, "month": 4, "destination": "China"},
            {"value": 5420, "year": 2025, "month": 5, "destination": "China"},
            {"value": 5080, "year": 2025, "month": 6, "destination": "China"},
        ],
        "metadata": {
            "country": "Argentina",
            "type": "Exports",
            "commodity": "Soybeans",
            "unit": "thousand_metric_tons",
            "source": "MAGyP"
        }
    },
]


def ingest_sample_data():
    """Ingest all sample data via the API with Graphiti embeddings."""
    print("=" * 80)
    print("Populating Tijara Knowledge Graph with Sample Data")
    print("(All data will pass through Graphiti for embeddings)")
    print("=" * 80)
    
    # Check API health first
    print("\n🔍 Checking API health...")
    try:
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code == 200:
            health = health_response.json()
            print(f"   FalkorDB: {'✅' if health.get('falkordb') else '❌'}")
            print(f"   Graphiti: {'✅' if health.get('graphiti') else '❌'}")
            if not health.get('overall'):
                print("\n⚠️  Warning: Some services are not ready. Continuing anyway...")
        else:
            print(f"   ⚠️  Could not check health: {health_response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Health check failed: {e}")
    
    total_entities = 0
    total_relationships = 0
    
    import time
    
    for i, dataset in enumerate(SAMPLE_DATA, 1):
        print(f"\n[{i}/{len(SAMPLE_DATA)}] Ingesting {dataset['metadata']['commodity']} "
              f"{dataset['metadata']['type']} data from {dataset['metadata'].get('country', 'N/A')}...")
        
        try:
            # Add validate flag to ensure proper data structure
            payload = {
                "data": dataset["data"],
                "metadata": dataset["metadata"],
                "validate": True
            }
            
            response = requests.post(
                f"{BASE_URL}/ingest",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300  # Extended timeout for embedding generation (Graphiti can be slow)
            )
            
            if response.status_code == 200:
                result = response.json()
                entities_created = result.get('entities_created', 0)
                relationships_created = result.get('relationships_created', 0)
                
                total_entities += entities_created
                total_relationships += relationships_created
                
                print(f"   ✅ Created {entities_created} entities, {relationships_created} relationships (with embeddings)")
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text}")
            
            # Small delay to allow Graphiti to process embeddings
            if i < len(SAMPLE_DATA):
                time.sleep(0.5)
        
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print("\n" + "=" * 80)
    print("Summary:")
    print(f"   Total entities created: {total_entities}")
    print(f"   Total relationships created: {total_relationships}")
    print("=" * 80)
    
    # Get final statistics
    print("\nFetching final graph statistics...")
    try:
        stats_response = requests.get(f"{BASE_URL}/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print("\n📊 Graph Statistics:")
            print(f"   Total Nodes: {stats.get('node_count', 0)}")
            print(f"   Total Relationships: {stats.get('relationship_count', 0)}")
            
            # Show node counts by type
            node_counts = stats.get('node_counts_by_label', {})
            if node_counts:
                print("\n   Node Types:")
                # Separate Graphiti nodes from domain nodes
                graphiti_types = ['Episodic', 'Entity', 'Episode']
                domain_nodes = {k: v for k, v in node_counts.items() if k not in graphiti_types}
                graphiti_nodes = {k: v for k, v in node_counts.items() if k in graphiti_types}
                
                # Show domain nodes first
                if domain_nodes:
                    print("     Domain Data:")
                    for label, count in sorted(domain_nodes.items()):
                        print(f"       - {label}: {count}")
                
                # Show Graphiti nodes
                if graphiti_nodes:
                    print("     Graphiti (with embeddings):")
                    for label, count in sorted(graphiti_nodes.items()):
                        print(f"       - {label}: {count}")
            
            # Show ontology info
            ontology = stats.get('ontology', {})
            if ontology:
                print(f"\n   Ontology concepts: {ontology.get('total_concepts', 0)}")
        else:
            print(f"   ⚠️  Could not fetch stats: {stats_response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Error fetching stats: {e}")
    
    print("\n" + "=" * 80)
    print("✅ Sample data population complete!")
    print("All nodes now have embeddings for semantic search via Graphiti.")
    print("=" * 80)


if __name__ == "__main__":
    ingest_sample_data()
