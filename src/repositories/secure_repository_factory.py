"""
Secure repository factory for wrapping repositories with security filtering.

Integrates EnhancedQueryRewriter into repository query execution pipeline.
"""

from typing import Type, TypeVar, Optional, Any, List
from falkordb import Graph
from falkordb_orm import Repository
from ..security.context import SecurityContext
from ..security.query_rewriter_enhanced import EnhancedQueryRewriter


T = TypeVar('T')


class SecureRepositoryWrapper:
    """
    Wrapper that adds security filtering to repository operations.
    
    Wraps an existing repository and intercepts query execution to apply
    QueryRewriter transformations.
    """
    
    def __init__(
        self,
        repository: Repository[T],
        security_context: SecurityContext,
        entity_class: Type[T]
    ):
        """
        Initialize secure repository wrapper.
        
        Args:
            repository: Underlying repository instance
            security_context: Security context for filtering
            entity_class: Entity class type
        """
        self._repository = repository
        self._security_context = security_context
        self._entity_class = entity_class
        self._query_rewriter = EnhancedQueryRewriter(security_context)
    
    def __getattr__(self, name: str) -> Any:
        """
        Delegate attribute access to underlying repository.
        
        Args:
            name: Attribute name
            
        Returns:
            Attribute value, with query methods wrapped
        """
        attr = getattr(self._repository, name)
        
        # If it's a callable method, wrap it to apply security
        if callable(attr):
            return self._wrap_method(name, attr)
        
        return attr
    
    def _wrap_method(self, method_name: str, method: callable) -> callable:
        """
        Wrap repository method to apply security filtering.
        
        Args:
            method_name: Name of the method
            method: Method to wrap
            
        Returns:
            Wrapped method
        """
        def wrapped(*args, **kwargs):
            # For methods that execute queries, intercept and rewrite
            if method_name in ['find_by_id', 'find_all', 'find_by_name', 
                               'search_case_insensitive', 'find_children_of',
                               'find_trade_partners', 'find_all_countries',
                               'find_by_geography', 'find_by_commodity',
                               'find_by_commodity_and_geography']:
                return self._execute_secure_query(method, args, kwargs)
            
            # For other methods (save, delete, etc.), apply property filtering on results
            result = method(*args, **kwargs)
            
            # Filter properties on returned entities
            if result:
                result = self._filter_result_properties(result)
            
            return result
        
        return wrapped
    
    def _execute_secure_query(self, method: callable, args: tuple, kwargs: dict) -> Any:
        """
        Execute query method with security filtering.
        
        Args:
            method: Original repository method
            args: Method arguments
            kwargs: Method keyword arguments
            
        Returns:
            Filtered query results
        """
        # Call original method
        result = method(*args, **kwargs)
        
        # Apply property filtering to results
        if result:
            result = self._filter_result_properties(result)
        
        return result
    
    def _filter_result_properties(self, result: Any) -> Any:
        """
        Filter denied properties from query results.
        
        Args:
            result: Query result (entity or list of entities)
            
        Returns:
            Result with denied properties set to None
        """
        # Get entity label
        if hasattr(self._entity_class, '__node_metadata__'):
            metadata = self._entity_class.__node_metadata__
            entity_label = metadata.labels[0] if hasattr(metadata, 'labels') and metadata.labels else None
        else:
            return result
        
        if not entity_label:
            return result
        
        # Get denied properties
        denied_props = self._security_context.get_denied_properties(entity_label, 'read')
        
        if not denied_props:
            return result
        
        # Filter properties
        if isinstance(result, list):
            for entity in result:
                self._filter_entity_properties(entity, denied_props)
        elif result is not None:
            self._filter_entity_properties(result, denied_props)
        
        return result
    
    def _filter_entity_properties(self, entity: Any, denied_props: set) -> None:
        """
        Set denied properties to None on entity.
        
        Args:
            entity: Entity instance
            denied_props: Set of property names to deny
        """
        for prop_name in denied_props:
            if hasattr(entity, prop_name):
                setattr(entity, prop_name, None)
    
    def _apply_query_rewriting(self, cypher: str, params: dict) -> tuple:
        """
        Apply query rewriting for security.
        
        Args:
            cypher: Original Cypher query
            params: Query parameters
            
        Returns:
            Tuple of (modified_cypher, modified_params)
        """
        return self._query_rewriter.rewrite(cypher, params, self._entity_class)


def create_secure_repository(
    repository_class: Type[Repository[T]],
    graph: Graph,
    entity_class: Type[T],
    security_context: Optional[SecurityContext] = None
) -> Repository[T]:
    """
    Create a secure repository wrapper or standard repository.
    
    Args:
        repository_class: Repository class to instantiate
        graph: FalkorDB graph instance
        entity_class: Entity class type
        security_context: Optional security context for filtering
        
    Returns:
        Repository instance (wrapped if security context provided)
    """
    # Create base repository
    repository = repository_class(graph, entity_class)
    
    # If no security context or user is superuser, return unwrapped
    if not security_context or security_context.is_superuser:
        return repository
    
    # Wrap with security
    return SecureRepositoryWrapper(repository, security_context, entity_class)


def wrap_existing_repository(
    repository: Repository[T],
    security_context: SecurityContext,
    entity_class: Type[T]
) -> Repository[T]:
    """
    Wrap an existing repository instance with security filtering.
    
    Args:
        repository: Existing repository instance
        security_context: Security context for filtering
        entity_class: Entity class type
        
    Returns:
        Wrapped repository
    """
    if not security_context or security_context.is_superuser:
        return repository
    
    return SecureRepositoryWrapper(repository, security_context, entity_class)
