"""
Spatial Operations - Geographic and spatial analysis for the knowledge graph
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from shapely.geometry import Point, Polygon, shape
from shapely import ops

logger = logging.getLogger(__name__)


class SpatialOperations:
    """
    Provides spatial and geographic operations for the knowledge graph.
    Handles geometric intersections, containment, and proximity analysis.
    """
    
    def __init__(self, falkordb_client, config: Optional[Dict[str, Any]] = None):
        """
        Initialize spatial operations.
        
        Args:
            falkordb_client: FalkorDB client instance
            config: Optional configuration for spatial operations
        """
        self.db = falkordb_client
        self.config = config or {}
        self.default_crs = self.config.get('crs', 'EPSG:4326')  # WGS84
    
    def find_intersecting_geographies(
        self,
        geometry: Any,
        max_results: int = 100
    ) -> List[str]:
        """
        Find geography nodes that intersect with a given geometry.
        Returns list of geography entity IDs.
        
        Args:
            geometry: Shapely geometry object or GeoJSON dict
            max_results: Maximum number of results
            
        Returns:
            List of geography entity IDs (as strings)
        """
        logger.info("Finding intersecting geographies")
        
        try:
            # Convert to Shapely geometry if needed
            from shapely.geometry import shape as shapely_shape
            if isinstance(geometry, dict):
                query_geom = shapely_shape(geometry)
            else:
                query_geom = geometry
            
            # Since we don't have actual geometry data in the graph yet,
            # we'll use a simple name-based matching for common regions
            # This is a placeholder implementation
            
            # Get all geography nodes
            query = 'MATCH (g:Geography) RETURN id(g) as id, g.name as name LIMIT 100'
            results = self.db.execute_query(query)
            
            # For now, return all geographies as potentially affected
            # In a real implementation, this would do actual geometric intersection
            geography_ids = [str(r['id']) for r in results[:max_results]]
            
            logger.info(f"Found {len(geography_ids)} potentially affected geographies")
            return geography_ids
            
        except Exception as e:
            logger.error(f"Error finding intersecting geographies: {e}")
            return []
    
    def find_intersecting_entities(
        self,
        geometry: Dict[str, Any],
        entity_types: Optional[List[str]] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find entities that intersect with a given geometry.
        
        Args:
            geometry: GeoJSON geometry dict
            entity_types: Optional list of entity types to filter
            max_results: Maximum number of results
            
        Returns:
            List of entities with their geometries
        """
        logger.info(f"Finding entities intersecting with geometry")
        
        try:
            # Convert GeoJSON to Shapely geometry
            query_geom = shape(geometry)
            
            # Build query to fetch entities with geometries
            query = self._build_spatial_query(entity_types, "has_geometry")
            
            # Execute query
            results = self.db.execute_query(query) if hasattr(self.db, 'execute_query') else []
            
            intersecting = []
            for record in results:
                if 'geometry' in record:
                    entity_geom = shape(record['geometry'])
                    if query_geom.intersects(entity_geom):
                        intersecting.append({
                            'entity_id': record.get('id'),
                            'entity_type': record.get('type'),
                            'geometry': record.get('geometry'),
                            'properties': record.get('properties', {})
                        })
                
                if len(intersecting) >= max_results:
                    break
            
            return intersecting
        
        except Exception as e:
            logger.error(f"Error finding intersecting entities: {e}")
            return []
    
    def find_entities_within(
        self,
        geometry: Dict[str, Any],
        entity_types: Optional[List[str]] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find entities completely within a given geometry.
        
        Args:
            geometry: GeoJSON geometry dict
            entity_types: Optional list of entity types to filter
            max_results: Maximum number of results
            
        Returns:
            List of entities within the geometry
        """
        logger.info(f"Finding entities within geometry")
        
        try:
            query_geom = shape(geometry)
            query = self._build_spatial_query(entity_types, "has_geometry")
            results = self.db.execute_query(query) if hasattr(self.db, 'execute_query') else []
            
            within = []
            for record in results:
                if 'geometry' in record:
                    entity_geom = shape(record['geometry'])
                    if query_geom.contains(entity_geom):
                        within.append({
                            'entity_id': record.get('id'),
                            'entity_type': record.get('type'),
                            'geometry': record.get('geometry'),
                            'properties': record.get('properties', {})
                        })
                
                if len(within) >= max_results:
                    break
            
            return within
        
        except Exception as e:
            logger.error(f"Error finding entities within: {e}")
            return []
    
    def find_nearby_entities(
        self,
        point: Tuple[float, float],
        radius_km: float,
        entity_types: Optional[List[str]] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find entities within a radius of a point.
        
        Args:
            point: (longitude, latitude) tuple
            radius_km: Search radius in kilometers
            entity_types: Optional list of entity types to filter
            max_results: Maximum number of results
            
        Returns:
            List of nearby entities with distances
        """
        logger.info(f"Finding entities near {point} within {radius_km} km")
        
        try:
            # Create point geometry
            query_point = Point(point)
            
            # Create buffer (approximate, for WGS84)
            # 1 degree ≈ 111 km at equator
            radius_degrees = radius_km / 111.0
            buffer_geom = query_point.buffer(radius_degrees)
            
            # Find intersecting entities
            entities = self.find_intersecting_entities(
                geometry=buffer_geom.__geo_interface__,
                entity_types=entity_types,
                max_results=max_results
            )
            
            # Calculate actual distances
            for entity in entities:
                if 'geometry' in entity:
                    entity_geom = shape(entity['geometry'])
                    # Get centroid for distance calculation
                    entity_point = entity_geom.centroid
                    # Approximate distance in km
                    distance_degrees = query_point.distance(entity_point)
                    distance_km = distance_degrees * 111.0
                    entity['distance_km'] = round(distance_km, 2)
            
            # Sort by distance
            entities.sort(key=lambda x: x.get('distance_km', float('inf')))
            
            return entities
        
        except Exception as e:
            logger.error(f"Error finding nearby entities: {e}")
            return []
    
    def calculate_impact_area(
        self,
        event_geometry: Dict[str, Any],
        event_type: str,
        max_hops: int = 5,
        impact_threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        Calculate impact area for a spatial event.
        
        Args:
            event_geometry: GeoJSON geometry of the event
            event_type: Type of event (e.g., 'drought', 'flood')
            max_hops: Maximum graph hops for impact propagation
            impact_threshold: Minimum impact score to include
            
        Returns:
            Dictionary with impacted entities and relationships
        """
        logger.info(f"Calculating impact area for {event_type} event")
        
        try:
            # Find directly affected entities
            directly_affected = self.find_intersecting_entities(event_geometry)
            
            # Initialize impact scores
            impact_scores = {}
            for entity in directly_affected:
                entity_id = entity.get('entity_id')
                impact_scores[entity_id] = 1.0  # Direct impact
            
            # Propagate impact through graph relationships
            propagated_impacts = self._propagate_impact(
                directly_affected,
                max_hops,
                impact_threshold
            )
            
            impact_scores.update(propagated_impacts)
            
            # Filter by threshold
            filtered_impacts = {
                entity_id: score
                for entity_id, score in impact_scores.items()
                if score >= impact_threshold
            }
            
            return {
                'event_type': event_type,
                'directly_affected_count': len(directly_affected),
                'total_impacted_count': len(filtered_impacts),
                'impact_scores': filtered_impacts,
                'directly_affected': directly_affected
            }
        
        except Exception as e:
            logger.error(f"Error calculating impact area: {e}")
            return {
                'error': str(e),
                'directly_affected_count': 0,
                'total_impacted_count': 0,
                'impact_scores': {},
                'directly_affected': []
            }
    
    def _propagate_impact(
        self,
        initial_entities: List[Dict[str, Any]],
        max_hops: int,
        threshold: float
    ) -> Dict[str, float]:
        """
        Propagate impact through graph relationships.
        
        Args:
            initial_entities: Initially affected entities
            max_hops: Maximum hops for propagation
            threshold: Minimum impact score
            
        Returns:
            Dictionary mapping entity IDs to impact scores
        """
        impact_scores = {}
        decay_factor = 0.5  # Impact decays by 50% per hop
        
        current_entities = [e.get('entity_id') for e in initial_entities if e.get('entity_id')]
        
        for hop in range(max_hops):
            if not current_entities:
                break
            
            # Calculate impact for current hop
            current_impact = (decay_factor ** hop)
            
            if current_impact < threshold:
                break
            
            # Find connected entities
            next_entities = []
            for entity_id in current_entities:
                connected = self._get_connected_entities(entity_id)
                for conn_id in connected:
                    if conn_id not in impact_scores or impact_scores[conn_id] < current_impact:
                        impact_scores[conn_id] = current_impact
                        next_entities.append(conn_id)
            
            current_entities = next_entities
        
        return impact_scores
    
    def _get_connected_entities(self, entity_id: str) -> List[str]:
        """Get entities connected to the given entity"""
        query = f"""
        MATCH (n)-[r]-(m)
        WHERE id(n) = '{entity_id}'
        RETURN id(m) as connected_id
        LIMIT 50
        """
        
        try:
            results = self.db.execute_query(query) if hasattr(self.db, 'execute_query') else []
            return [r.get('connected_id') for r in results if r.get('connected_id')]
        except Exception as e:
            logger.error(f"Error getting connected entities: {e}")
            return []
    
    def _build_spatial_query(
        self,
        entity_types: Optional[List[str]],
        relationship_type: str
    ) -> str:
        """Build a Cypher query for spatial operations"""
        type_filter = ""
        if entity_types:
            types_str = "|".join(entity_types)
            type_filter = f":{types_str}"
        
        query = f"""
        MATCH (n{type_filter})-[:{relationship_type}]->(g)
        WHERE exists(g.geometry)
        RETURN id(n) as id, labels(n)[0] as type, g.geometry as geometry, properties(n) as properties
        LIMIT 1000
        """
        
        return query
    
    def get_entity_geometry(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get the geometry of a specific entity"""
        query = f"""
        MATCH (n)-[:has_geometry]->(g)
        WHERE id(n) = '{entity_id}'
        RETURN g.geometry as geometry
        """
        
        try:
            results = self.db.execute_query(query) if hasattr(self.db, 'execute_query') else []
            if results and 'geometry' in results[0]:
                return results[0]['geometry']
        except Exception as e:
            logger.error(f"Error getting entity geometry: {e}")
        
        return None
