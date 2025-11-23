"""
Component entity model representing balance sheet components.
"""

from typing import Optional
from falkordb_orm import node, generated_id


@node("Component")
class Component:
    """
    Represents a component of a balance sheet (e.g., Production, Imports, Consumption).
    """
    
    id: Optional[int] = generated_id()
    name: str
    description: Optional[str] = None
    component_type: Optional[str] = None  # "supply", "demand", "stock"
    
    def __repr__(self) -> str:
        return f"Component(id={self.id}, name='{self.name}')"
    
    def __str__(self) -> str:
        return self.name
