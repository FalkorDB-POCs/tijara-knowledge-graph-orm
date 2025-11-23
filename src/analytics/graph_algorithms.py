"""
Graph Analytics - Algorithms for analyzing the knowledge graph
Uses FalkorDB native algorithms for optimal performance.
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class GraphAnalytics:
    """
    Provides graph analytics algorithms for the knowledge graph.
    Includes centrality measures, community detection, and pathfinding.
    """
    
    def __init__(self, falkordb_client):
        """
        Initialize graph analytics.
        
        Args:
            falkordb_client: FalkorDB client instance
        """
        self.db = falkordb_client
    
    def pagerank(
        self,
        filters: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Calculate PageRank centrality using FalkorDB's native algorithm.
        
        FalkorDB's algo.pageRank takes (node_label, relationship_type) as arguments.
        
        Args:
            filters: Not used for native algorithm (runs on entire graph)
            parameters: Algorithm parameters:
                - node_label: Node label to compute PageRank on (default: '' for all)
                - relationship_type: Relationship type to traverse (default: '')
            
        Returns:
            Dictionary mapping node IDs to PageRank scores
        """
        logger.info("Calculating PageRank using FalkorDB native algorithm")
        
        # Extract parameters for FalkorDB PageRank
        node_label = parameters.get('node_label', '') if parameters else ''
        relationship_type = parameters.get('relationship_type', '') if parameters else ''
        
        # If filters provided, try to infer label/relationship
        if filters:
            # Try to infer node label from indicator filter
            if 'indicator' in filters:
                node_label = filters['indicator']  # e.g., 'Production', 'Exports'
            
            # Use a default relationship if not specified
            if not relationship_type:
                relationship_type = 'HAS_COMMODITY'  # Default to commodity relationships
        
        try:
            # Build query with proper FalkorDB PageRank signature
            query = f"CALL algo.pageRank('{node_label}', '{relationship_type}') YIELD node, score RETURN id(node) as node_id, score ORDER BY score DESC"
            
            logger.info(f"Running PageRank on label='{node_label}' relationship='{relationship_type}'")
            
            # Execute PageRank
            result = self.db.execute_query(query)
            
            # Convert to dict
            pagerank_scores = {}
            for row in result:
                node_id = str(row['node_id'])
                score = row['score']
                pagerank_scores[node_id] = score
            
            logger.info(f"PageRank calculated for {len(pagerank_scores)} nodes")
            return pagerank_scores
        
        except Exception as e:
            logger.error(f"Error calculating PageRank: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    
    def centrality(
        self,
        algorithm: str = "betweenness",
        filters: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Calculate betweenness centrality using FalkorDB's native algorithm.
        
        FalkorDB's algo.betweenness takes a node collection as input.
        
        Args:
            algorithm: Type of centrality (currently only 'betweenness' supported)
            filters: Not used for native algorithm
            parameters: Algorithm parameters (node_collection for filtering)
            
        Returns:
            Dictionary mapping node IDs to centrality scores
        """
        logger.info(f"Calculating {algorithm} centrality using FalkorDB native algorithm")
        
        if algorithm != "betweenness":
            logger.warning(f"Only betweenness centrality is supported, got: {algorithm}")
            return {}
        
        try:
            # FalkorDB betweenness takes an empty dict {} as parameter for all nodes
            query = "CALL algo.betweenness({}) YIELD node, score RETURN id(node) as node_id, score ORDER BY score DESC"
            
            logger.info("Running betweenness centrality on all nodes")
            
            # Execute betweenness
            result = self.db.execute_query(query)
            
            # Convert to dict
            centrality_scores = {}
            for row in result:
                node_id = str(row['node_id'])
                score = row['score']
                centrality_scores[node_id] = score
            
            logger.info(f"Betweenness centrality calculated for {len(centrality_scores)} nodes")
            return centrality_scores
        
        except Exception as e:
            logger.error(f"Error calculating centrality: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def community_detection(
        self,
        algorithm: str = "label_propagation",
        filters: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """
        Detect communities using FalkorDB's native label propagation algorithm.
        
        FalkorDB's algo.labelPropagation takes a node collection as input.
        
        Args:
            algorithm: Detection algorithm (only 'label_propagation' supported)
            filters: Not used for native algorithm
            parameters: Algorithm parameters
            
        Returns:
            Dictionary mapping node IDs to community IDs
        """
        logger.info(f"Detecting communities using FalkorDB native label propagation")
        
        if algorithm not in ["label_propagation", "louvain"]:
            logger.warning(f"Only label_propagation is supported, got: {algorithm}")
            return {}
        
        try:
            # FalkorDB labelPropagation takes an empty dict {} as parameter for all nodes
            query = "CALL algo.labelPropagation({}) YIELD node, communityId RETURN id(node) as node_id, communityId"
            
            logger.info("Running label propagation on all nodes")
            
            # Execute label propagation
            result = self.db.execute_query(query)
            
            # Convert to dict
            communities = {}
            for row in result:
                node_id = str(row['node_id'])
                community_id = row['communityId']
                communities[node_id] = community_id
            
            logger.info(f"Label propagation found communities for {len(communities)} nodes")
            return communities
        
        except Exception as e:
            logger.error(f"Error detecting communities: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def shortest_path(
        self,
        source: str,
        target: str,
        filters: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Find paths from source node using BFS with FalkorDB's native algorithm.
        
        FalkorDB's algo.BFS takes (sourceNode, maxDepth, relationshipType).
        
        Args:
            source: Source node ID
            target: Target node ID (not used with BFS, returns all reachable nodes)
            filters: Not used
            parameters: Algorithm parameters:
                - max_depth: Maximum traversal depth (default: 5)
                - relationship_type: Relationship type to traverse (default: '')
            
        Returns:
            Dictionary with 'nodes' and 'edges' lists from BFS traversal
        """
        logger.info(f"Running BFS from node {source}")
        
        # Extract parameters
        max_depth = parameters.get('max_depth', 5) if parameters else 5
        relationship_type = parameters.get('relationship_type', '') if parameters else ''
        
        try:
            # First get the source node
            source_query = f"MATCH (n) WHERE id(n) = {source} RETURN n"
            source_result = self.db.execute_query(source_query)
            
            if not source_result:
                logger.warning(f"Source node {source} not found")
                return {'nodes': [], 'edges': []}
            
            source_node = source_result[0]['n']
            
            # Build BFS query - need to pass the actual node object
            # Since we can't pass node objects via execute_query, we'll use a different approach
            # Use inline MATCH to get the source node
            if relationship_type:
                query = f"""
                MATCH (source)
                WHERE id(source) = {source}
                CALL algo.BFS(source, {max_depth}, '{relationship_type}')
                YIELD nodes, edges
                RETURN nodes, edges
                """
            else:
                query = f"""
                MATCH (source)
                WHERE id(source) = {source}
                CALL algo.BFS(source, {max_depth}, '')
                YIELD nodes, edges
                RETURN nodes, edges
                """
            
            logger.info(f"Running BFS with max_depth={max_depth}, relationship_type='{relationship_type}'")
            
            # Execute BFS
            result = self.db.execute_query(query)
            
            if not result:
                return {'nodes': [], 'edges': []}
            
            # Extract nodes and edges
            nodes_list = result[0].get('nodes', [])
            edges_list = result[0].get('edges', [])
            
            # Convert to node IDs
            node_ids = []
            for node in nodes_list:
                if hasattr(node, 'id'):
                    node_ids.append(str(node.id))
            
            edge_ids = []
            for edge in edges_list:
                if hasattr(edge, 'id'):
                    edge_ids.append(str(edge.id))
            
            logger.info(f"BFS found {len(node_ids)} nodes and {len(edge_ids)} edges")
            return {'nodes': node_ids, 'edges': edge_ids}
        
        except Exception as e:
            logger.error(f"Error running BFS: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'nodes': [], 'edges': []}
    
    
    def _build_filter_query(self, filters: Optional[Dict[str, Any]] = None) -> str:
        """
        Build a Cypher query based on filters.
        
        Args:
            filters: Filter conditions
            
        Returns:
            Cypher query string
        """
        if not filters:
            return "MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 1000"
        
        # Build WHERE clause from filters
        where_clauses = []
        for key, value in filters.items():
            where_clauses.append(f"a.{key} = '{value}' OR b.{key} = '{value}'")
        
        where_clause = " OR ".join(where_clauses) if where_clauses else "true"
        
        query = f"""
        MATCH (a)-[r]->(b)
        WHERE {where_clause}
        RETURN a, r, b
        LIMIT 1000
        """
        
        return query
    
    def get_subgraph(
        self,
        node_id: str,
        depth: int = 2,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract a subgraph around a specific node.
        
        Args:
            node_id: Central node ID
            depth: Depth of traversal
            filters: Filters to apply
            
        Returns:
            Dictionary with nodes and relationships
        """
        logger.info(f"Extracting subgraph around {node_id} with depth {depth}")
        
        query = f"""
        MATCH path = (n)-[*1..{depth}]-(m)
        WHERE id(n) = '{node_id}'
        RETURN path
        LIMIT 100
        """
        
        try:
            result = self.db.execute_query(query) if hasattr(self.db, 'execute_query') else []
            
            nodes = set()
            relationships = []
            
            for record in result:
                if 'path' in record:
                    # Extract nodes and relationships from path
                    # This is simplified - actual implementation depends on result format
                    pass
            
            return {
                'nodes': list(nodes),
                'relationships': relationships
            }
        
        except Exception as e:
            logger.error(f"Error extracting subgraph: {e}")
            return {'nodes': [], 'relationships': []}
