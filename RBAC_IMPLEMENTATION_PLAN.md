# RBAC Implementation Plan - Tijara Knowledge Graph

**Date Started:** November 29, 2024  
**ORM Version:** falkordb-orm 1.2.0  
**Status:** In Progress

---

## Overview

Implementing a comprehensive Role-Based Access Control (RBAC) system with:
- User authentication via JWT tokens
- Role and permission management stored in FalkorDB
- Admin UI for RBAC administration
- Login page with different user access levels
- Integration with existing UI tabs (Analytics, Ingestion, Discovery, Impact)

---

## Implementation Progress

### ✅ Phase 1: Core Models (COMPLETED)
- [x] Created `src/models/security.py` with User, Role, Permission entities
- [x] Defined system roles: admin, analyst, trader, data_engineer, viewer
- [x] Defined permissions for all resources: analytics, ingestion, discovery, impact, rbac

### ✅ Phase 2: Authentication (COMPLETED)
- [x] Created `src/security/auth.py` with JWT token management
- [x] Password hashing with bcrypt
- [x] Token creation and validation
- [x] Session ID generation

### ✅ Phase 3: Security Context (COMPLETED)
- [x] Created `src/security/context.py` for permission checking
- [x] Permission caching for performance
- [x] Role hierarchy support
- [x] Wildcard permission matching

### 🔄 Phase 4: API Integration (IN PROGRESS)
- [ ] Add authentication endpoints to FastAPI
- [ ] Add RBAC management endpoints
- [ ] Integrate security context with existing endpoints
- [ ] Add permission decorators

### 📋 Phase 5: UI Components (TODO)
- [ ] Create login.html page
- [ ] Create admin.html RBAC management page
- [ ] Add authentication to main UI
- [ ] Add role-based UI element visibility

### 📋 Phase 6: Demo Data (TODO)
- [ ] Create initialization script for RBAC data
- [ ] Create demo users with different roles
- [ ] Test access control scenarios

---

## System Roles Defined

| Role | Description | Permissions |
|------|-------------|-------------|
| **admin** | Full system access | All permissions including RBAC management |
| **analyst** | Analytics and discovery | analytics:*, discovery:read, impact:* |
| **trader** | Trading operations | analytics:*, discovery:*, impact:* |
| **data_engineer** | Data management | ingestion:*, discovery:read |
| **viewer** | Read-only access | analytics:read, discovery:read |

---

## Permissions Matrix

| Resource | Actions | Description |
|----------|---------|-------------|
| **analytics** | read, execute | View and run graph algorithms |
| **ingestion** | read, write | View and ingest data |
| **discovery** | read, execute | Search and query entities |
| **impact** | read, execute | View and run impact analysis |
| **rbac** | read, write, admin | Manage users, roles, permissions |

---

## Files Created

### Models
- ✅ `src/models/security.py` - User, Role, Permission entities (127 lines)

### Security Module
- ✅ `src/security/__init__.py` - Module initialization (23 lines)
- ✅ `src/security/auth.py` - Authentication utilities (77 lines)
- ✅ `src/security/context.py` - Security context (218 lines)

### TODO: API Files
- [ ] Update `api/main.py` - Add auth endpoints
- [ ] Create `api/rbac.py` - RBAC management endpoints
- [ ] Create `api/dependencies.py` - FastAPI dependencies for auth

### TODO: UI Files
- [ ] Create `web/login.html` - Login page
- [ ] Create `web/admin.html` - RBAC admin page
- [ ] Update `web/index.html` - Add authentication
- [ ] Update `web/static/js/app.js` - Add auth handling

### TODO: Scripts
- [ ] Create `scripts/init_rbac.py` - Initialize RBAC data
- [ ] Create `scripts/create_demo_users.py` - Create demo users

---

## Next Steps

### Immediate Tasks
1. **Add authentication endpoints** to FastAPI:
   - `POST /auth/login` - User login
   - `POST /auth/logout` - User logout  
   - `GET /auth/me` - Get current user
   - `POST /auth/refresh` - Refresh token

2. **Add RBAC management endpoints**:
   - `GET /rbac/users` - List users
   - `POST /rbac/users` - Create user
   - `GET /rbac/roles` - List roles
   - `POST /rbac/roles/{role}/assign` - Assign role to user

3. **Create login UI**:
   - Simple login form with username/password
   - JWT token storage in localStorage
   - Redirect after login

4. **Create admin UI**:
   - User management table
   - Role assignment interface
   - Permission viewer

5. **Integrate with existing endpoints**:
   - Add security dependency to all endpoints
   - Check permissions before executing operations
   - Return 403 Forbidden for unauthorized access

---

## Demo Users to Create

| Username | Password | Role | Use Case |
|----------|----------|------|----------|
| admin | admin123 | admin | Full access for testing |
| alice_analyst | password | analyst | Analytics-focused user |
| bob_trader | password | trader | Trading operations |
| charlie_engineer | password | data_engineer | Data ingestion |
| dave_viewer | password | viewer | Read-only access |

---

## Required Dependencies

Add to `requirements.txt`:
```
python-jose[cryptography]>=3.3.0  # JWT tokens
passlib[bcrypt]>=1.7.4  # Password hashing
python-multipart>=0.0.6  # Form data parsing
```

---

## Security Best Practices

1. **Password Storage**: Using bcrypt with automatic salt
2. **JWT Tokens**: Short expiration (8 hours), include user ID and roles
3. **Session Management**: Stateless JWT, no server-side session storage
4. **Permission Caching**: Cache permissions per request to reduce queries
5. **Error Messages**: Generic messages to prevent username enumeration
6. **HTTPS Only**: In production, enforce HTTPS for all auth endpoints

---

## Testing Strategy

### Unit Tests
- Test password hashing and verification
- Test JWT token creation and validation
- Test permission checking logic
- Test role inheritance

### Integration Tests
- Test login flow
- Test permission enforcement on endpoints
- Test RBAC admin operations
- Test different user roles

### UI Tests
- Test login page functionality
- Test admin page CRUD operations
- Test UI element visibility based on roles
- Test unauthorized access handling

---

## Performance Considerations

1. **Permission Caching**: Cache user permissions in SecurityContext
2. **Graph Queries**: Single query to fetch all user permissions
3. **JWT Tokens**: No database lookup needed for auth
4. **Index Creation**: Add indexes on User.username and Role.name

---

## Migration Path

1. **Phase 1**: Deploy with RBAC disabled (backward compatible)
2. **Phase 2**: Initialize RBAC data and create admin user
3. **Phase 3**: Enable authentication requirement
4. **Phase 4**: Migrate existing access patterns to roles

---

## API Changes Summary

### New Endpoints
- `POST /auth/login` - Authenticate user
- `POST /auth/logout` - Invalidate session
- `GET /auth/me` - Get current user info
- `GET /rbac/users` - List users (admin only)
- `POST /rbac/users` - Create user (admin only)
- `PUT /rbac/users/{id}/roles` - Assign roles (admin only)
- `GET /rbac/roles` - List roles (admin only)
- `GET /rbac/permissions` - List permissions (admin only)

### Modified Endpoints
All existing endpoints will require authentication and check permissions:
- `/analytics` - Requires analytics:read or analytics:execute
- `/ingest` - Requires ingestion:write
- `/search` - Requires discovery:read
- `/query` - Requires discovery:execute
- `/impact` - Requires impact:execute

---

## Documentation Needs

1. **API Documentation**: Update with authentication requirements
2. **User Guide**: How to login and use RBAC
3. **Admin Guide**: How to manage users and roles
4. **Developer Guide**: How to add new permissions

---

**Last Updated:** November 29, 2024  
**Implementation Progress:** 40% Complete  
**Estimated Completion:** Phase 4-6 remaining
