"""
Comprehensive tests for EnhancedQueryRewriter
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.security.query_rewriter_enhanced import EnhancedQueryRewriter
from src.security.context import SecurityContext


class MockGraph:
    """Mock graph for testing."""
    def query(self, cypher, params=None):
        """Mock query execution."""
        result = Mock()
        result.result_set = []
        return result


class TestEnhancedQueryRewriter:
    """Test EnhancedQueryRewriter functionality."""
    
    @pytest.fixture
    def mock_context(self):
        """Create mock SecurityContext with sample permissions."""
        context = SecurityContext(user_data={'username': 'test_user'})
        context._permissions_details_cache = []
        return context
    
    @pytest.fixture
    def rewriter(self, mock_context):
        """Create QueryRewriter instance."""
        return EnhancedQueryRewriter(mock_context)
    
    def test_parse_entity_classes_simple(self, rewriter):
        """Test parsing entity classes from simple query."""
        cypher = "MATCH (g:Geography) WHERE g.level = 0 RETURN g"
        
        entities = rewriter._parse_entity_classes(cypher)
        
        assert 'g' in entities
        assert entities['g'] == 'Geography'
    
    def test_parse_entity_classes_multiple(self, rewriter):
        """Test parsing multiple entity types."""
        cypher = "MATCH (g:Geography)-[:TRADES_WITH]->(c:Commodity) RETURN g, c"
        
        entities = rewriter._parse_entity_classes(cypher)
        
        assert 'g' in entities
        assert 'c' in entities
        assert entities['g'] == 'Geography'
        assert entities['c'] == 'Commodity'
    
    def test_rewrite_with_superuser_no_changes(self, mock_context):
        """Test that superusers bypass query rewriting."""
        mock_context.is_superuser = True
        rewriter = EnhancedQueryRewriter(mock_context)
        
        original_cypher = "MATCH (g:Geography) RETURN g"
        params = {}
        
        modified_cypher, modified_params = rewriter.rewrite(original_cypher, params)
        
        assert modified_cypher == original_cypher
    
    def test_add_row_filters_simple(self, mock_context, rewriter):
        """Test adding simple row filter to WHERE clause."""
        # Mock row filters
        mock_context.get_row_filters = Mock(return_value=["country = 'France'"])
        
        cypher = "MATCH (g:Geography) WHERE g.level = 0 RETURN g"
        parts = {'where_clause': 'g.level = 0', 'match_clause': '(g:Geography)', 'return_clause': 'g'}
        entities = {'g': 'Geography'}
        
        modified = rewriter._add_row_filters(cypher, parts, entities)
        
        assert "AND" in modified
        assert "g.country = 'France'" in modified
    
    def test_add_row_filters_no_existing_where(self, mock_context, rewriter):
        """Test adding row filter when no WHERE clause exists."""
        mock_context.get_row_filters = Mock(return_value=["country = 'France'"])
        
        cypher = "MATCH (g:Geography) RETURN g"
        parts = {'where_clause': None, 'match_clause': '(g:Geography)', 'return_clause': 'g'}
        entities = {'g': 'Geography'}
        
        modified = rewriter._add_row_filters(cypher, parts, entities)
        
        assert "WHERE" in modified
        assert "g.country = 'France'" in modified
    
    def test_filter_properties_removes_denied(self, mock_context, rewriter):
        """Test that denied properties are removed from RETURN."""
        mock_context.get_denied_properties = Mock(return_value={'price', 'confidential_notes'})
        
        cypher = "MATCH (bs:BalanceSheet) RETURN bs.product_name, bs.price, bs.season"
        parts = {'return_clause': 'bs.product_name, bs.price, bs.season', 'match_clause': '(bs:BalanceSheet)', 'where_clause': None}
        entities = {'bs': 'BalanceSheet'}
        
        modified = rewriter._filter_properties(cypher, parts, entities)
        
        assert "bs.product_name" in modified
        assert "bs.season" in modified
        assert "bs.price" not in modified
    
    def test_filter_properties_preserves_allowed(self, mock_context, rewriter):
        """Test that allowed properties are preserved."""
        mock_context.get_denied_properties = Mock(return_value={'price'})
        
        cypher = "MATCH (bs:BalanceSheet) RETURN bs.product_name, bs.season"
        parts = {'return_clause': 'bs.product_name, bs.season', 'match_clause': '(bs:BalanceSheet)', 'where_clause': None}
        entities = {'bs': 'BalanceSheet'}
        
        modified = rewriter._filter_properties(cypher, parts, entities)
        
        assert "bs.product_name" in modified
        assert "bs.season" in modified
    
    def test_add_edge_filters(self, mock_context, rewriter):
        """Test adding edge-level filters."""
        mock_context.get_edge_filters = Mock(return_value=["commodity = 'Wheat'"])
        
        cypher = "MATCH (g1:Geography)-[t:TRADES_WITH]->(g2:Geography) RETURN g1, g2"
        parts = {'where_clause': None, 'match_clause': '(g1:Geography)-[t:TRADES_WITH]->(g2:Geography)', 'return_clause': 'g1, g2'}
        
        modified = rewriter._add_edge_filters(cypher, parts)
        
        assert "WHERE" in modified
        assert "t.commodity = 'Wheat'" in modified
    
    def test_rewrite_complete_flow(self, mock_context):
        """Test complete rewrite with row and property filters."""
        # Setup mock context with filters
        mock_context.get_row_filters = Mock(return_value=["country = 'France'"])
        mock_context.get_denied_properties = Mock(return_value={'confidential_notes'})
        mock_context.get_edge_filters = Mock(return_value=[])
        
        rewriter = EnhancedQueryRewriter(mock_context)
        
        cypher = "MATCH (g:Geography) WHERE g.level = 0 RETURN g.name, g.country, g.confidential_notes"
        params = {}
        
        modified_cypher, modified_params = rewriter.rewrite(cypher, params)
        
        # Should have row filter added
        assert "g.country = 'France'" in modified_cypher or "country = 'France'" in modified_cypher
        
        # Should have security params injected
        assert '__security_user_id__' in modified_params
        assert '__security_roles__' in modified_params
    
    def test_rewrite_preserves_order_by(self, mock_context, rewriter):
        """Test that ORDER BY clause is preserved."""
        mock_context.get_row_filters = Mock(return_value=["country = 'France'"])
        mock_context.get_denied_properties = Mock(return_value=set())
        mock_context.get_edge_filters = Mock(return_value=[])
        
        cypher = "MATCH (g:Geography) RETURN g ORDER BY g.name"
        parts = {'where_clause': None, 'match_clause': '(g:Geography)', 'return_clause': 'g'}
        entities = {'g': 'Geography'}
        
        modified = rewriter._add_row_filters(cypher, parts, entities)
        
        assert "ORDER BY" in modified
    
    def test_rewrite_preserves_limit(self, mock_context, rewriter):
        """Test that LIMIT clause is preserved."""
        mock_context.get_row_filters = Mock(return_value=["country = 'France'"])
        mock_context.get_denied_properties = Mock(return_value=set())
        mock_context.get_edge_filters = Mock(return_value=[])
        
        cypher = "MATCH (g:Geography) RETURN g LIMIT 10"
        parts = {'where_clause': None, 'match_clause': '(g:Geography)', 'return_clause': 'g'}
        entities = {'g': 'Geography'}
        
        modified = rewriter._add_row_filters(cypher, parts, entities)
        
        assert "LIMIT" in modified
    
    def test_should_filter_query_with_metadata(self, rewriter):
        """Test should_filter_query with entity having security metadata."""
        # Mock entity class with security metadata
        class MockEntity:
            __security_metadata__ = {
                'row_filter': 'n.level = 0',
                'deny_read_properties': ['confidential']
            }
        
        result = rewriter.should_filter_query(MockEntity)
        
        assert result is True
    
    def test_should_filter_query_non_superuser(self, mock_context, rewriter):
        """Test that non-superusers always trigger filtering."""
        mock_context.is_superuser = False
        
        class MockEntity:
            pass
        
        result = rewriter.should_filter_query(MockEntity)
        
        assert result is True


class TestQueryRewriterEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_query(self):
        """Test handling of empty query."""
        context = SecurityContext(user_data={'username': 'test'})
        rewriter = EnhancedQueryRewriter(context)
        
        cypher = ""
        params = {}
        
        # Should not crash
        modified_cypher, modified_params = rewriter.rewrite(cypher, params)
        
        assert modified_cypher == cypher
    
    def test_query_without_match(self):
        """Test query without MATCH clause."""
        context = SecurityContext(user_data={'username': 'test'})
        rewriter = EnhancedQueryRewriter(context)
        
        cypher = "RETURN 1 as result"
        params = {}
        
        modified_cypher, modified_params = rewriter.rewrite(cypher, params)
        
        # Should preserve query
        assert "RETURN 1" in modified_cypher
    
    def test_complex_property_access(self):
        """Test handling of complex property patterns."""
        context = SecurityContext(user_data={'username': 'test'})
        context.get_denied_properties = Mock(return_value={'price'})
        rewriter = EnhancedQueryRewriter(context)
        
        cypher = "MATCH (n) RETURN n.name as name, n.price * 1.1 as adjusted_price"
        parts = {'return_clause': 'n.name as name, n.price * 1.1 as adjusted_price', 'match_clause': '(n)', 'where_clause': None}
        entities = {'n': 'Product'}
        
        modified = rewriter._filter_properties(cypher, parts, entities)
        
        # Should remove price calculation
        assert "n.name" in modified
        assert "n.price" not in modified or "price" not in modified.split("RETURN")[1].split("ORDER")[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
