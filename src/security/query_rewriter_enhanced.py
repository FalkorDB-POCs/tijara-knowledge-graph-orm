"""
Enhanced QueryRewriter for data-level security filtering.

Extends falkordb-orm's QueryRewriter with concrete implementations
for row-level, property-level, and relationship-level filtering.
"""

from typing import Dict, List, Tuple, Optional, Type, Any, Set
import re
from falkordb_orm.security import QueryRewriter
from .context import SecurityContext


class EnhancedQueryRewriter(QueryRewriter):
    """
    Enhanced query rewriter with full implementation of security filtering.
    
    Supports:
    - Row-level filtering (WHERE clause injection)
    - Property-level filtering (RETURN clause modification)
    - Relationship-level filtering (edge type restrictions)
    - DENY precedence over GRANT
    """
    
    def __init__(self, security_context: SecurityContext):
        """
        Initialize enhanced query rewriter.
        
        Args:
            security_context: SecurityContext with user permissions
        """
        super().__init__(security_context)
        self.context = security_context
    
    def rewrite(self, cypher: str, params: Dict, entity_class: Optional[Type] = None) -> Tuple[str, Dict]:
        """
        Rewrite query to enforce RBAC and data-level security.
        
        Args:
            cypher: Original Cypher query
            params: Query parameters
            entity_class: Primary entity class being queried
            
        Returns:
            Tuple of (modified_cypher, modified_params)
        """
        # Skip rewriting for superusers
        if self.context.is_superuser:
            return cypher, params
        
        # Parse query to identify components
        query_parts = self._parse_query(cypher)
        
        # Get entity classes from query
        entity_classes = self._parse_entity_classes(cypher, entity_class)
        
        # Apply security filters
        modified_cypher = cypher
        
        # Step 1: Add row-level filters (WHERE clause injection)
        if query_parts["match_clause"] and entity_classes:
            modified_cypher = self._add_row_filters(
                modified_cypher, query_parts, entity_classes
            )
        
        # Step 2: Filter properties in RETURN clause
        if query_parts["return_clause"] and entity_classes:
            modified_cypher = self._filter_properties(
                modified_cypher, query_parts, entity_classes
            )
        
        # Step 3: Add edge filters (relationship restrictions)
        if entity_classes:
            modified_cypher = self._add_edge_filters(
                modified_cypher, query_parts
            )
        
        # Inject user context into parameters
        params = params.copy()
        params["__security_user_id__"] = self.context.username
        params["__security_roles__"] = self.context.get_roles()
        
        return modified_cypher, params
    
    def _parse_entity_classes(
        self, 
        cypher: str, 
        primary_entity: Optional[Type] = None
    ) -> Dict[str, Type]:
        """
        Parse entity classes from Cypher query.
        
        Args:
            cypher: Cypher query
            primary_entity: Primary entity class if known
            
        Returns:
            Dictionary mapping variable names to entity classes
        """
        entity_map = {}
        
        # Extract (var:Label) or (var:Label {...}) patterns
        # Matches: (g:Geography) or (g:Geography {level: 0})
        pattern = r'\((\w+):(\w+)(?:\s*\{[^}]*\})?\)'
        matches = re.findall(pattern, cypher)
        
        for var_name, label in matches:
            entity_map[var_name] = label
        
        # If primary entity provided, try to match it
        if primary_entity and hasattr(primary_entity, '__node_metadata__'):
            metadata = primary_entity.__node_metadata__
            if hasattr(metadata, 'labels'):
                primary_label = metadata.labels[0] if metadata.labels else None
                # Find variable with matching label
                for var_name, label in entity_map.items():
                    if label == primary_label:
                        entity_map[var_name] = primary_entity
                        break
        
        return entity_map
    
    def _add_row_filters(
        self,
        cypher: str,
        parts: Dict,
        entity_classes: Dict[str, Any]
    ) -> str:
        """
        Add row-level security filters to WHERE clause.
        
        Args:
            cypher: Original Cypher
            parts: Parsed query parts
            entity_classes: Mapping of variables to entity classes
            
        Returns:
            Modified Cypher with injected WHERE conditions
        """
        filters_by_var = {}
        
        # Helper to prefix unqualified property names with the variable (avoid functions/keywords)
        def _prefix_unqualified(cond: str, var: str) -> str:
            reserved = {'NOT','AND','OR','IN','IS','NULL','TRUE','FALSE'}
            # Only prefix identifiers that are not already qualified (no preceding '.') and not functions (no following '(')
            # Also avoid string literals in quotes
            def repl(m):
                word = m.group(1)
                if word.upper() in reserved:
                    return word
                return f"{var}.{word}"
            # First, protect string literals by temporarily replacing them
            strings = []
            def save_string(m):
                strings.append(m.group(0))
                return f"§§STRING{len(strings)-1}§§"  # Use special chars unlikely in Cypher
            # Match single and double quoted strings
            protected = re.sub(r"'[^']*'|\"[^\"]*\"", save_string, cond)
            # (?<!\.) ensures not already qualified, (?!\s*\() avoids function calls
            # Exclude our placeholder pattern from matching
            prefixed = re.sub(r"(?<!\.)(?<!§)\b([A-Za-z_]\w*)\b(?!\s*\()(?!§)", repl, protected)
            # Restore string literals
            for i, s in enumerate(strings):
                prefixed = prefixed.replace(f"§§STRING{i}§§", s)
            return prefixed
        
        # Collect filters for each entity variable
        for var_name, entity_info in entity_classes.items():
            # Get entity label
            if isinstance(entity_info, str):
                entity_label = entity_info
            elif isinstance(entity_info, type) and hasattr(entity_info, '__node_metadata__'):
                metadata = entity_info.__node_metadata__
                entity_label = metadata.labels[0] if hasattr(metadata, 'labels') and metadata.labels else None
            else:
                continue
            
            if not entity_label:
                continue
            
            # Get row filters from security context
            row_filters = self.context.get_row_filters(entity_label, 'read')
            
            if row_filters:
                # Add variable prefix to filters
                prefixed_filters = []
                for filter_cond in row_filters:
                    # Always ensure properties are qualified with the current variable
                    prefixed = _prefix_unqualified(filter_cond, var_name)
                    prefixed_filters.append(prefixed)
                
                filters_by_var[var_name] = prefixed_filters
        
        if not filters_by_var:
            return cypher
        
        # Build combined WHERE clause
        all_filters = []
        for var_name, filters in filters_by_var.items():
            all_filters.extend(filters)
        
        if not all_filters:
            return cypher
        
        combined_filter = ' AND '.join([f'({f})' for f in all_filters])
        
        # Inject into query
        if parts["where_clause"]:
            # Existing WHERE clause - append with AND
            where_pattern = r'(WHERE\s+)(.*?)(\s+(?:RETURN|ORDER|LIMIT|WITH|$))'
            def replacer(match):
                return f'{match.group(1)}{match.group(2)} AND {combined_filter}{match.group(3)}'
            cypher = re.sub(where_pattern, replacer, cypher, flags=re.IGNORECASE | re.DOTALL)
        else:
            # No WHERE clause - add one
            # Insert WHERE before RETURN, ORDER BY, LIMIT, or WITH
            insert_pattern = r'(\s+)(RETURN|ORDER|LIMIT|WITH)'
            cypher = re.sub(
                insert_pattern,
                f' WHERE {combined_filter}\\g<1>\\g<2>',
                cypher,
                count=1,
                flags=re.IGNORECASE
            )
        
        return cypher
    
    def _filter_properties(
        self,
        cypher: str,
        parts: Dict,
        entity_classes: Dict[str, Any]
    ) -> str:
        """
        Remove denied properties from RETURN clause.
        
        Args:
            cypher: Original Cypher
            parts: Parsed query parts
            entity_classes: Mapping of variables to entity classes
            
        Returns:
            Modified Cypher with filtered properties
        """
        denied_props_by_var = {}
        
        # Collect denied properties for each entity
        for var_name, entity_info in entity_classes.items():
            # Get entity label
            if isinstance(entity_info, str):
                entity_label = entity_info
            elif isinstance(entity_info, type) and hasattr(entity_info, '__node_metadata__'):
                metadata = entity_info.__node_metadata__
                entity_label = metadata.labels[0] if hasattr(metadata, 'labels') and metadata.labels else None
            else:
                continue
            
            if not entity_label:
                continue
            
            # Get denied properties from security context
            denied_props = self.context.get_denied_properties(entity_label, 'read')
            
            if denied_props:
                denied_props_by_var[var_name] = denied_props
        
        if not denied_props_by_var:
            return cypher
        
        # Parse RETURN clause and remove denied properties
        return_pattern = r'(RETURN\s+)(.*?)(\s+(?:ORDER|LIMIT|$))'
        
        def filter_return(match):
            return_clause = match.group(2)
            
            # Split by comma to get individual return items
            items = [item.strip() for item in return_clause.split(',')]
            filtered_items = []
            
            for item in items:
                # Check if this is a property access that should be denied
                should_include = True
                
                for var_name, denied_props in denied_props_by_var.items():
                    # Match patterns like: var.property or var.property AS alias
                    prop_pattern = rf'{var_name}\.(\w+)'
                    prop_match = re.search(prop_pattern, item)
                    
                    if prop_match:
                        prop_name = prop_match.group(1)
                        if prop_name in denied_props:
                            should_include = False
                            break
                
                if should_include:
                    filtered_items.append(item)
            
            # If all properties were denied, return just the entity
            if not filtered_items:
                # Return just the variables
                filtered_items = [var for var in entity_classes.keys()]
            
            new_return = ', '.join(filtered_items)
            return f'{match.group(1)}{new_return}{match.group(3)}'
        
        cypher = re.sub(return_pattern, filter_return, cypher, flags=re.IGNORECASE | re.DOTALL)
        
        return cypher
    
    def _add_edge_filters(
        self,
        cypher: str,
        parts: Dict
    ) -> str:
        """
        Add relationship-level filters.
        
        Args:
            cypher: Original Cypher
            parts: Parsed query parts
            
        Returns:
            Modified Cypher with edge filters
        """
        # Extract relationship patterns: -[r:TYPE]->
        rel_pattern = r'-\[(\w+):(\w+)\]-'
        matches = re.findall(rel_pattern, cypher)
        
        if not matches:
            return cypher
        
        # Collect edge filters
        edge_filters_by_var = {}
        
        for var_name, edge_type in matches:
            edge_filters = self.context.get_edge_filters(edge_type, 'read')
            
            if edge_filters:
                # Add variable prefix to filters
                prefixed_filters = []
                for filter_cond in edge_filters:
                    # Replace property references with relationship variable
                    if '.' not in filter_cond and not any(op in filter_cond for op in ['startNode', 'endNode']):
                        parts_list = filter_cond.split()
                        if len(parts_list) >= 3:
                            prop = parts_list[0]
                            prefixed_filters.append(filter_cond.replace(prop, f'{var_name}.{prop}', 1))
                    else:
                        prefixed_filters.append(filter_cond)
                
                edge_filters_by_var[var_name] = prefixed_filters
        
        if not edge_filters_by_var:
            return cypher
        
        # Build combined filters
        all_edge_filters = []
        for var_name, filters in edge_filters_by_var.items():
            all_edge_filters.extend(filters)
        
        if not all_edge_filters:
            return cypher
        
        combined_filter = ' AND '.join([f'({f})' for f in all_edge_filters])
        
        # Inject into WHERE clause (similar to row filters)
        if parts["where_clause"]:
            where_pattern = r'(WHERE\s+)(.*?)(\s+(?:RETURN|ORDER|LIMIT|WITH|$))'
            def replacer(match):
                return f'{match.group(1)}{match.group(2)} AND {combined_filter}{match.group(3)}'
            cypher = re.sub(where_pattern, replacer, cypher, flags=re.IGNORECASE | re.DOTALL)
        else:
            insert_pattern = r'(\s+)(RETURN|ORDER|LIMIT|WITH)'
            cypher = re.sub(
                insert_pattern,
                f' WHERE {combined_filter}\\g<1>\\g<2>',
                cypher,
                count=1,
                flags=re.IGNORECASE
            )
        
        return cypher
    
    def should_filter_query(self, entity_class) -> bool:
        """
        Determine if query needs security filtering.
        
        Args:
            entity_class: Entity class to check
            
        Returns:
            True if filtering needed, False otherwise
        """
        # Always filter if not superuser
        if not self.context.is_superuser:
            return True
        
        # Check if entity class has security metadata
        if hasattr(entity_class, "__security_metadata__"):
            metadata = entity_class.__security_metadata__
            if metadata.get("row_filter") or metadata.get("deny_read_properties"):
                return True
        
        return False
