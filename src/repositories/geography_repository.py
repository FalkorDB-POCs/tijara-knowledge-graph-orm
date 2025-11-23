"""
Repository for Geography entities.
"""

from typing import List, Optional
from falkordb_orm import Repository, query
from ..models.geography import Geography


class GeographyRepository(Repository[Geography]):
    """
    Repository for querying Geography entities.
    
    Provides derived query methods and custom queries for geographic data.
    """
    
    # Derived query methods (auto-implemented by ORM)
    # - find_by_name(name: str) -> Optional[Geography]
    # - find_by_level(level: int) -> List[Geography]
    # - find_by_iso_code(iso_code: str) -> Optional[Geography]
    # - find_by_gid_code(gid_code: str) -> Optional[Geography]
    
    @query(
        """
        MATCH (g:Geography)
        WHERE g.level = $level AND g.name CONTAINS $name_fragment
        RETURN g
        ORDER BY g.name
        """,
        returns=Geography
    )
    def search_by_level_and_name(self, level: int, name_fragment: str) -> List[Geography]:
        """Search geographies by level and name fragment."""
        pass
    
    @query(
        """
        MATCH (child:Geography)-[:LOCATED_IN]->(parent:Geography)
        WHERE parent.name = $parent_name
        RETURN child
        ORDER BY child.name
        """,
        returns=Geography
    )
    def find_children_of(self, parent_name: str) -> List[Geography]:
        """Find all child geographies of a parent."""
        pass
    
    @query(
        """
        MATCH (g1:Geography)-[t:TRADES_WITH]->(g2:Geography)
        WHERE g1.name = $source_country
        RETURN g2
        """,
        returns=Geography
    )
    def find_trade_partners(self, source_country: str) -> List[Geography]:
        """Find all trade partners for a country."""
        pass
    
    @query(
        """
        MATCH (g:Geography)
        WHERE g.level = 0
        RETURN g
        ORDER BY g.name
        """,
        returns=Geography
    )
    def find_all_countries(self) -> List[Geography]:
        """Find all country-level geographies."""
        pass
