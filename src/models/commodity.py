"""
Commodity entity model representing commodity hierarchy.
"""

from typing import Optional, List
from falkordb_orm import node, property, relationship, generated_id


@node("Commodity")
class Commodity:
    """
    Represents a commodity in the hierarchy.
    
    Hierarchy levels:
        - Level 0: Categories (e.g., Grains, Oilseeds)
        - Level 1: Commodity types (e.g., Wheat, Corn)
        - Level 2: Specific varieties (e.g., Hard Red Wheat, Yellow Corn)
        - Level 3: Sub-varieties (e.g., Hard Red Spring Wheat)
    
    Relationships:
        - SUBCLASS_OF: Commodity hierarchy (child -> parent)
    """
    
    id: Optional[int] = generated_id()
    name: str
    level: int = 0  # 0=category, 1=type, 2=variety, 3=sub-variety
    category: Optional[str] = None  # Top-level category name
    description: Optional[str] = None
    
    # Commodity-specific attributes
    hs_code: Optional[str] = None  # Harmonized System code
    unit: Optional[str] = None  # Default unit (e.g., "metric tons")
    
    # Relationships
    parent: Optional["Commodity"] = relationship(
        type="SUBCLASS_OF",
        direction="OUTGOING",
        lazy=True
    )
    
    children: List["Commodity"] = relationship(
        type="SUBCLASS_OF",
        direction="INCOMING",
        lazy=True
    )
    
    def __repr__(self) -> str:
        return f"Commodity(id={self.id}, name='{self.name}', level={self.level})"
    
    def __str__(self) -> str:
        return self.name
