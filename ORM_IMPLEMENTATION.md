# Tijara Knowledge Graph - ORM Implementation

This project implements the Tijara Knowledge Graph using the **falkordb-py-orm** object-relational mapping framework, providing cleaner, more maintainable code through declarative entity models and repository patterns.

## Overview

The ORM implementation replaces direct FalkorDB client calls and manual Cypher query construction with:

- **Declarative Entity Models**: Type-safe entity classes with `@node` decorators
- **Repository Pattern**: CRUD operations with derived query methods
- **Automatic Query Generation**: Methods like `find_by_name()` auto-generate Cypher
- **Relationship Management**: Lazy/eager loading with cascade saves
- **Type Safety**: Full type hints for IDE support

## Architecture

### Entity Models (`src/models/`)

Core entity classes representing graph nodes:

#### Geography
```python
@node("Geography")
class Geography:
    id: Optional[int] = generated_id()
    name: str
    level: int  # 0=country, 1=region, 2=sub-region
    
    parent: Optional["Geography"] = relationship(type="LOCATED_IN", direction="OUTGOING")
    children: List["Geography"] = relationship(type="LOCATED_IN", direction="INCOMING")
    trade_partners: List["Geography"] = relationship(type="TRADES_WITH", direction="OUTGOING")
```

#### Commodity
```python
@node("Commodity")
class Commodity:
    id: Optional[int] = generated_id()
    name: str
    level: int  # 0=category, 1=type, 2=variety
    
    parent: Optional["Commodity"] = relationship(type="SUBCLASS_OF", direction="OUTGOING")
    children: List["Commodity"] = relationship(type="SUBCLASS_OF", direction="INCOMING")
```

#### BalanceSheet
```python
@node("BalanceSheet")
class BalanceSheet:
    id: Optional[int] = generated_id()
    product_name: str
    season: Optional[str] = None
    
    commodity: Optional["Commodity"] = relationship(type="FOR_COMMODITY", direction="OUTGOING")
    geography: Optional["Geography"] = relationship(type="FOR_GEOGRAPHY", direction="OUTGOING")
    components: List["Component"] = relationship(type="HAS_COMPONENT", direction="OUTGOING")
```

### Repositories (`src/repositories/`)

Type-safe repositories with CRUD and derived queries:

#### GeographyRepository
```python
class GeographyRepository(Repository[Geography]):
    # Auto-implemented derived queries:
    # - find_by_name(name: str) -> Optional[Geography]
    # - find_by_level(level: int) -> List[Geography]
    # - find_by_iso_code(iso_code: str) -> Optional[Geography]
    
    @query("MATCH (g:Geography) WHERE g.level = 0 RETURN g ORDER BY g.name", returns=Geography)
    def find_all_countries(self) -> List[Geography]:
        pass
    
    @query("MATCH (g1:Geography)-[:TRADES_WITH]->(g2) WHERE g1.name = $source RETURN g2", returns=Geography)
    def find_trade_partners(self, source: str) -> List[Geography]:
        pass
```

#### CommodityRepository
```python
class CommodityRepository(Repository[Commodity]):
    # Auto-implemented derived queries:
    # - find_by_name(name: str) -> Optional[Commodity]
    # - find_by_level(level: int) -> List[Commodity]
    
    @query("MATCH (c:Commodity) WHERE c.level = 0 RETURN c", returns=Commodity)
    def find_all_categories(self) -> List[Commodity]:
        pass
```

#### BalanceSheetRepository
```python
class BalanceSheetRepository(Repository[BalanceSheet]):
    @query("""
        MATCH (bs:BalanceSheet)-[:FOR_COMMODITY]->(c:Commodity),
              (bs)-[:FOR_GEOGRAPHY]->(g:Geography)
        WHERE c.name = $commodity AND g.name = $geography
        RETURN bs ORDER BY bs.season DESC
    """, returns=BalanceSheet)
    def find_by_commodity_and_geography(self, commodity: str, geography: str) -> List[BalanceSheet]:
        pass
```

### ORM Knowledge Graph (`src/core/orm_knowledge_graph.py`)

Drop-in replacement for `TijaraKnowledgeGraph` that uses ORM:

```python
from src.core.orm_knowledge_graph import ORMKnowledgeGraph

kg = ORMKnowledgeGraph(config)

# Find entities using repositories
france = kg.geography_repo.find_by_name("France")
corn = kg.commodity_repo.find_by_name("Corn")

# Access relationships (lazy-loaded)
for partner in france.trade_partners:
    print(f"France trades with {partner.name}")

# Derived queries
countries = kg.geography_repo.find_all_countries()
categories = kg.commodity_repo.find_all_categories()

# Create entities with relationships
balance_sheet = BalanceSheet(
    product_name="Corn",
    season="2023/24",
    commodity=corn,
    geography=france
)
saved = kg.balance_sheet_repo.save(balance_sheet)  # Creates relationships automatically
```

## Benefits Over Raw Client Approach

### Before (Raw Cypher)
```python
# Manual query construction
query = """
    CREATE (g:Geography {name: $name, level: $level})
    RETURN id(g) as id
"""
result = graph.query(query, {'name': 'France', 'level': 0})
france_id = result.result_set[0][0]

# Manual relationship creation
rel_query = """
    MATCH (a:Geography), (b:Geography)
    WHERE id(a) = $source AND id(b) = $target
    CREATE (a)-[:TRADES_WITH]->(b)
"""
graph.query(rel_query, {'source': france_id, 'target': usa_id})
```

### After (ORM)
```python
# Entity creation with type safety
france = Geography(name="France", level=0)
france = geo_repo.save(france)

# Relationship assignment
france.trade_partners = [usa, germany]
geo_repo.save(france)  # Relationships created automatically
```

### Derived Queries
```python
# Before: Manual Cypher
query = """
    MATCH (g:Geography)
    WHERE g.name = $name
    RETURN g
"""
result = graph.query(query, {'name': 'France'})

# After: Auto-generated
france = geo_repo.find_by_name("France")  # Query auto-generated from method name
```

## Installation

```bash
# Install dependencies including ORM
pip install -r requirements.txt

# falkordb-orm>=0.1.0 is included
```

## Usage Examples

### Basic CRUD
```python
from src.models import Geography, Commodity
from src.repositories import GeographyRepository, CommodityRepository

# Initialize
geo_repo = GeographyRepository(graph, Geography)
commodity_repo = CommodityRepository(graph, Commodity)

# Create
france = Geography(name="France", level=0, iso_code="FRA")
france = geo_repo.save(france)

# Read
found = geo_repo.find_by_name("France")
all_countries = geo_repo.find_by_level(0)

# Update
france.iso_code = "FR"
geo_repo.save(france)

# Delete
geo_repo.delete(france)
```

### Relationships
```python
# Create entities with relationships
usa = Geography(name="United States", level=0)
france = Geography(name="France", level=0)

# Bidirectional trade relationship
france.trade_partners = [usa]
geo_repo.save(france)

# Lazy loading (query on access)
for partner in france.trade_partners:  # Query executed here
    print(partner.name)

# Eager loading (prevent N+1 queries)
france_with_partners = geo_repo.find_by_id(france.id, fetch=["trade_partners"])
```

### Custom Queries
```python
# Complex queries with @query decorator
@query("""
    MATCH (g1:Geography)-[:TRADES_WITH]->(g2:Geography)
    WHERE g1.name = $source
    RETURN g2
    ORDER BY g2.name
""", returns=Geography)
def find_trade_partners(self, source: str) -> List[Geography]:
    pass
```

### Integration with Existing API
```python
# ORM Knowledge Graph maintains same API
kg = ORMKnowledgeGraph(config)

# Natural language queries (same as before)
result = await kg.query_natural_language(
    "What commodities does France export to USA?"
)

# Graph analytics (same as before)
pagerank_results = kg.analyze_graph(
    algorithm="pagerank",
    filters={"commodity": "Corn"}
)

# But internally uses repositories
countries = kg.geography_repo.find_all_countries()
```

## Migration Guide

### Step 1: Use ORM alongside existing code
```python
# Import both
from src.core.knowledge_graph import TijaraKnowledgeGraph  # Old
from src.core.orm_knowledge_graph import ORMKnowledgeGraph  # New

# Gradually replace usage
kg_orm = ORMKnowledgeGraph(config)
```

### Step 2: Replace manual queries with repositories
```python
# Old way
query = "MATCH (g:Geography {name: 'France'}) RETURN g"
result = kg.falkordb.execute_query(query)

# New way
france = kg_orm.geography_repo.find_by_name("France")
```

### Step 3: Use entity models for data ingestion
```python
# Old way
entity_id = kg.falkordb.create_entity('Geography', {'name': 'France', 'level': 0})

# New way
france = Geography(name='France', level=0)
france = kg_orm.geography_repo.save(france)
```

## Testing

```bash
# Run ORM tests
pytest tests/test_orm_models.py
pytest tests/test_orm_repositories.py
pytest tests/integration/test_orm_integration.py
```

## Performance Considerations

- **Lazy Loading**: Relationships loaded on-demand (prevents fetching unnecessary data)
- **Eager Loading**: Use `fetch=["relationships"]` to prevent N+1 queries
- **Query Caching**: ORM caches parsed query specifications
- **Batch Operations**: Use `save_all()` for bulk inserts

## Comparison with Baseline

| Feature | Baseline (Raw Client) | ORM Implementation |
|---------|----------------------|---------------------|
| **Entity Definition** | Manual dict construction | Declarative `@node` classes |
| **Queries** | Manual Cypher strings | Derived methods + `@query` decorator |
| **Type Safety** | ❌ No type hints | ✅ Full type hints |
| **Relationships** | Manual relationship creation | Automatic with `@relationship` |
| **Validation** | Manual validation | Built-in type conversion |
| **Maintainability** | Low (scattered Cypher) | High (centralized models) |
| **Testability** | Medium | High (mock repositories) |

## File Structure

```
tijara-knowledge-graph-orm/
├── src/
│   ├── models/              # NEW: ORM entity models
│   │   ├── __init__.py
│   │   ├── geography.py
│   │   ├── commodity.py
│   │   ├── balance_sheet.py
│   │   ├── production_area.py
│   │   ├── component.py
│   │   └── indicator.py
│   ├── repositories/        # NEW: Repository pattern
│   │   ├── __init__.py
│   │   ├── geography_repository.py
│   │   ├── commodity_repository.py
│   │   └── balance_sheet_repository.py
│   ├── core/
│   │   ├── orm_knowledge_graph.py  # NEW: ORM-based KG interface
│   │   ├── knowledge_graph.py      # EXISTING: Original implementation
│   │   └── ...
│   ├── ontology/
│   ├── analytics/
│   └── rag/
├── requirements.txt         # UPDATED: Added falkordb-orm
└── ORM_IMPLEMENTATION.md    # This file
```

## Next Steps

1. ✅ Entity models created
2. ✅ Repositories implemented
3. ✅ ORM Knowledge Graph interface
4. 🔄 Add comprehensive tests
5. 🔄 Migrate analytics to use repositories
6. 🔄 Update data loading scripts
7. 🔄 Performance benchmarking

## Resources

- [FalkorDB ORM Documentation](https://github.com/FalkorDB/falkordb-py-orm)
- [Original Tijara Knowledge Graph](../tijara-knowledge-graph/README.md)
- [Design Document](https://github.com/FalkorDB/falkordb-py-orm/blob/main/DESIGN.md)
