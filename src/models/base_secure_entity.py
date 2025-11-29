"""
Security metadata decorator for entity classes.

Provides @secure decorator to attach row-level and property-level
security metadata to ORM entity classes.
"""

from typing import List, Optional, Callable, Type, TypeVar, Dict, Any


T = TypeVar('T')


def secure(
    row_filter: Optional[str] = None,
    deny_read_properties: Optional[List[str]] = None,
    deny_write_properties: Optional[List[str]] = None,
    **kwargs
) -> Callable[[Type[T]], Type[T]]:
    """
    Decorator to attach security metadata to entity classes.
    
    Args:
        row_filter: Cypher WHERE condition for row-level filtering
        deny_read_properties: List of property names to deny on read
        deny_write_properties: List of property names to deny on write
        **kwargs: Additional security metadata
        
    Returns:
        Decorated class with __security_metadata__ attribute
        
    Example:
        ```python
        @secure(
            row_filter="g.country = $user_country",
            deny_read_properties=["confidential_notes", "internal_id"]
        )
        @node("Geography")
        class Geography:
            ...
        ```
    """
    def decorator(cls: Type[T]) -> Type[T]:
        # Build security metadata dictionary
        metadata: Dict[str, Any] = {}
        
        if row_filter:
            metadata['row_filter'] = row_filter
        
        if deny_read_properties:
            metadata['deny_read_properties'] = deny_read_properties
        
        if deny_write_properties:
            metadata['deny_write_properties'] = deny_write_properties
        
        # Add any additional kwargs
        metadata.update(kwargs)
        
        # Attach to class
        cls.__security_metadata__ = metadata
        
        return cls
    
    return decorator


class SecureEntityMixin:
    """
    Mixin class for entities with security metadata.
    
    Provides convenience methods for checking security constraints.
    """
    
    __security_metadata__: Dict[str, Any] = {}
    
    @classmethod
    def has_row_filter(cls) -> bool:
        """Check if entity has row-level filtering."""
        return 'row_filter' in getattr(cls, '__security_metadata__', {})
    
    @classmethod
    def has_property_filters(cls) -> bool:
        """Check if entity has property-level filtering."""
        metadata = getattr(cls, '__security_metadata__', {})
        return bool(
            metadata.get('deny_read_properties') or 
            metadata.get('deny_write_properties')
        )
    
    @classmethod
    def get_row_filter(cls) -> Optional[str]:
        """Get row filter condition."""
        return getattr(cls, '__security_metadata__', {}).get('row_filter')
    
    @classmethod
    def get_denied_read_properties(cls) -> List[str]:
        """Get list of properties denied for reading."""
        return getattr(cls, '__security_metadata__', {}).get('deny_read_properties', [])
    
    @classmethod
    def get_denied_write_properties(cls) -> List[str]:
        """Get list of properties denied for writing."""
        return getattr(cls, '__security_metadata__', {}).get('deny_write_properties', [])
    
    def filter_properties(self, denied_properties: List[str]) -> None:
        """
        Filter out denied properties by setting them to None.
        
        Args:
            denied_properties: List of property names to filter
        """
        for prop_name in denied_properties:
            if hasattr(self, prop_name):
                setattr(self, prop_name, None)


def get_entity_security_metadata(entity_class: Type) -> Dict[str, Any]:
    """
    Get security metadata from entity class.
    
    Args:
        entity_class: Entity class to inspect
        
    Returns:
        Security metadata dictionary (empty if none)
    """
    return getattr(entity_class, '__security_metadata__', {})


def has_security_metadata(entity_class: Type) -> bool:
    """
    Check if entity class has security metadata.
    
    Args:
        entity_class: Entity class to check
        
    Returns:
        True if metadata present, False otherwise
    """
    return hasattr(entity_class, '__security_metadata__') and bool(
        entity_class.__security_metadata__
    )
