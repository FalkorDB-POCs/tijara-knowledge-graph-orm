"""
Repository for BalanceSheet entities.
"""

from typing import List, Optional
from falkordb_orm import Repository, query
from ..models.balance_sheet import BalanceSheet


class BalanceSheetRepository(Repository[BalanceSheet]):
    """
    Repository for querying BalanceSheet entities.
    
    Provides derived query methods and custom queries for balance sheet data.
    """
    
    # Derived query methods (auto-implemented by ORM)
    # - find_by_product_name(product_name: str) -> List[BalanceSheet]
    # - find_by_season(season: str) -> List[BalanceSheet]
    
    @query(
        """
        MATCH (bs:BalanceSheet)-[:FOR_GEOGRAPHY]->(g:Geography)
        WHERE g.name = $geography_name
        RETURN bs
        ORDER BY bs.product_name
        """,
        returns=BalanceSheet
    )
    def find_by_geography(self, geography_name: str) -> List[BalanceSheet]:
        """Find all balance sheets for a geography."""
        pass
    
    @query(
        """
        MATCH (bs:BalanceSheet)-[:FOR_COMMODITY]->(c:Commodity)
        WHERE c.name = $commodity_name
        RETURN bs
        ORDER BY bs.season DESC
        """,
        returns=BalanceSheet
    )
    def find_by_commodity(self, commodity_name: str) -> List[BalanceSheet]:
        """Find all balance sheets for a commodity."""
        pass
    
    @query(
        """
        MATCH (bs:BalanceSheet)-[:FOR_COMMODITY]->(c:Commodity),
              (bs)-[:FOR_GEOGRAPHY]->(g:Geography)
        WHERE c.name = $commodity_name AND g.name = $geography_name
        RETURN bs
        ORDER BY bs.season DESC
        """,
        returns=BalanceSheet
    )
    def find_by_commodity_and_geography(
        self, 
        commodity_name: str, 
        geography_name: str
    ) -> List[BalanceSheet]:
        """Find balance sheets for a specific commodity and geography combination."""
        pass
    
    @query(
        """
        MATCH (bs:BalanceSheet)
        WHERE toLower(bs.balance_sheet_id) CONTAINS toLower($search_term)
        RETURN bs
        ORDER BY bs.balance_sheet_id
        LIMIT $limit
        """,
        returns=BalanceSheet
    )
    def search_case_insensitive(self, search_term: str, limit: int = 20) -> List[BalanceSheet]:
        """Search balance sheets by ID (case-insensitive)."""
        pass
