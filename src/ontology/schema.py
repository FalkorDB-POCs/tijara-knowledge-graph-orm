"""
Ontology Schema - Defines and validates the knowledge graph schema
"""

from typing import Dict, List, Optional, Any, Tuple
import yaml
import os
import logging

from .concepts import Concept, Commodity, Geography, Indicator, Ticker
from .concepts import PREDEFINED_COMMODITIES, PREDEFINED_INDICATORS
from .relationships import RelationshipType, validate_relationship

logger = logging.getLogger(__name__)


class OntologySchema:
    """
    Manages the ontology schema for the knowledge graph.
    Handles concept definitions, validation, and placement logic.
    """
    
    def __init__(self, ontology_path: Optional[str] = None):
        """
        Initialize the ontology schema.
        
        Args:
            ontology_path: Path to ontology YAML file (optional)
        """
        self.concepts: Dict[str, Concept] = {}
        self.relationships: List[RelationshipType] = list(RelationshipType)
        
        # Load predefined concepts
        self._load_predefined_concepts()
        
        # Load from file if provided
        if ontology_path and os.path.exists(ontology_path):
            self._load_from_file(ontology_path)
        else:
            logger.warning(f"Ontology file not found at {ontology_path}, using defaults")
    
    def _load_predefined_concepts(self):
        """Load predefined commodities and indicators"""
        for commodity in PREDEFINED_COMMODITIES:
            self.concepts[commodity.name] = commodity
        
        for indicator in PREDEFINED_INDICATORS:
            self.concepts[indicator.name] = indicator
    
    def _load_from_file(self, file_path: str):
        """Load ontology from YAML file"""
        try:
            with open(file_path, 'r') as f:
                ontology_data = yaml.safe_load(f)
            
            # Load additional concepts from file
            if 'concepts' in ontology_data:
                for concept_data in ontology_data['concepts']:
                    concept = self._create_concept_from_dict(concept_data)
                    if concept:
                        self.concepts[concept.name] = concept
            
            logger.info(f"Loaded ontology from {file_path}")
        except Exception as e:
            logger.error(f"Error loading ontology from {file_path}: {e}")
    
    def _create_concept_from_dict(self, data: Dict) -> Optional[Concept]:
        """Create a concept object from dictionary data"""
        concept_type = data.get('type', '').lower()
        name = data.get('name')
        
        if not name:
            return None
        
        if concept_type == 'commodity':
            return Commodity(
                name=name,
                description=data.get('description'),
                category=data.get('category')
            )
        elif concept_type == 'geography':
            return Geography(
                name=name,
                description=data.get('description'),
                level=data.get('level'),
                iso_code=data.get('iso_code')
            )
        elif concept_type == 'indicator':
            return Indicator(
                name=name,
                description=data.get('description'),
                unit=data.get('unit'),
                category=data.get('category')
            )
        elif concept_type == 'ticker':
            return Ticker(
                name=name,
                description=data.get('description'),
                exchange=data.get('exchange'),
                instrument_type=data.get('instrument_type')
            )
        
        return None
    
    def validate_data(
        self,
        data: Any,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate data against the ontology schema.
        
        Args:
            data: Data to validate
            metadata: Metadata describing the data
            
        Returns:
            Validation result with 'valid' boolean and 'errors' list
        """
        errors = []
        
        # Check if commodity exists in ontology
        commodity = metadata.get('commodity')
        if commodity and commodity not in self.concepts:
            errors.append(f"Unknown commodity: {commodity}")
        
        # Check if indicator type is valid
        indicator_type = metadata.get('type')
        if indicator_type and indicator_type not in self.concepts:
            errors.append(f"Unknown indicator type: {indicator_type}")
        
        # Basic data structure validation
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    errors.append(f"Data items must be dictionaries, got {type(item)}")
                    break
        elif isinstance(data, dict):
            pass  # Single item is valid
        else:
            errors.append(f"Data must be dict or list of dicts, got {type(data)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def determine_placement(
        self,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Determine where in the ontology to place the data.
        
        Args:
            metadata: Metadata describing the data
            
        Returns:
            Placement information with entity_type and relationships
        """
        # Determine entity type based on indicator
        indicator_type = metadata.get('type', 'DataPoint')
        entity_type = indicator_type
        
        # Build relationships
        relationships = {}
        
        # Commodity relationship
        if 'commodity' in metadata:
            relationships['has_commodity'] = {
                'target_id': self._get_or_create_concept_id('commodity', metadata['commodity']),
                'properties': {}
            }
        
        # Geography relationship
        if 'country' in metadata or 'region' in metadata:
            geo_name = metadata.get('region') or metadata.get('country')
            relationships['has_geography'] = {
                'target_id': self._get_or_create_concept_id('geography', geo_name),
                'properties': {}
            }
        
        # Indicator relationship
        if 'type' in metadata:
            relationships['has_indicator'] = {
                'target_id': self._get_or_create_concept_id('indicator', metadata['type']),
                'properties': {}
            }
        
        # Source relationship
        if 'source' in metadata:
            relationships['has_source'] = {
                'target_id': self._get_or_create_concept_id('source', metadata['source']),
                'properties': {}
            }
        
        return {
            'entity_type': entity_type,
            'relationships': relationships,
            'metadata': metadata
        }
    
    def _get_or_create_concept_id(self, concept_type: str, concept_name: str) -> str:
        """
        Get or create a concept ID.
        In a real implementation, this would interact with the database.
        """
        return f"{concept_type}:{concept_name}"
    
    def get_concept(self, name: str) -> Optional[Concept]:
        """Get a concept by name"""
        return self.concepts.get(name)
    
    def add_concept(self, concept: Concept):
        """Add a new concept to the schema"""
        self.concepts[concept.name] = concept
        logger.info(f"Added concept: {concept.name}")
    
    def get_all_concepts(self) -> Dict[str, Concept]:
        """Get all concepts in the schema"""
        return self.concepts.copy()
    
    def get_concepts_by_type(self, concept_type: str) -> List[Concept]:
        """Get all concepts of a specific type"""
        return [
            c for c in self.concepts.values()
            if c.concept_type.value.lower() == concept_type.lower()
        ]
    
    def validate_relationship_type(
        self,
        rel_type: RelationshipType,
        source_type: str,
        target_type: str
    ) -> bool:
        """Validate if a relationship type is valid"""
        return validate_relationship(rel_type, source_type, target_type)
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the complete ontology schema."""
        return self.to_dict()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the ontology schema."""
        concept_types = {}
        for concept in self.concepts.values():
            ctype = concept.concept_type.value
            concept_types[ctype] = concept_types.get(ctype, 0) + 1
        
        return {
            'total_concepts': len(self.concepts),
            'concepts_by_type': concept_types,
            'relationship_types': len(self.relationships)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Export schema to dictionary format"""
        return {
            'concepts': {
                name: concept.to_dict()
                for name, concept in self.concepts.items()
            },
            'relationships': [rt.value for rt in self.relationships]
        }
