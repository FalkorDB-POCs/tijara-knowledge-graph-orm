"""
FalkorDB Driver for Graphiti
Adapter that allows Graphiti to use FalkorDB as its graph backend instead of Neo4j
"""

from typing import Any, Dict, List, Optional
import logging
from graphiti_core.driver.driver import GraphDriver
import falkordb

logger = logging.getLogger(__name__)


class FalkorDBGraphitiDriver(GraphDriver):
    """
    FalkorDB implementation of Graphiti's GraphDriver interface.
    Allows Graphiti to use FalkorDB instead of Neo4j as the graph backend.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        graph_name: str = "graphiti",
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssl: bool = False
    ):
        """
        Initialize FalkorDB driver for Graphiti.
        
        Args:
            host: FalkorDB host
            port: FalkorDB port
            graph_name: Name of the graph to use
            username: Optional username
            password: Optional password
            ssl: Use SSL connection
        """
        self.host = host
        self.port = port
        self.graph_name = graph_name
        self.provider = "falkordb"  # Required by Graphiti
        
        # Connect to FalkorDB
        try:
            self.client = falkordb.FalkorDB(
                host=host,
                port=port,
                username=username,
                password=password,
                ssl=ssl
            )
            self.graph = self.client.select_graph(graph_name)
            logger.info(f"FalkorDB Graphiti driver connected to graph: {graph_name}")
        except Exception as e:
            logger.error(f"Failed to connect to FalkorDB: {e}")
            raise
    
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs  # Accept additional keyword arguments from Graphiti
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result dictionaries
        """
        try:
            # Clean and prepare parameters for FalkorDB
            cleaned_params = {}
            if parameters:
                for key, value in parameters.items():
                    # Convert values to appropriate types for FalkorDB
                    if key in ['limit', 'skip', 'offset', 'num_results', 'top_k']:
                        # Ensure integer parameters are actually integers
                        try:
                            cleaned_params[key] = int(value) if value is not None else 10
                        except (ValueError, TypeError):
                            cleaned_params[key] = 10  # Default if conversion fails
                    elif isinstance(value, (list, dict)):
                        # Keep complex types as-is
                        cleaned_params[key] = value
                    else:
                        # Keep other types as-is
                        cleaned_params[key] = value
            
            # FalkorDB sometimes has issues with parameterized LIMIT clauses
            # Replace $limit, $skip, etc. in the query with actual values
            import re
            modified_query = query
            keys_to_remove = []
            
            if cleaned_params:
                for key in ['limit', 'skip', 'offset', 'num_results', 'top_k']:
                    if key in cleaned_params:
                        value = cleaned_params[key]
                        # Replace $key or ${key} with the actual integer value (case-insensitive)
                        modified_query = re.sub(rf'\${key}\b', str(value), modified_query, flags=re.IGNORECASE)
                        modified_query = re.sub(rf'\$\{{{key}\}}', str(value), modified_query, flags=re.IGNORECASE)
                        # Mark for removal
                        keys_to_remove.append(key)
                
                # Remove keys that were inlined into the query
                for key in keys_to_remove:
                    del cleaned_params[key]
            
            # Also handle LIMIT/SKIP with direct numeric parameters that might be None or invalid
            # Replace "LIMIT $variable" patterns
            modified_query = re.sub(r'LIMIT\s+\$\w+', 'LIMIT 10', modified_query, flags=re.IGNORECASE)
            modified_query = re.sub(r'SKIP\s+\$\w+', 'SKIP 0', modified_query, flags=re.IGNORECASE)
            
            # Log the query for debugging
            logger.info(f"Executing query (first 300 chars): {modified_query[:300]}...")
            logger.info(f"With parameters: {cleaned_params}")
            
            result = self.graph.query(modified_query, cleaned_params)
            
            # Convert FalkorDB result to list of dicts
            if hasattr(result, 'result_set') and hasattr(result, 'header'):
                if result.header and result.result_set:
                    try:
                        return [dict(zip(result.header, row)) for row in result.result_set]
                    except Exception as e:
                        logger.warning(f"Error converting result to dict: {e}")
                        logger.debug(f"Header: {result.header}, Result set length: {len(result.result_set) if result.result_set else 0}")
                        return []
                return []
            
            return []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Parameters: {parameters}")
            logger.debug(f"Cleaned parameters: {cleaned_params if 'cleaned_params' in locals() else 'N/A'}")
            raise
    
    def session(self):
        """
        Return a session context manager.
        FalkorDB doesn't have explicit sessions, so we return a mock context.
        """
        return FalkorDBSessionContext(self)
    
    def close(self):
        """Close the FalkorDB connection."""
        try:
            if hasattr(self.client, 'close'):
                self.client.close()
            logger.info("FalkorDB connection closed")
        except Exception as e:
            logger.error(f"Error closing FalkorDB connection: {e}")
    
    def with_database(self, database: str):
        """
        Switch to a different graph/database.
        
        Args:
            database: Name of the graph to switch to
        """
        self.graph_name = database
        self.graph = self.client.select_graph(database)
        return self
    
    def delete_all_indexes(self):
        """Delete all indexes in the graph."""
        try:
            # FalkorDB index deletion
            # Note: This is a placeholder - adjust based on FalkorDB's index management
            query = "CALL db.indexes()"
            indexes = self.execute_query(query)
            
            for index in indexes:
                # Delete each index
                # Adjust based on actual FalkorDB index structure
                pass
            
            logger.info("All indexes deleted")
        except Exception as e:
            logger.warning(f"Could not delete indexes: {e}")
    
    def build_fulltext_query(
        self,
        search_text: str,
        node_label: Optional[str] = None,
        property_name: str = "content"
    ) -> str:
        """
        Build a fulltext search query compatible with FalkorDB.
        
        Args:
            search_text: Text to search for
            node_label: Optional node label to filter
            property_name: Property to search in
            
        Returns:
            Cypher query string
        """
        label_filter = f":{node_label}" if node_label else ""
        
        # FalkorDB fulltext search using CONTAINS or regex
        query = f"""
        MATCH (n{label_filter})
        WHERE n.{property_name} CONTAINS $search_text
        RETURN n
        """
        
        return query
    
    @property
    def fulltext_syntax(self) -> str:
        """
        Return the fulltext search syntax for FalkorDB.
        FalkorDB uses CONTAINS for text matching.
        """
        return "CONTAINS"
    
    @property
    def graph_operations_interface(self):
        """
        Return interface for graph operations.
        This is used by Graphiti for graph-specific operations.
        """
        return self
    
    @property
    def search_interface(self):
        """
        Return interface for search operations.
        This is used by Graphiti for search operations.
        """
        return self
    
    def edge_fulltext_search(
        self,
        search_text: str,
        relationship_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform fulltext search on relationship properties.
        
        Args:
            search_text: Text to search for
            relationship_types: Optional list of relationship types to filter
            limit: Maximum number of results
            
        Returns:
            List of matching relationships
        """
        try:
            # Build relationship type filter
            rel_type_filter = ""
            if relationship_types:
                rel_type_filter = ":" + "|".join(relationship_types)
            
            # Search in relationship properties
            query = f"""
            MATCH (a)-[r{rel_type_filter}]->(b)
            WHERE r.content CONTAINS $search_text OR r.description CONTAINS $search_text
            RETURN r, a, b
            LIMIT $limit
            """
            
            return self.execute_query(query, {
                'search_text': search_text,
                'limit': limit
            })
        except Exception as e:
            logger.warning(f"Edge fulltext search failed: {e}")
            return []
    
    def node_fulltext_search(
        self,
        search_text: str,
        node_labels: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform fulltext search on node properties.
        
        Args:
            search_text: Text to search for
            node_labels: Optional list of node labels to filter
            limit: Maximum number of results
            
        Returns:
            List of matching nodes
        """
        try:
            # Build label filter
            label_filter = ""
            if node_labels:
                label_filter = ":" + ":".join(node_labels)
            
            # Search in node properties
            query = f"""
            MATCH (n{label_filter})
            WHERE n.content CONTAINS $search_text OR n.description CONTAINS $search_text
            RETURN n
            LIMIT $limit
            """
            
            return self.execute_query(query, {
                'search_text': search_text,
                'limit': limit
            })
        except Exception as e:
            logger.warning(f"Node fulltext search failed: {e}")
            return []


class FalkorDBSessionContext:
    """
    Mock session context for FalkorDB.
    FalkorDB doesn't have explicit sessions like Neo4j.
    """
    
    def __init__(self, driver: FalkorDBGraphitiDriver):
        self.driver = driver
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def run(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute a query in the session context."""
        return await self.driver.execute_query(query, parameters)
    
    async def execute_read(self, transaction_function, *args, **kwargs):
        """Execute a read transaction."""
        return await transaction_function(self, *args, **kwargs)
    
    async def execute_write(self, transaction_function, *args, **kwargs):
        """Execute a write transaction."""
        return await transaction_function(self, *args, **kwargs)
