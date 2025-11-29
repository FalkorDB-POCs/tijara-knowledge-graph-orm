"""
ORM-based Tijara Knowledge Graph Interface
Uses FalkorDB ORM for cleaner, type-safe entity management
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import logging

import falkordb
from ..models import Geography, Commodity, ProductionArea, BalanceSheet, Component, Indicator
from ..repositories import GeographyRepository, CommodityRepository, BalanceSheetRepository
from ..repositories.secure_repository_factory import create_secure_repository
from ..security.context import SecurityContext
from ..security.policy_manager import PolicyManager
from .graphiti_engine import GraphitiEngine
from ..ontology.schema import OntologySchema
from ..analytics.graph_algorithms import GraphAnalytics
from ..analytics.spatial_ops import SpatialOperations
from ..rag.query_engine import QueryEngine

logger = logging.getLogger(__name__)


class ORMKnowledgeGraph:
    """
    ORM-based Knowledge Graph interface using falkordb-py-orm.
    
    Provides the same high-level API as TijaraKnowledgeGraph but uses
    entity models and repositories instead of raw Cypher queries.
    """
    
    def __init__(self, config: Dict[str, Any], security_context: Optional[SecurityContext] = None):
        """
        Initialize the ORM-based knowledge graph.
        
        Args:
            config: Configuration dictionary with FalkorDB, Graphiti, and other settings
            security_context: Optional security context for data-level filtering
        """
        self.config = config
        self.security_context = security_context
        
        # Initialize FalkorDB connection
        self.client = falkordb.FalkorDB(
            host=config['falkordb']['host'],
            port=config['falkordb']['port'],
            username=config['falkordb'].get('username'),
            password=config['falkordb'].get('password')
        )
        self.graph = self.client.select_graph(config['falkordb']['graph_name'])
        
        # Set graph on security context if provided
        # IMPORTANT: Do NOT overwrite if the context already points to the RBAC graph.
        # Only attach the data graph when no graph was set (e.g., programmatic usage).
        if security_context and security_context.graph is None:
            security_context.graph = self.graph
        
        # Initialize security policy
        self.security_policy = None
        if security_context and not security_context.is_superuser:
            try:
                self.security_policy = PolicyManager.initialize_policy(self.graph)
                logger.info("Security policy initialized")
            except Exception as e:
                logger.warning(f"Security policy initialization failed: {e}")
        
        # Initialize repositories (with security if context provided)
        self.geography_repo = create_secure_repository(
            GeographyRepository, self.graph, Geography, security_context
        )
        self.commodity_repo = create_secure_repository(
            CommodityRepository, self.graph, Commodity, security_context
        )
        self.balance_sheet_repo = create_secure_repository(
            BalanceSheetRepository, self.graph, BalanceSheet, security_context
        )
        
        # Initialize other components (keep existing)
        self.graphiti = GraphitiEngine(config['graphiti'])
        self.ontology = OntologySchema(config.get('ontology_path'))
        self.analytics = GraphAnalytics(self)  # Pass self instead of falkordb_client
        self.spatial = SpatialOperations(self, config.get('spatial', {}))
        
        # Initialize RAG engine
        self.query_engine = QueryEngine(
            falkordb=self,
            graphiti=self.graphiti,
            config=config.get('rag', {})
        )
        
        logger.info("ORM-based Tijara Knowledge Graph initialized successfully")
    
    # ========== Natural Language Query Interface ==========
    
    async def query_natural_language(
        self, 
        question: str, 
        context: Optional[Dict[str, Any]] = None,
        return_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Answer natural language questions using GraphRAG.
        
        Same API as TijaraKnowledgeGraph.query_natural_language()
        """
        logger.info(f"Processing natural language query: {question}")
        
        result = await self.query_engine.process_query(
            question=question,
            context=context or {},
            return_sources=return_sources
        )
        
        return {
            'answer': result['answer'],
            'sources': result.get('sources', []) if return_sources else [],
            'confidence': result.get('confidence', 0.0),
            'retrieved_entities': result.get('entities', []),
            'query_graph': result.get('subgraph')
        }
    
    # ========== Data Ingestion Interface ==========
    
    async def ingest_data(
        self,
        data: Union[Dict, List[Dict]],
        metadata: Dict[str, Any],
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest data using ORM entities with automatic relationships.
        
        Example:
            kg.ingest_data(
                data={'value': 1000, 'year': 2023},
                metadata={'commodity': 'Corn', 'country': 'USA', 'type': 'Production'}
            )
        """
        logger.info(f"Ingesting data with metadata: {metadata}")
        
        # Validate against ontology if requested
        if validate:
            validation_result = self.ontology.validate_data(data, metadata)
            if not validation_result['valid']:
                raise ValueError(f"Data validation failed: {validation_result['errors']}")
        
        entities_created = []
        data_list = data if isinstance(data, list) else [data]
        
        # Get or create concept entities using repositories
        commodity = None
        if metadata.get('commodity'):
            commodity = self.commodity_repo.find_by_name(metadata['commodity'])
            if not commodity:
                commodity = Commodity(
                    name=metadata['commodity'],
                    level=1  # Assume type level
                )
                commodity = self.commodity_repo.save(commodity)
        
        geography = None
        geo_name = metadata.get('region') or metadata.get('country')
        if geo_name:
            geography = self.geography_repo.find_by_name(geo_name)
            if not geography:
                geography = Geography(
                    name=geo_name,
                    level=0 if not metadata.get('region') else 1
                )
                geography = self.geography_repo.save(geography)
        
        # Create balance sheets or other entities based on data type
        for record in data_list:
            if metadata.get('type') in ['Production', 'Exports', 'Imports', 'Consumption']:
                # Create balance sheet
                balance_sheet = BalanceSheet(
                    product_name=metadata.get('commodity', 'Unknown'),
                    season=f"{record.get('year', 2023)}/{record.get('year', 2023)+1}",
                    unit=metadata.get('unit', 'metric tons')
                )
                
                # Set relationships
                if commodity:
                    balance_sheet.commodity = commodity
                if geography:
                    balance_sheet.geography = geography
                
                # Save with cascade (will create relationships)
                saved = self.balance_sheet_repo.save(balance_sheet)
                entities_created.append(saved.id)
                
                # Add to Graphiti for semantic search
                if self.graphiti and self.graphiti.is_ready():
                    try:
                        from graphiti_core.nodes import EpisodeType
                        
                        description = self._create_entity_description(record, metadata)
                        await self.graphiti.client.add_episode(
                            name=f"entity_BalanceSheet_{saved.id}",
                            episode_body=description,
                            source=EpisodeType.text,
                            source_description=metadata.get('source', 'structured_data'),
                            reference_time=datetime.now(timezone.utc)
                        )
                    except Exception as e:
                        logger.warning(f"Graphiti episode creation failed: {e}")
        
        return {
            'entities_created': len(entities_created),
            'relationships_created': len(entities_created) * 2,  # commodity + geography per entity
            'entity_ids': entities_created
        }
    
    def _create_entity_description(self, entity_props: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create a text description of an entity for semantic search."""
        commodity = metadata.get('commodity', 'commodity')
        indicator = metadata.get('type', 'data')
        country = metadata.get('country', '')
        region = metadata.get('region', '')
        
        location = region if region else country
        
        if 'value' in entity_props and 'year' in entity_props:
            time_str = f"{entity_props['year']}"
            value_str = f"{entity_props['value']}"
            unit = metadata.get('unit', '')
            
            description = f"{commodity} {indicator.lower()} in {location} for {time_str} was {value_str} {unit}."
        else:
            description = f"{commodity} {indicator.lower()} data for {location}."
        
        if metadata.get('source'):
            description += f" Source: {metadata['source']}."
        
        return description
    
    # ========== Graph Analytics Interface ==========
    
    def analyze_graph(
        self,
        algorithm: str,
        filters: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute graph algorithms for analysis.
        
        Same API as TijaraKnowledgeGraph.analyze_graph()
        """
        logger.info(f"Running graph algorithm: {algorithm}")
        
        if algorithm == 'pagerank':
            return self.analytics.pagerank(filters=filters, parameters=parameters)
        elif algorithm == 'centrality':
            return self.analytics.centrality(algorithm='betweenness', filters=filters, parameters=parameters)
        elif algorithm == 'community':
            return self.analytics.community_detection(algorithm='louvain', filters=filters, parameters=parameters)
        elif algorithm == 'pathfinding':
            if not parameters or 'source' not in parameters or 'target' not in parameters:
                raise ValueError("Pathfinding requires 'source' and 'target' in parameters")
            return self.analytics.shortest_path(
                source=parameters['source'],
                target=parameters['target'],
                filters=filters,
                parameters=parameters
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
    
    # ========== Helper Methods for Backward Compatibility ==========
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        Execute raw Cypher query with security filtering applied.
        
        The query will be automatically filtered based on the user's permissions.
        Superusers bypass all filtering.
        
        Note: Prefer using repositories where possible.
        """
        params = parameters or {}
        rewritten_query = query
        
        # Apply security filtering if not superuser
        if self.security_context and not self.security_context.is_superuser:
            from ..security.query_rewriter_enhanced import EnhancedQueryRewriter
            rewriter = EnhancedQueryRewriter(self.security_context)
            rewritten_query, params = rewriter.rewrite(query, params)
        
        result = self.graph.query(rewritten_query, params)
        results = []
        
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
    
    def is_connected(self) -> bool:
        """Check if connected to FalkorDB."""
        try:
            self.graph.query("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"FalkorDB connection check failed: {e}")
            return False
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get graph statistics using raw queries."""
        stats = {}
        
        # Node counts by type
        node_query = "MATCH (n) RETURN labels(n) as type, count(n) as count"
        node_counts = self.execute_query(node_query)
        stats['nodes'] = {}
        for r in node_counts:
            if r['type'] and len(r['type']) > 0:
                label = r['type'][0] if isinstance(r['type'], list) else str(r['type'])
                stats['nodes'][label] = r['count']
        
        # Relationship counts
        rel_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count"
        rel_counts = self.execute_query(rel_query)
        stats['relationships'] = {r['type']: r['count'] for r in rel_counts}
        
        return stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        stats = self.get_graph_statistics()
        stats['ontology'] = self.ontology.get_statistics()
        return stats
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all components."""
        return {
            'falkordb': self.is_connected(),
            'graphiti': self.graphiti.is_ready(),
            'overall': self.is_connected() and self.graphiti.is_ready()
        }
    
    # ========== Exploration Interface ==========
    
    def explore_schema(self) -> Dict[str, Any]:
        """Get ontology schema for exploration."""
        return self.ontology.get_schema()
    
    def search_entities(
        self,
        search_term: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for entities by name using repositories.
        """
        results = []
        
        if not entity_types or 'Geography' in entity_types:
            geographies = self.geography_repo.search_by_level_and_name(0, search_term)
            results.extend([{'type': 'Geography', 'entity': g} for g in geographies[:limit]])
        
        if not entity_types or 'Commodity' in entity_types:
            commodities = self.commodity_repo.search_by_name(search_term, limit)
            results.extend([{'type': 'Commodity', 'entity': c} for c in commodities])
        
        return results[:limit]
