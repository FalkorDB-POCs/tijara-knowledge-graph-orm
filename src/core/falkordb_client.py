"""
FalkorDB Client for graph database operations
"""

from typing import Dict, List, Optional, Any
import falkordb
import logging

logger = logging.getLogger(__name__)


class FalkorDBClient:
    """Client for interacting with FalkorDB graph database."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize FalkorDB connection."""
        self.config = config
        self.graph_name = config['graph_name']
        
        # Connect to FalkorDB
        self.client = falkordb.FalkorDB(
            host=config['host'],
            port=config['port'],
            username=config.get('username'),
            password=config.get('password'),
            ssl=config.get('ssl', False)
        )
        
        self.graph = self.client.select_graph(self.graph_name)
        logger.info(f"Connected to FalkorDB graph: {self.graph_name}")
    
    def create_entity(self, entity_type: str, properties: Dict[str, Any]) -> str:
        """Create a new entity node in the graph."""
        # Build property string for Cypher
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        
        query = f"""
        CREATE (n:{entity_type} {{{props_str}}})
        RETURN id(n) as entity_id
        """
        
        result = self.graph.query(query, properties)
        return str(result.result_set[0][0])
    
    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create relationship between two nodes."""
        props = properties or {}
        props_str = ", ".join([f"{k}: ${k}" for k in props.keys()])
        
        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $source_id AND id(b) = $target_id
        CREATE (a)-[r:{relationship_type} {{{props_str}}}]->(b)
        RETURN id(r) as rel_id
        """
        
        params = {**props, 'source_id': int(source_id), 'target_id': int(target_id)}
        result = self.graph.query(query, params)
        return str(result.result_set[0][0])
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """Execute raw Cypher query."""
        result = self.graph.query(query, parameters or {})
        results = []
        
        # FalkorDB header is a list of [column_id, column_name] pairs
        # Extract just the column names
        column_names = [header_item[1] if isinstance(header_item, list) else header_item 
                        for header_item in result.header]
        
        for row in result.result_set:
            row_dict = {}
            for i in range(len(column_names)):
                key = column_names[i]
                value = row[i]
                row_dict[key] = value
            results.append(row_dict)
        return results
    
    def get_subgraph(self, filters: Dict[str, Any]) -> Any:
        """Extract subgraph based on filters."""
        # Build WHERE clause from filters
        conditions = [f"n.{k} = ${k}" for k in filters.keys()]
        where_clause = " AND ".join(conditions)
        
        query = f"""
        MATCH (n)-[r]-(m)
        WHERE {where_clause}
        RETURN n, r, m
        """
        
        return self.execute_query(query, filters)
    
    def traverse_relationships(
        self,
        start_id: str,
        max_depth: int = 5,
        relationship_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """Traverse relationships from a starting node."""
        rel_filter = ""
        if relationship_types:
            rel_filter = ":" + "|".join(relationship_types)
        
        query = f"""
        MATCH path = (start)-[{rel_filter}*1..{max_depth}]-(connected)
        WHERE id(start) = $start_id
        RETURN connected, length(path) as distance, path
        """
        
        return self.execute_query(query, {'start_id': int(start_id)})
    
    def search_entities(
        self,
        search_term: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search entities by text."""
        type_filter = ""
        if entity_types:
            type_filter = ":" + "|".join(entity_types)
        
        query = f"""
        MATCH (n{type_filter})
        WHERE n.name CONTAINS $search_term OR n.description CONTAINS $search_term
        RETURN n
        LIMIT {limit}
        """
        
        return self.execute_query(query, {'search_term': search_term})
    
    def get_entity_history(
        self,
        entity_id: str,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """Get version history for an entity."""
        query = """
        MATCH (n)-[:VERSION_OF*]->(history)
        WHERE id(n) = $entity_id
        RETURN history
        ORDER BY history.version DESC
        """
        
        return self.execute_query(query, {'entity_id': int(entity_id)})
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        stats = {}
        
        # Node counts by type
        node_query = "MATCH (n) RETURN labels(n) as type, count(n) as count"
        node_counts = self.execute_query(node_query)
        stats['nodes'] = {}
        for r in node_counts:
            if r['type'] and len(r['type']) > 0:
                # Use first label as the type
                label = r['type'][0] if isinstance(r['type'], list) else str(r['type'])
                stats['nodes'][label] = r['count']
        
        # Relationship counts
        rel_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count"
        rel_counts = self.execute_query(rel_query)
        stats['relationships'] = {r['type']: r['count'] for r in rel_counts}
        
        return stats
    
    def is_connected(self) -> bool:
        """Check if connected to FalkorDB."""
        try:
            self.graph.query("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"FalkorDB connection check failed: {e}")
            return False
