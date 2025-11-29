"""
Tijara Knowledge Graph - Main Interface
Integrates FalkorDB for graph storage and Graphiti for GraphRAG capabilities
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import logging

from .falkordb_client import FalkorDBClient
from .graphiti_engine import GraphitiEngine
from ..ontology.schema import OntologySchema
from ..analytics.graph_algorithms import GraphAnalytics
from ..analytics.spatial_ops import SpatialOperations
from ..rag.query_engine import QueryEngine
from ..repositories import (
    CommodityRepository,
    GeographyRepository,
    BalanceSheetRepository,
    ProductionAreaRepository
)

logger = logging.getLogger(__name__)


class TijaraKnowledgeGraph:
    """
    Main interface for the Tijara Knowledge Graph system.
    
    Provides unified access to:
    - Graph storage (FalkorDB)
    - GraphRAG capabilities (Graphiti)
    - Analytics and algorithms
    - Spatial operations
    - Natural language querying
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the knowledge graph system.
        
        Args:
            config: Configuration dictionary with FalkorDB, Graphiti, and other settings
        """
        self.config = config
        
        # Initialize core components
        self.falkordb = FalkorDBClient(config['falkordb'])
        self.graphiti = GraphitiEngine(config['graphiti'])
        self.ontology = OntologySchema(config.get('ontology_path'))
        
        # Initialize analytics modules
        self.analytics = GraphAnalytics(self.falkordb)
        self.spatial = SpatialOperations(self.falkordb, config.get('spatial', {}))
        
        # Initialize RAG engine
        self.query_engine = QueryEngine(
            falkordb=self.falkordb,
            graphiti=self.graphiti,
            config=config.get('rag', {})
        )
        
        # Initialize ORM repositories
        from ..models.commodity import Commodity
        from ..models.geography import Geography
        from ..models.balance_sheet import BalanceSheet
        from ..models.production_area import ProductionArea
        
        self.commodity_repo = CommodityRepository(self.falkordb.graph, Commodity)
        self.geography_repo = GeographyRepository(self.falkordb.graph, Geography)
        self.balance_sheet_repo = BalanceSheetRepository(self.falkordb.graph, BalanceSheet)
        self.production_area_repo = ProductionAreaRepository(self.falkordb.graph, ProductionArea)
        
        logger.info("Tijara Knowledge Graph initialized successfully")
    
    # ========== Natural Language Query Interface ==========
    
    async def query_natural_language(
        self, 
        question: str, 
        context: Optional[Dict[str, Any]] = None,
        return_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Answer natural language questions using GraphRAG.
        
        Example:
            answer = await kg.query_natural_language(
                "What are the relevant information on the demand of corn in Germany?"
            )
        
        Args:
            question: Natural language question
            context: Additional context (user role, filters, etc.)
            return_sources: Whether to include source references
            
        Returns:
            Dict with answer, sources, and confidence score
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
        Ingest data with automatic ontology placement.
        
        Example:
            kg.ingest_data(
                data=production_series,
                metadata={"region": "Picardie", "country": "France", "type": "Production"}
            )
        
        Args:
            data: Data to ingest (single record or list)
            metadata: Metadata including source, geography, indicator type
            validate: Whether to validate against ontology
            
        Returns:
            Ingestion result with entity IDs and relationships created
        """
        logger.info(f"Ingesting data with metadata: {metadata}")
        
        # Validate against ontology if requested
        if validate:
            validation_result = self.ontology.validate_data(data, metadata)
            if not validation_result['valid']:
                raise ValueError(f"Data validation failed: {validation_result['errors']}")
        
        # Determine ontology placement
        placement = self.ontology.determine_placement(metadata)
        
        # Create or get concept nodes (Commodity, Geography, Indicator, Source)
        concept_ids = self._get_or_create_concepts(metadata)
        
        # Create entities in FalkorDB
        entities_created = []
        relationships_created = []
        
        data_list = data if isinstance(data, list) else [data]
        
        for record in data_list:
            # Create entity node with embedded metadata properties
            entity_props = {
                **record,
                'commodity': metadata.get('commodity'),
                'country': metadata.get('country'),
                'region': metadata.get('region'),
                'indicator_type': metadata.get('type'),
                'unit': metadata.get('unit'),
                'data_source': metadata.get('source'),
                'ingestion_timestamp': datetime.utcnow().isoformat(),
                'is_active': True
            }
            
            entity_id = self.falkordb.create_entity(
                entity_type=placement['entity_type'],
                properties=entity_props
            )
            entities_created.append(entity_id)
            
            # Create relationships to concept nodes
            try:
                if 'commodity' in concept_ids:
                    rel_id = self.falkordb.create_relationship(
                        source_id=entity_id,
                        target_id=concept_ids['commodity'],
                        relationship_type='HAS_COMMODITY'
                    )
                    relationships_created.append(rel_id)
                
                if 'geography' in concept_ids:
                    rel_id = self.falkordb.create_relationship(
                        source_id=entity_id,
                        target_id=concept_ids['geography'],
                        relationship_type='HAS_GEOGRAPHY'
                    )
                    relationships_created.append(rel_id)
                
                if 'indicator' in concept_ids:
                    rel_id = self.falkordb.create_relationship(
                        source_id=entity_id,
                        target_id=concept_ids['indicator'],
                        relationship_type='HAS_INDICATOR'
                    )
                    relationships_created.append(rel_id)
                
                if 'source' in concept_ids:
                    rel_id = self.falkordb.create_relationship(
                        source_id=entity_id,
                        target_id=concept_ids['source'],
                        relationship_type='HAS_SOURCE'
                    )
                    relationships_created.append(rel_id)
            except Exception as e:
                logger.warning(f"Failed to create some relationships: {e}")
            
            # Create text description for Graphiti episode
            text_description = self._create_entity_description(entity_props, metadata)
            
            # Add to Graphiti as an episode with embeddings
            # This creates semantic search capability for structured data
            if self.graphiti and self.graphiti.is_ready():
                try:
                    from graphiti_core.nodes import EpisodeType
                    
                    await self.graphiti.client.add_episode(
                        name=f"entity_{placement['entity_type']}_{entity_id}",
                        episode_body=text_description,
                        source=EpisodeType.text,
                        source_description=f"{metadata.get('source', 'structured_data')}",
                        reference_time=datetime.now(timezone.utc)
                    )
                    logger.info(f"Added entity {entity_id} to Graphiti with embeddings")
                except Exception as e:
                    logger.warning(f"Graphiti episode creation failed for entity {entity_id}: {e}")
        
        return {
            'entities_created': len(entities_created),
            'relationships_created': len(relationships_created),
            'entity_ids': entities_created,
            'placement': placement,
            'concept_ids': concept_ids
        }
    
    # ========== Graph Analytics Interface ==========
    
    def analyze_graph(
        self,
        algorithm: str,
        filters: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute graph algorithms for analysis.
        
        Example:
            exporters = kg.analyze_graph(
                algorithm="pagerank",
                filters={"commodity": "Corn", "indicator": "Exports"}
            )
        
        Args:
            algorithm: Algorithm name (pagerank, centrality, community, pathfinding)
            filters: Filters to apply to subgraph
            parameters: Algorithm-specific parameters
            
        Returns:
            Algorithm results (varies by algorithm)
        """
        logger.info(f"Running graph algorithm: {algorithm}")
        
        # Execute algorithm with filters
        if algorithm == 'pagerank':
            return self.analytics.pagerank(filters=filters, parameters=parameters)
        elif algorithm == 'centrality':
            return self.analytics.centrality(algorithm='betweenness', filters=filters, parameters=parameters)
        elif algorithm == 'community':
            return self.analytics.community_detection(algorithm='louvain', filters=filters, parameters=parameters)
        elif algorithm == 'pathfinding':
            # Pathfinding needs source and target from parameters
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
    
    def extract_dimensions(
        self,
        entity_type: str,
        filters: Optional[Dict[str, Any]] = None,
        dimensions: Optional[List[str]] = None,
        as_dataframe: bool = True
    ) -> Any:
        """
        Extract dimensional data from graph as table.
        
        Example:
            df = kg.extract_dimensions(
                entity_type="Production",
                filters={"commodity": "Corn", "year": 2023},
                dimensions=["geography", "value", "unit"]
            )
        
        Args:
            entity_type: Type of entity to extract
            filters: Filters to apply
            dimensions: Dimensions to extract (columns)
            as_dataframe: Return as pandas DataFrame
            
        Returns:
            Table data (DataFrame or list of dicts)
        """
        return self.analytics.extract_dimensional_data(
            entity_type=entity_type,
            filters=filters,
            dimensions=dimensions,
            as_dataframe=as_dataframe
        )
    
    # ========== Impact Analysis Interface ==========
    
    def find_impacts(
        self,
        event_geometry: Any,
        event_type: str,
        max_hops: int = 5,
        impact_threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        Find impacts of an event through the graph.
        
        Example:
            impacts = kg.find_impacts(
                event_geometry=weather_event_polygon,
                event_type="drought"
            )
        
        Args:
            event_geometry: Spatial geometry of event (Shapely geometry)
            event_type: Type of event (weather, policy, etc.)
            max_hops: Maximum relationship hops to traverse
            impact_threshold: Minimum impact score to include
            
        Returns:
            Impacted entities with scores and paths
        """
        logger.info(f"Analyzing impacts for event type: {event_type}")
        
        # Find intersecting geographies
        affected_geographies = self.spatial.find_intersecting_geographies(
            geometry=event_geometry
        )
        
        # Traverse graph to find impacts
        impacts = []
        for geo_id in affected_geographies:
            try:
                # Find data nodes connected to this geography via various relationships
                # FOR_GEOGRAPHY: BalanceSheet -> Geography
                # PRODUCES: ProductionArea -> Commodity
                # TRADES_WITH: Geography -> Geography
                query = f"""
                MATCH (g:Geography)
                WHERE id(g) = {geo_id}
                OPTIONAL MATCH (bs:BalanceSheet)-[:FOR_GEOGRAPHY]->(g)
                OPTIONAL MATCH (g)-[t:TRADES_WITH]->(dest:Geography)
                WITH g,
                     [bs IN collect(DISTINCT bs) WHERE bs IS NOT NULL | {{type: 'BalanceSheet', id: id(bs), product: bs.product_name, season: bs.season}}] as balance_sheets,
                     [t IN collect(DISTINCT t) WHERE t IS NOT NULL | {{type: 'Trade', from: g.name, to: dest.name, commodity: t.commodity}}] as trades
                WITH balance_sheets + trades as all_entities
                UNWIND all_entities as entity
                RETURN entity
                LIMIT 50
                """
                connected = self.falkordb.execute_query(query)
                
                for row in connected:
                    entity = row.get('entity', {})
                    if not entity:
                        continue
                        
                    impact_score = self._calculate_impact_score(
                        entity=entity,
                        event_type=event_type,
                        geography_id=geo_id
                    )
                    
                    if impact_score >= impact_threshold:
                        impacts.append({
                            'entity_id': entity.get('id'),
                            'entity_type': entity.get('type'),
                            'commodity': entity.get('commodity') or entity.get('product'),
                            'season': entity.get('season'),
                            'trade_info': f"{entity.get('from')} -> {entity.get('to')}" if entity.get('from') else None,
                            'impact_score': impact_score,
                            'affected_geography': geo_id,
                            'path': [geo_id]
                        })
            except Exception as e:
                logger.warning(f"Error finding impacts for geography {geo_id}: {e}")
        
        return {
            'total_impacts': len(impacts),
            'impacted_entities': impacts,
            'affected_geographies': affected_geographies,
            'event_summary': {
                'type': event_type,
                'geometry': str(event_geometry)
            }
        }
    
    def _calculate_impact_score(
        self,
        entity: Dict[str, Any],
        event_type: str,
        geography_id: str
    ) -> float:
        """Calculate impact score based on entity type and event."""
        # Simple scoring logic - can be enhanced with ML models
        base_score = 0.5
        
        # Get entity type
        entity_type = entity.get('type', entity.get('entity_type', ''))
        
        # Adjust based on LDC entity types
        if entity_type == 'BalanceSheet':
            base_score += 0.3  # Balance sheets track critical supply/demand data
        elif entity_type == 'ProductionArea':
            base_score += 0.35  # Production areas directly affected by weather
        elif entity_type == 'Trade':
            base_score += 0.2  # Trade flows can be disrupted
        
        # Adjust based on event type
        if event_type in ['drought', 'flood', 'storm'] and entity_type == 'ProductionArea':
            base_score += 0.3  # Weather events heavily impact production
        elif event_type in ['drought', 'flood'] and entity_type == 'BalanceSheet':
            base_score += 0.2  # Weather affects supply tracked in balance sheets
        elif event_type in ['policy', 'tariff', 'embargo'] and entity_type == 'Trade':
            base_score += 0.3  # Policy events affect trade flows
        
        return min(base_score, 1.0)
    
    def _get_or_create_concepts(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """Get or create concept nodes and return their IDs using ORM."""
        concept_ids = {}
        
        try:
            # Commodity concept
            if metadata.get('commodity'):
                commodity_name = metadata['commodity']
                commodity = self.commodity_repo.find_by_name(commodity_name)
                if commodity:
                    # Get ID using raw query (ORM entities don't expose internal node ID)
                    query = f'MATCH (n:Commodity {{name: "{commodity_name}"}}) RETURN id(n) as id LIMIT 1'
                    result = self.falkordb.execute_query(query)
                    if result:
                        concept_ids['commodity'] = str(result[0]['id'])
                else:
                    # Create it using raw client (not ORM-managed concept)
                    concept_ids['commodity'] = self.falkordb.create_entity(
                        'Commodity',
                        {'name': commodity_name, 'type': 'commodity'}
                    )
            
            # Geography concept (country or region)
            geo_name = metadata.get('region') or metadata.get('country')
            if geo_name:
                geography = self.geography_repo.find_by_name(geo_name)
                if geography:
                    query = f'MATCH (n:Geography {{name: "{geo_name}"}}) RETURN id(n) as id LIMIT 1'
                    result = self.falkordb.execute_query(query)
                    if result:
                        concept_ids['geography'] = str(result[0]['id'])
                else:
                    concept_ids['geography'] = self.falkordb.create_entity(
                        'Geography',
                        {'name': geo_name, 'type': 'geography', 'country': metadata.get('country')}
                    )
            
            # Indicator concept (not an ORM entity)
            if metadata.get('type'):
                indicator = metadata['type']
                query = f'MATCH (n:Indicator {{name: "{indicator}"}}) RETURN id(n) as id LIMIT 1'
                result = self.falkordb.execute_query(query)
                if result:
                    concept_ids['indicator'] = str(result[0]['id'])
                else:
                    concept_ids['indicator'] = self.falkordb.create_entity(
                        'Indicator',
                        {'name': indicator, 'type': 'indicator'}
                    )
            
            # Source concept (not an ORM entity)
            if metadata.get('source'):
                source = metadata['source']
                query = f'MATCH (n:Source {{name: "{source}"}}) RETURN id(n) as id LIMIT 1'
                result = self.falkordb.execute_query(query)
                if result:
                    concept_ids['source'] = str(result[0]['id'])
                else:
                    concept_ids['source'] = self.falkordb.create_entity(
                        'Source',
                        {'name': source, 'type': 'source'}
                    )
        
        except Exception as e:
            logger.error(f"Error creating/getting concept nodes: {e}")
        
        return concept_ids
    
    def _create_entity_description(self, entity_props: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Create a text description of an entity for semantic search."""
        parts = []
        
        # Build descriptive text
        commodity = metadata.get('commodity', 'commodity')
        indicator = metadata.get('type', 'data')
        country = metadata.get('country', '')
        region = metadata.get('region', '')
        
        location = region if region else country
        
        # Example: "Corn production in Iowa, USA for January 2023 was 384900 thousand metric tons"
        if 'value' in entity_props and 'year' in entity_props:
            month = entity_props.get('month', '')
            time_str = f"{entity_props['year']}"
            if month:
                months = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                         'July', 'August', 'September', 'October', 'November', 'December']
                time_str = f"{months[month]} {entity_props['year']}"
            
            value_str = f"{entity_props['value']}"
            unit = metadata.get('unit', '')
            
            description = f"{commodity} {indicator.lower()} in {location} for {time_str} was {value_str} {unit}."
        else:
            description = f"{commodity} {indicator.lower()} data for {location}."
        
        # Add source information
        if metadata.get('source'):
            description += f" Source: {metadata['source']}."
        
        return description
    
    # ========== Exploration Interface ==========
    
    def explore_schema(self) -> Dict[str, Any]:
        """
        Get ontology schema for exploration.
        
        Returns:
            Complete ontology schema with concepts and relationships
        """
        schema = self.ontology.get_schema()
        
        # Query actual relationship types from the graph
        try:
            query = "MATCH ()-[r]->() RETURN DISTINCT type(r) as rel_type"
            results = self.falkordb.execute_query(query)
            
            # Extract relationship types from results
            actual_relationships = [r['rel_type'] for r in results if 'rel_type' in r]
            
            # Replace static relationships with actual ones from graph
            if actual_relationships:
                schema['relationships'] = actual_relationships
                logger.info(f"Found {len(actual_relationships)} relationship types in graph")
            else:
                logger.warning("No relationships found in graph")
        except Exception as e:
            logger.error(f"Error fetching relationship types from graph: {e}")
        
        return schema
    
    def search_entities(
        self,
        search_term: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for entities by name or properties using ORM repositories.
        
        Args:
            search_term: Search query
            entity_types: Filter by entity types
            limit: Maximum results
            
        Returns:
            List of matching entities
        """
        results = []
        
        # If entity_types specified, only search those
        search_all = not entity_types or len(entity_types) == 0
        
        # Search Commodity entities
        if search_all or 'Commodity' in entity_types:
            commodities = self.commodity_repo.search_case_insensitive(search_term, limit=limit)
            for c in commodities:
                results.append({
                    'type': 'Commodity',
                    'name': c.name,
                    'level': c.level,
                    'category': c.category
                })
        
        # Search Geography entities
        if search_all or 'Geography' in entity_types:
            geographies = self.geography_repo.search_case_insensitive(search_term, limit=limit)
            for g in geographies:
                results.append({
                    'type': 'Geography',
                    'name': g.name,
                    'level': g.level,
                    'gid_code': g.gid_code
                })
        
        # Search BalanceSheet entities
        if search_all or 'BalanceSheet' in entity_types:
            balance_sheets = self.balance_sheet_repo.search_case_insensitive(search_term, limit=limit)
            for bs in balance_sheets:
                results.append({
                    'type': 'BalanceSheet',
                    'balance_sheet_id': bs.balance_sheet_id,
                    'product_name': bs.product_name,
                    'season': bs.season
                })
        
        # Search ProductionArea entities
        if search_all or 'ProductionArea' in entity_types:
            production_areas = self.production_area_repo.search_case_insensitive(search_term, limit=limit)
            for pa in production_areas:
                results.append({
                    'type': 'ProductionArea',
                    'name': pa.name
                })
        
        return results[:limit]
    
    def get_entity_history(
        self,
        entity_id: str,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """
        Get version history for an entity.
        
        Args:
            entity_id: Entity identifier
            include_relationships: Include relationship changes
            
        Returns:
            Entity history with timestamps and changes
        """
        return self.falkordb.get_entity_history(
            entity_id=entity_id,
            include_relationships=include_relationships
        )
    
    # ========== Utility Methods ==========
    
    def execute_cypher(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        Execute raw Cypher query on FalkorDB.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Query results
        """
        return self.falkordb.execute_query(query, parameters)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get graph statistics.
        
        Returns:
            Node counts, relationship counts, data sources, etc.
        """
        stats = self.falkordb.get_graph_statistics()
        stats['ontology'] = self.ontology.get_statistics()
        return stats
    
    def health_check(self) -> Dict[str, bool]:
        """
        Check health of all components.
        
        Returns:
            Health status of each component
        """
        return {
            'falkordb': self.falkordb.is_connected(),
            'graphiti': self.graphiti.is_ready(),
            'overall': self.falkordb.is_connected() and self.graphiti.is_ready()
        }
    
    async def clear_all_data(self) -> Dict[str, Any]:
        """
        Clear all data from both FalkorDB and Graphiti.
        This will delete all nodes and relationships.
        
        Returns:
            Summary of cleared data
        """
        logger.warning("Clearing all data from knowledge graph")
        
        # Clear FalkorDB data
        try:
            query = "MATCH (n) DETACH DELETE n"
            self.falkordb.execute_query(query)
            logger.info("FalkorDB data cleared")
            falkordb_cleared = True
        except Exception as e:
            logger.error(f"Error clearing FalkorDB: {e}")
            falkordb_cleared = False
        
        # Clear Graphiti data
        graphiti_cleared = False
        if self.graphiti and self.graphiti.is_ready():
            try:
                # Access the underlying driver from the Graphiti client
                driver = self.graphiti.client.driver
                
                # Delete all nodes in Graphiti (simple DETACH DELETE all)
                # This clears all Graphiti episodes and entities
                delete_query = "MATCH (n) DETACH DELETE n"
                driver.execute_query(delete_query)
                
                logger.info("Graphiti data cleared")
                graphiti_cleared = True
            except Exception as e:
                logger.error(f"Error clearing Graphiti: {e}")
        
        return {
            'status': 'success' if (falkordb_cleared and graphiti_cleared) else 'partial',
            'falkordb_cleared': falkordb_cleared,
            'graphiti_cleared': graphiti_cleared,
            'message': 'All data cleared successfully' if (falkordb_cleared and graphiti_cleared) else 'Some data may remain'
        }
