"""
Repository for Commodity entities.
"""

from typing import List, Optional
from falkordb_orm import Repository, query
from ..models.commodity import Commodity


class CommodityRepository(Repository[Commodity]):
    """
    Repository for querying Commodity entities.
    
    Provides derived query methods and custom queries for commodity data.
    """
    
    # Derived query methods (auto-implemented by ORM)
    # - find_by_name(name: str) -> Optional[Commodity]
    # - find_by_level(level: int) -> List[Commodity]
    # - find_by_category(category: str) -> List[Commodity]
    
    @query(
        """
        MATCH (c:Commodity)
        WHERE c.level = 0
        RETURN c
        ORDER BY c.name
        """,
        returns=Commodity
    )
    def find_all_categories(self) -> List[Commodity]:
        """Find all top-level commodity categories."""
        pass
    
    @query(
        """
        MATCH (child:Commodity)-[:SUBCLASS_OF]->(parent:Commodity)
        WHERE parent.name = $parent_name
        RETURN child
        ORDER BY child.name
        """,
        returns=Commodity
    )
    def find_children_of(self, parent_name: str) -> List[Commodity]:
        """Find all child commodities of a parent."""
        pass
    
    @query(
        """
        MATCH path = (c:Commodity)-[:SUBCLASS_OF*]->(root:Commodity)
        WHERE c.name = $commodity_name AND root.level = 0
        RETURN root
        """,
        returns=Commodity
    )
    def find_category_for(self, commodity_name: str) -> Optional[Commodity]:
        """Find the top-level category for a commodity."""
        pass
    
    @query(
        """
        MATCH (c:Commodity)
        WHERE c.name CONTAINS $search_term
        RETURN c
        ORDER BY c.level, c.name
        LIMIT $limit
        """,
        returns=Commodity
    )
    def search_by_name(self, search_term: str, limit: int = 20) -> List[Commodity]:
        """Search commodities by name fragment."""
        pass
