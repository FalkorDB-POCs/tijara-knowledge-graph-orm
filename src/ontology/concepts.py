"""
Ontology Concepts - Abstract classes for domain entities
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ConceptType(Enum):
    """Types of concepts in the ontology"""
    COMMODITY = "Commodity"
    GEOGRAPHY = "Geography"
    INDICATOR = "Indicator"
    TICKER = "Ticker"


@dataclass
class Concept:
    """
    Base class for ontology concepts.
    Concepts are abstract categories in the domain.
    """
    name: str
    concept_type: ConceptType
    description: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert concept to dictionary representation"""
        return {
            'name': self.name,
            'type': self.concept_type.value,
            'description': self.description,
            'properties': self.properties,
            'parent': self.parent,
            'children': self.children
        }


class Commodity(Concept):
    """
    Commodity concept - represents agricultural commodities
    Examples: Wheat, Corn, Soybean, Rice
    """
    def __init__(self, name: str, description: Optional[str] = None, 
                 category: Optional[str] = None, **kwargs):
        super().__init__(
            name=name,
            concept_type=ConceptType.COMMODITY,
            description=description,
            **kwargs
        )
        self.category = category


class Geography(Concept):
    """
    Geography concept - represents locations and regions
    Examples: Countries, Regions, Trade Zones
    """
    def __init__(self, name: str, description: Optional[str] = None,
                 level: Optional[str] = None, iso_code: Optional[str] = None,
                 geometry: Optional[Dict] = None, **kwargs):
        super().__init__(
            name=name,
            concept_type=ConceptType.GEOGRAPHY,
            description=description,
            **kwargs
        )
        self.level = level
        self.iso_code = iso_code
        self.geometry = geometry


class Indicator(Concept):
    """
    Indicator concept - represents measurable metrics
    Examples: Production, Demand, Exports, Temperature, Population
    """
    def __init__(self, name: str, description: Optional[str] = None,
                 unit: Optional[str] = None, category: Optional[str] = None, **kwargs):
        super().__init__(
            name=name,
            concept_type=ConceptType.INDICATOR,
            description=description,
            **kwargs
        )
        self.unit = unit
        self.category = category


class Ticker(Concept):
    """
    Ticker concept - represents price series and financial instruments
    Examples: CME Futures, Premiums, Spot Prices
    """
    def __init__(self, name: str, description: Optional[str] = None,
                 exchange: Optional[str] = None, instrument_type: Optional[str] = None, **kwargs):
        super().__init__(
            name=name,
            concept_type=ConceptType.TICKER,
            description=description,
            **kwargs
        )
        self.exchange = exchange
        self.instrument_type = instrument_type


# Predefined concepts based on the domain
PREDEFINED_COMMODITIES = [
    Commodity(name="Wheat", description="Wheat grain", category="Grains"),
    Commodity(name="Corn", description="Corn/Maize grain", category="Grains"),
    Commodity(name="Soybean", description="Soybean oilseed", category="Oilseeds"),
    Commodity(name="Soybeans", description="Soybeans oilseed", category="Oilseeds"),
    Commodity(name="Rice", description="Rice grain", category="Grains"),
    Commodity(name="Barley", description="Barley grain", category="Grains"),
]

PREDEFINED_INDICATORS = [
    Indicator(name="Production", category="Supply", unit="MT"),
    Indicator(name="Demand", category="Demand", unit="MT"),
    Indicator(name="Exports", category="Trade", unit="MT"),
    Indicator(name="Imports", category="Trade", unit="MT"),
    Indicator(name="Stocks", category="Supply", unit="MT"),
    Indicator(name="Yield", category="Supply", unit="MT/ha"),
    Indicator(name="Price", category="Market", unit="USD/MT"),
    Indicator(name="Temperature", category="Climate", unit="celsius"),
    Indicator(name="Precipitation", category="Climate", unit="mm"),
]
