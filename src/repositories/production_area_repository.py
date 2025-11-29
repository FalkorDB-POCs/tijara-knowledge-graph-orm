"""
Repository for ProductionArea entities.
"""

from typing import List, Optional
from falkordb_orm import Repository, query
from ..models.production_area import ProductionArea


class ProductionAreaRepository(Repository[ProductionArea]):
    """
    Repository for querying ProductionArea entities.
    
    Provides derived query methods and custom queries for production area data.
    """
    
    @query(
        """
        MATCH (pa:ProductionArea)-[:PRODUCES]->(c:Commodity)
        WHERE toLower(c.name) CONTAINS toLower($commodity_name)
        RETURN pa, c.name as commodity_name
        ORDER BY pa.name
        LIMIT $limit
        """,
        returns=ProductionArea
    )
    def find_by_commodity(self, commodity_name: str, limit: int = 20) -> List[ProductionArea]:
        """Find production areas that produce a commodity (case-insensitive)."""
        pass
    
    @query(
        """
        MATCH (pa:ProductionArea)
        WHERE toLower(pa.name) CONTAINS toLower($search_term)
        RETURN pa
        ORDER BY pa.name
        LIMIT $limit
        """,
        returns=ProductionArea
    )
    def search_case_insensitive(self, search_term: str, limit: int = 20) -> List[ProductionArea]:
        """Search production areas by name (case-insensitive)."""
        pass
