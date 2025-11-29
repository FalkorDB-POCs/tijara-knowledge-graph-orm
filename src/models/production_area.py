"""
ProductionArea entity model representing geographic production zones.
"""

from typing import Optional, List
from falkordb_orm import node, property, relationship, generated_id


@node("ProductionArea")
class ProductionArea:
    """
    Represents a geographic production zone for commodities.
    
    Relationships:
        - PRODUCES: Commodities produced in this area
        - IN_GEOGRAPHY: Geographic location of production area
    """
    
    id: Optional[int] = generated_id()
    name: str
    description: Optional[str] = None
    
    # Geographic reference
    geometry: Optional[str] = None  # GeoJSON or WKT geometry
    
    # Relationships
    geography: Optional["Geography"] = relationship(
        relationship_type="IN_GEOGRAPHY",
        direction="OUTGOING",
        lazy=True
    )
    
    commodities: List["Commodity"] = relationship(
        relationship_type="PRODUCES",
        direction="OUTGOING",
        lazy=True
    )
    
    def __repr__(self) -> str:
        return f"ProductionArea(id={self.id}, name='{self.name}')"
    
    def __str__(self) -> str:
        return self.name
