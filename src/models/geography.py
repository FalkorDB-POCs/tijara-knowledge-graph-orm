"""
Geography entity model representing countries, regions, and sub-regions.
"""

from typing import Optional, List
from falkordb_orm import node, property, relationship, generated_id


@node("Geography")
class Geography:
    """
    Represents a geographic entity (country, region, sub-region).
    
    Relationships:
        - LOCATED_IN: Geographic hierarchy (region -> country)
        - TRADES_WITH: Trade relationships between countries
    """
    
    id: Optional[int] = generated_id()
    name: str
    gid_code: Optional[str] = None  # GID_0, GID_1, GID_2 codes
    level: int = 0  # 0=country, 1=region, 2=sub-region
    iso_code: Optional[str] = None  # ISO country code
    
    # Optional geographic metadata
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geometry: Optional[str] = None  # GeoJSON or WKT geometry
    
    # Relationships
    parent: Optional["Geography"] = relationship(
        relationship_type="LOCATED_IN",
        direction="OUTGOING",
        lazy=True
    )
    
    children: List["Geography"] = relationship(
        relationship_type="LOCATED_IN",
        direction="INCOMING",
        lazy=True
    )
    
    # Trade relationships (outgoing)
    trade_partners: List["Geography"] = relationship(
        relationship_type="TRADES_WITH",
        direction="OUTGOING",
        lazy=True
    )
    
    def __repr__(self) -> str:
        return f"Geography(id={self.id}, name='{self.name}', level={self.level})"
    
    def __str__(self) -> str:
        return self.name
