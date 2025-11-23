"""
Indicator entity model representing weather and other indicators.
"""

from typing import Optional
from falkordb_orm import node, generated_id


@node("Indicator")
class Indicator:
    """
    Represents an indicator (weather, economic, etc.) tracked in the system.
    """
    
    id: Optional[int] = generated_id()
    name: str
    description: Optional[str] = None
    indicator_type: Optional[str] = None  # "weather", "economic", "production"
    unit: Optional[str] = None
    category: Optional[str] = None
    
    def __repr__(self) -> str:
        return f"Indicator(id={self.id}, name='{self.name}')"
    
    def __str__(self) -> str:
        return self.name
