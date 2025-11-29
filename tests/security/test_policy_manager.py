"""
Tests for PolicyManager - Permission to PolicyRule conversion
"""

import pytest
import json
from src.security.policy_manager import PolicyManager


class TestPolicyManager:
    """Test PolicyManager permission loading and conversion."""
    
    def test_build_cypher_condition_simple(self):
        """Test building simple Cypher WHERE condition from permission."""
        permission = {
            'property_filter': '{"country": "France"}',
            'attribute_conditions': None
        }
        
        condition = PolicyManager.build_cypher_condition(permission, 'g')
        
        assert condition == "g.country = 'France'"
    
    def test_build_cypher_condition_multiple(self):
        """Test building Cypher condition with multiple filters."""
        permission = {
            'property_filter': '{"country": "France", "level": 0}',
            'attribute_conditions': None
        }
        
        condition = PolicyManager.build_cypher_condition(permission, 'g')
        
        assert "g.country = 'France'" in condition
        assert "g.level = 0" in condition
        assert " AND " in condition
    
    def test_build_cypher_condition_with_attribute(self):
        """Test building Cypher condition with attribute_conditions."""
        permission = {
            'property_filter': None,
            'attribute_conditions': 'n.value > 1000000'
        }
        
        condition = PolicyManager.build_cypher_condition(permission, 'g')
        
        assert condition == "(g.value > 1000000)"
    
    def test_build_cypher_condition_combined(self):
        """Test building Cypher condition with both property_filter and attribute_conditions."""
        permission = {
            'property_filter': '{"country": "France"}',
            'attribute_conditions': 'n.year >= 2024'
        }
        
        condition = PolicyManager.build_cypher_condition(permission, 'g')
        
        assert "g.country = 'France'" in condition
        assert "(g.year >= 2024)" in condition
        assert " AND " in condition
    
    def test_build_resource_pattern_node(self):
        """Test building resource pattern for node-level permission."""
        manager = PolicyManager(None)
        permission = {
            'resource': 'node',
            'node_label': 'Geography'
        }
        
        pattern = manager._build_resource_pattern(permission)
        
        assert pattern == 'Geography'
    
    def test_build_resource_pattern_edge(self):
        """Test building resource pattern for edge-level permission."""
        manager = PolicyManager(None)
        permission = {
            'resource': 'edge',
            'edge_type': 'TRADES_WITH'
        }
        
        pattern = manager._build_resource_pattern(permission)
        
        assert pattern == 'TRADES_WITH'
    
    def test_build_resource_pattern_property(self):
        """Test building resource pattern for property-level permission."""
        manager = PolicyManager(None)
        permission = {
            'resource': 'property',
            'node_label': 'BalanceSheet',
            'property_name': 'price'
        }
        
        pattern = manager._build_resource_pattern(permission)
        
        assert pattern == 'BalanceSheet.price'
    
    def test_build_conditions(self):
        """Test building conditions dictionary from permission."""
        manager = PolicyManager(None)
        permission = {
            'node_label': 'Geography',
            'property_filter': '{"country": "France"}',
            'attribute_conditions': 'n.level = 0'
        }
        
        conditions = manager._build_conditions(permission)
        
        assert conditions is not None
        assert conditions['node_label'] == 'Geography'
        assert conditions['property_filter'] == {"country": "France"}
        assert conditions['attribute_conditions'] == 'n.level = 0'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
