"""
Ontology Relationships - Defines relationship types between entities
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class RelationshipType(Enum):
    """
    Enumeration of relationship types in the knowledge graph
    """
    # Core relationships
    HAS_COMMODITY = "has_commodity"
    HAS_GEOGRAPHY = "has_geography"
    HAS_INDICATOR = "has_indicator"
    HAS_TICKER = "has_ticker"
    
    # Hierarchical relationships
    SUBCLASS_OF = "subclass_of"
    IS_A = "is_a"
    CHILD_OF = "child_of"
    PARENT_OF = "parent_of"
    
    # Trade relationships
    HAS_EXPORTER = "has_exporter"
    HAS_IMPORTER = "has_importer"
    EXPORTS_TO = "exports_to"
    IMPORTS_FROM = "imports_from"
    TRADES_WITH = "trades_with"
    
    # Measurement relationships
    HAS_UNIT = "has_unit"
    HAS_VALUE = "has_value"
    HAS_PRICE = "has_price"
    
    # Temporal relationships
    FOLLOWS = "follows"
    PRECEDES = "precedes"
    VALID_FROM = "valid_from"
    VALID_TO = "valid_to"
    
    # Spatial relationships
    HAS_GEOMETRY = "has_geometry"
    CONTAINS = "contains"
    WITHIN = "within"
    ADJACENT_TO = "adjacent_to"
    
    # Data provenance
    HAS_SOURCE = "has_source"
    DERIVED_FROM = "derived_from"
    INFLUENCES = "influences"
    IMPACTS = "impacts"


@dataclass
class RelationshipDefinition:
    """
    Definition of a relationship type with metadata
    """
    rel_type: RelationshipType
    description: str
    source_types: List[str]  # Valid source entity types
    target_types: List[str]  # Valid target entity types
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


# Predefined relationship definitions
RELATIONSHIP_DEFINITIONS = [
    RelationshipDefinition(
        rel_type=RelationshipType.HAS_COMMODITY,
        description="Links an entity to its commodity",
        source_types=["Production", "Demand", "Exports", "Imports", "Price"],
        target_types=["Commodity"]
    ),
    RelationshipDefinition(
        rel_type=RelationshipType.HAS_GEOGRAPHY,
        description="Links an entity to its geographic location",
        source_types=["Production", "Demand", "Exports", "Imports", "Price"],
        target_types=["Geography"]
    ),
    RelationshipDefinition(
        rel_type=RelationshipType.HAS_INDICATOR,
        description="Links an entity to its indicator type",
        source_types=["Series", "DataPoint"],
        target_types=["Indicator"]
    ),
    RelationshipDefinition(
        rel_type=RelationshipType.EXPORTS_TO,
        description="Trade relationship showing export destination",
        source_types=["Geography"],
        target_types=["Geography"]
    ),
    RelationshipDefinition(
        rel_type=RelationshipType.IMPORTS_FROM,
        description="Trade relationship showing import source",
        source_types=["Geography"],
        target_types=["Geography"]
    ),
    RelationshipDefinition(
        rel_type=RelationshipType.HAS_SOURCE,
        description="Data provenance - links to original source",
        source_types=["*"],
        target_types=["Source"]
    ),
    RelationshipDefinition(
        rel_type=RelationshipType.IMPACTS,
        description="Causal relationship between entities",
        source_types=["*"],
        target_types=["*"]
    ),
]


def validate_relationship(
    rel_type: RelationshipType,
    source_type: str,
    target_type: str
) -> bool:
    """
    Validate if a relationship type is valid for given source and target types
    
    Args:
        rel_type: The relationship type
        source_type: Source entity type
        target_type: Target entity type
        
    Returns:
        True if valid, False otherwise
    """
    for rel_def in RELATIONSHIP_DEFINITIONS:
        if rel_def.rel_type == rel_type:
            source_valid = "*" in rel_def.source_types or source_type in rel_def.source_types
            target_valid = "*" in rel_def.target_types or target_type in rel_def.target_types
            return source_valid and target_valid
    
    # If not found in definitions, allow it (permissive mode)
    return True


def get_relationship_description(rel_type: RelationshipType) -> Optional[str]:
    """Get the description for a relationship type"""
    for rel_def in RELATIONSHIP_DEFINITIONS:
        if rel_def.rel_type == rel_type:
            return rel_def.description
    return None
