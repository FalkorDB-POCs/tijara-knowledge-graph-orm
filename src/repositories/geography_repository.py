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
    
    def find_by_name(self, name: str) -> Optional[Geography]:
        """Find geography by exact name match."""
        cypher = """
        MATCH (g:Geography)
        WHERE g.name = $name
        RETURN g
        LIMIT 1
        """
        result = self.graph.query(cypher, {'name': name})
        if result.result_set:
            return self.mapper.map_from_record(result.result_set[0], Geography, header=result.header)
        return None
    
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
    
    @query(
        """
        MATCH (g:Geography)
        WHERE toLower(g.name) CONTAINS toLower($search_term) OR toLower(g.gid_code) = toLower($search_term)
        RETURN g
        ORDER BY g.level, g.name
        LIMIT $limit
        """,
        returns=Geography
    )
    def search_case_insensitive(self, search_term: str, limit: int = 20) -> List[Geography]:
        """Search geographies by name or code (case-insensitive)."""
        pass
    
    @query(
        """
        MATCH (g1:Geography)-[t:TRADES_WITH]->(g2:Geography)
        WHERE toLower(g1.name) CONTAINS toLower($search_term) OR toLower(g2.name) CONTAINS toLower($search_term)
        RETURN g1, g2, t.commodity as commodity, t.flow_type as flow_type
        LIMIT $limit
        """
    )
    def find_trade_flows_by_geography(self, search_term: str, limit: int = 20):
        """Find trade flows involving a geography (case-insensitive)."""
        # Note: This returns raw query results (not Geography entities)
        pass
