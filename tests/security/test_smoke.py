"""
Smoke tests to validate basic implementation of security filtering.

These tests ensure all components can be imported and instantiated correctly.
"""

import pytest


class TestImports:
    """Test that all security components can be imported."""
    
    def test_import_policy_manager(self):
        """Test PolicyManager import."""
        from src.security.policy_manager import PolicyManager
        assert PolicyManager is not None
    
    def test_import_query_rewriter(self):
        """Test EnhancedQueryRewriter import."""
        from src.security.query_rewriter_enhanced import EnhancedQueryRewriter
        assert EnhancedQueryRewriter is not None
    
    def test_import_security_context(self):
        """Test SecurityContext import."""
        from src.security.context import SecurityContext, ANONYMOUS_CONTEXT
        assert SecurityContext is not None
        assert ANONYMOUS_CONTEXT is not None
    
    def test_import_secure_decorator(self):
        """Test @secure decorator import."""
        from src.models.base_secure_entity import secure, SecureEntityMixin
        assert secure is not None
        assert SecureEntityMixin is not None
    
    def test_import_secure_repository(self):
        """Test SecureRepository imports."""
        from src.repositories.secure_repository_factory import (
            SecureRepositoryWrapper,
            create_secure_repository,
            wrap_existing_repository
        )
        assert SecureRepositoryWrapper is not None
        assert create_secure_repository is not None
        assert wrap_existing_repository is not None


class TestBasicInstantiation:
    """Test that components can be instantiated."""
    
    def test_security_context_creation(self):
        """Test creating SecurityContext."""
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={'username': 'test_user'})
        
        assert context.username == 'test_user'
        assert context.is_authenticated
        assert not context.is_superuser
    
    def test_security_context_superuser(self):
        """Test superuser SecurityContext."""
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={'username': 'admin', 'is_superuser': True})
        
        assert context.is_superuser
        assert context.is_authenticated
    
    def test_security_context_anonymous(self):
        """Test anonymous SecurityContext."""
        from src.security.context import SecurityContext
        
        context = SecurityContext()
        
        assert context.is_anonymous
        assert not context.is_authenticated
    
    def test_query_rewriter_creation(self):
        """Test creating EnhancedQueryRewriter."""
        from src.security.query_rewriter_enhanced import EnhancedQueryRewriter
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={'username': 'test'})
        rewriter = EnhancedQueryRewriter(context)
        
        assert rewriter is not None
        assert rewriter.context == context
    
    def test_secure_decorator_usage(self):
        """Test using @secure decorator."""
        from src.models.base_secure_entity import secure
        
        @secure(
            row_filter="n.country = 'France'",
            deny_read_properties=['price']
        )
        class TestEntity:
            pass
        
        assert hasattr(TestEntity, '__security_metadata__')
        assert TestEntity.__security_metadata__['row_filter'] == "n.country = 'France'"
        assert 'price' in TestEntity.__security_metadata__['deny_read_properties']
    
    def test_secure_entity_mixin(self):
        """Test SecureEntityMixin methods."""
        from src.models.base_secure_entity import SecureEntityMixin
        
        class TestEntity(SecureEntityMixin):
            __security_metadata__ = {
                'row_filter': 'n.level = 0',
                'deny_read_properties': ['confidential']
            }
        
        assert TestEntity.has_row_filter()
        assert TestEntity.has_property_filters()
        assert TestEntity.get_row_filter() == 'n.level = 0'
        assert 'confidential' in TestEntity.get_denied_read_properties()


class TestSecurityContextMethods:
    """Test SecurityContext data-level methods."""
    
    def test_get_permissions(self):
        """Test getting user permissions."""
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={
            'username': 'test',
            'permissions': ['analytics:read', 'discovery:read']
        })
        
        perms = context.get_permissions()
        
        assert 'analytics:read' in perms
        assert 'discovery:read' in perms
    
    def test_has_permission(self):
        """Test permission checking."""
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={
            'username': 'test',
            'permissions': ['analytics:read']
        })
        
        assert context.has_permission('analytics:read')
        assert not context.has_permission('analytics:write')
    
    def test_superuser_has_all_permissions(self):
        """Test that superusers have all permissions."""
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={
            'username': 'admin',
            'is_superuser': True
        })
        
        assert context.has_permission('analytics:read')
        assert context.has_permission('analytics:write')
        assert context.has_permission('any:permission')
    
    def test_get_row_filters_empty(self):
        """Test get_row_filters with no permissions."""
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={'username': 'test'})
        
        filters = context.get_row_filters('Geography', 'read')
        
        # No graph connection, should return empty
        assert filters == []
    
    def test_get_denied_properties_empty(self):
        """Test get_denied_properties with no permissions."""
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={'username': 'test'})
        
        denied = context.get_denied_properties('Geography', 'read')
        
        # No graph connection, should return empty
        assert denied == set()
    
    def test_superuser_no_filters(self):
        """Test that superusers have no filters."""
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={
            'username': 'admin',
            'is_superuser': True
        })
        
        filters = context.get_row_filters('Geography', 'read')
        denied = context.get_denied_properties('Geography', 'read')
        
        assert filters == []
        assert denied == set()


class TestPolicyManager:
    """Test PolicyManager basic functionality."""
    
    def test_build_cypher_condition_simple(self):
        """Test building Cypher condition."""
        from src.security.policy_manager import PolicyManager
        
        permission = {
            'property_filter': '{"country": "France"}',
            'attribute_conditions': None
        }
        
        condition = PolicyManager.build_cypher_condition(permission, 'g')
        
        assert condition == "g.country = 'France'"
    
    def test_build_cypher_condition_numeric(self):
        """Test building Cypher condition with numeric value."""
        from src.security.policy_manager import PolicyManager
        
        permission = {
            'property_filter': '{"level": 0}',
            'attribute_conditions': None
        }
        
        condition = PolicyManager.build_cypher_condition(permission, 'g')
        
        assert "g.level = 0" in condition


class TestQueryRewriting:
    """Test basic query rewriting."""
    
    def test_superuser_bypasses_rewriting(self):
        """Test that superusers bypass query rewriting."""
        from src.security.query_rewriter_enhanced import EnhancedQueryRewriter
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={'username': 'admin', 'is_superuser': True})
        rewriter = EnhancedQueryRewriter(context)
        
        original_cypher = "MATCH (g:Geography) RETURN g"
        params = {}
        
        modified_cypher, modified_params = rewriter.rewrite(original_cypher, params)
        
        assert modified_cypher == original_cypher
    
    def test_rewrite_injects_params(self):
        """Test that rewrite injects security params."""
        from src.security.query_rewriter_enhanced import EnhancedQueryRewriter
        from src.security.context import SecurityContext
        
        context = SecurityContext(user_data={'username': 'test', 'roles': ['analyst']})
        rewriter = EnhancedQueryRewriter(context)
        
        cypher = "MATCH (g:Geography) RETURN g"
        params = {}
        
        _, modified_params = rewriter.rewrite(cypher, params)
        
        assert '__security_user_id__' in modified_params
        assert '__security_roles__' in modified_params
        assert modified_params['__security_user_id__'] == 'test'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
