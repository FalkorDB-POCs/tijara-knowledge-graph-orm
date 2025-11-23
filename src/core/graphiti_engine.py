"""
Graphiti Engine for GraphRAG capabilities
Integrates Graphiti for semantic search and LLM-powered knowledge retrieval
"""

from typing import Dict, List, Any, Optional
import logging
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.driver.falkordb_driver import FalkorDriver

logger = logging.getLogger(__name__)


class GraphitiEngine:
    """Engine for GraphRAG using Graphiti."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Graphiti engine with FalkorDB backend."""
        self.config = config
        
        # Initialize Graphiti client with FalkorDB driver
        # Graphiti will use FalkorDB instead of Neo4j as the graph backend
        try:
            # Get FalkorDB connection settings from config
            # These should be in the parent 'falkordb' config section
            falkordb_config = config.get('falkordb_connection', {})
            
            # Create official FalkorDB driver for Graphiti
            # Use configured graphiti database for semantic search
            falkordb_driver = FalkorDriver(
                host=falkordb_config.get('host', 'localhost'),
                port=falkordb_config.get('port', 6379),
                username=falkordb_config.get('username'),
                password=falkordb_config.get('password'),
                database=falkordb_config.get('graph_name', 'graphiti')  # Use Graphiti graph from config
            )
            
            # Initialize Graphiti with the FalkorDB driver
            # Note: Graphiti will initialize default OpenAI clients if not provided
            # This requires OPENAI_API_KEY environment variable to be set
            self.client = Graphiti(
                graph_driver=falkordb_driver
            )
            
            logger.info(f"Graphiti client initialized with FalkorDB at {falkordb_config.get('host', 'localhost')}:{falkordb_config.get('port', 6379)}")
        except Exception as e:
            logger.warning(f"Could not initialize Graphiti client: {e}. GraphRAG features will be limited.")
            logger.info("To enable Graphiti, ensure FalkorDB is running and OPENAI_API_KEY is set.")
            self.client = None
        
        logger.info("Graphiti engine initialized")
    
    async def index_entities(self, entity_ids: List[str]) -> None:
        """Index entities for semantic search."""
        # In production, fetch entity details from FalkorDB and add to Graphiti
        logger.info(f"Indexing {len(entity_ids)} entities in Graphiti")
        
        if not self.client:
            logger.warning("Graphiti client not initialized, skipping indexing")
            return
        
        # Example: Add episodes to Graphiti
        from datetime import datetime
        for entity_id in entity_ids:
            try:
                await self.client.add_episode(
                    name=f"entity_{entity_id}",
                    episode_body=f"Entity {entity_id}",  # Fetch actual content
                    source=EpisodeType.text,
                    source_description="FalkorDB",
                    reference_time=datetime.now()
                )
            except Exception as e:
                logger.error(f"Failed to index entity {entity_id}: {e}")
    
    async def add_entity_episode(
        self,
        entity_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an entity as a Graphiti episode with embeddings."""
        if not self.client:
            logger.warning("Graphiti client not initialized, skipping episode creation")
            return
        
        try:
            # Create episode with the entity content
            # Graphiti will automatically generate embeddings using OpenAI
            await self.client.add_episode(
                name=f"entity_{entity_id}",
                episode_body=content,
                source=EpisodeType.text,
                source_description=metadata.get('source', 'FalkorDB') if metadata else 'FalkorDB',
                reference_time=None  # Can add timestamp if needed
            )
            logger.info(f"Added entity {entity_id} to Graphiti with content: {content[:100]}...")
        except Exception as e:
            logger.error(f"Failed to add entity episode {entity_id}: {e}")
    
    async def extract_entities_from_text(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """Extract entities from text using Graphiti's entity extraction."""
        if not self.client:
            logger.warning("Graphiti client not initialized, returning empty entities")
            return []
        
        try:
            # Use Graphiti to extract entities from text
            # This uses LLM to identify entities, relationships, and facts
            from datetime import datetime
            await self.client.add_episode(
                name="query_context",
                episode_body=text,
                source=EpisodeType.text,
                source_description="user_query",
                reference_time=datetime.now()
            )
            
            # Search for related entities
            results = await self.client.search(
                query=text,
                num_results=10
            )
            
            entities = []
            for result in results:
                entities.append({
                    'id': getattr(result, 'id', None),
                    'name': getattr(result, 'name', ''),
                    'type': getattr(result, 'type', ''),
                    'content': getattr(result, 'content', ''),
                    'score': getattr(result, 'score', 0.0)
                })
            
            return entities
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic search over the knowledge graph."""
        if not self.client:
            logger.warning("Graphiti client not initialized")
            return []
        
        try:
            # Search using Graphiti
            results = await self.client.search(
                query=query,
                num_results=top_k
            )
            
            logger.info(f"Graphiti search returned {len(results)} results for query: {query[:50]}...")
            
            formatted_results = []
            for r in results:
                # Handle different possible attribute names from Graphiti
                entity_id = getattr(r, 'uuid', getattr(r, 'id', getattr(r, 'entity_id', 'unknown')))
                
                # Try multiple content fields
                content = getattr(r, 'content', None)
                if not content:
                    content = getattr(r, 'fact', None)
                if not content:
                    content = getattr(r, 'summary', None)
                if not content:
                    content = getattr(r, 'name', 'No content')
                
                # Get score
                score = getattr(r, 'score', getattr(r, 'distance', 0.0))
                
                # Get metadata - this should contain source information
                metadata = getattr(r, 'metadata', {})
                if not isinstance(metadata, dict):
                    metadata = {}
                
                # Extract source from metadata or node properties
                source_name = metadata.get('source', metadata.get('source_description', 'Knowledge Graph'))
                
                formatted_result = {
                    'entity_id': str(entity_id),
                    'content': str(content) if content else '',
                    'score': float(score) if score else 0.0,
                    'metadata': {
                        'source': source_name,
                        **metadata
                    }
                }
                
                formatted_results.append(formatted_result)
                logger.debug(f"Formatted result: id={entity_id}, source={source_name}, score={score}, content_len={len(str(content))}")
            
            return formatted_results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def build_context(
        self,
        query: str,
        max_context_items: int = 5
    ) -> Dict[str, Any]:
        """Build context for LLM from graph."""
        # Search relevant entities
        search_results = await self.semantic_search(query, top_k=max_context_items)
        
        # Build context string
        context_parts = []
        for result in search_results:
            context_parts.append(
                f"- {result['content']} (relevance: {result['score']:.2f})"
            )
        
        return {
            'context': "\n".join(context_parts),
            'sources': search_results
        }
    
    def is_ready(self) -> bool:
        """Check if Graphiti is ready."""
        try:
            # Simple health check
            return self.client is not None
        except Exception as e:
            logger.error(f"Graphiti health check failed: {e}")
            return False
