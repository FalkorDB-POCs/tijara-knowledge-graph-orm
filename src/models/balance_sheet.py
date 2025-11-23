"""
BalanceSheet entity model representing supply/demand data.
"""

from typing import Optional, List
from falkordb_orm import node, property, relationship, generated_id


@node("BalanceSheet")
class BalanceSheet:
    """
    Represents supply/demand balance sheet data for a commodity and geography.
    
    Relationships:
        - FOR_COMMODITY: The commodity this balance sheet tracks
        - FOR_GEOGRAPHY: The geographic area this balance sheet covers
        - HAS_COMPONENT: Components of the balance sheet
    """
    
    id: Optional[int] = generated_id()
    product_name: str
    season: Optional[str] = None  # e.g., "2023/24"
    unit: Optional[str] = None  # e.g., "thousand metric tons"
    
    # Relationships
    commodity: Optional["Commodity"] = relationship(
        type="FOR_COMMODITY",
        direction="OUTGOING",
        lazy=True
    )
    
    geography: Optional["Geography"] = relationship(
        type="FOR_GEOGRAPHY",
        direction="OUTGOING",
        lazy=True
    )
    
    components: List["Component"] = relationship(
        type="HAS_COMPONENT",
        direction="OUTGOING",
        lazy=True
    )
    
    def __repr__(self) -> str:
        return f"BalanceSheet(id={self.id}, product='{self.product_name}', season='{self.season}')"
    
    def __str__(self) -> str:
        return f"{self.product_name} Balance Sheet ({self.season})"
