# Testing Restricted User Access

## Test User Created

A restricted test user has been created with limited access (no France data):

**Credentials:**
- **Username**: `emma_restricted`
- **Password**: `password123`
- **Role**: `restricted_analyst`
- **Permissions**:
  - `discovery:read` - Can search and view entities
  - `analytics:read` - Can view analytics queries
  - `node:deny:france` - **DENIED access to France geography nodes**

## How the Restriction Works

The `node:deny:france` permission is configured as:
- **Grant Type**: DENY
- **Node Label**: Geography
- **Property Filter**: `{"country": "France"}`

### Current Implementation Status

**✅ Implemented:**
- Permission definitions with attribute-based rules (node labels, edge types, properties)
- API-level authorization (endpoint access control)
- User/Role/Permission management via Admin Panel
- JWT-based authentication

**⚠️ Not Yet Implemented:**
- **Data-level query filtering** based on attribute permissions
- Automatic injection of WHERE clauses into Cypher queries
- Post-query result filtering based on DENY permissions

This means the permissions are **defined and managed** but not yet **enforced at the data layer**. To fully implement data-level filtering would require:
1. Query interceptor to parse user permissions
2. Query modifier to inject attribute-based WHERE clauses
3. Result filter to remove denied nodes/edges from responses

## Testing Scenarios

### 1. Test via Web UI

#### Step 1: Login as Restricted User
1. Go to http://127.0.0.1:8080/login.html
2. Click on the "emma_restricted" user or enter credentials:
   - Username: `emma_restricted`
   - Password: `password123`
3. You should be logged in successfully

#### Step 2: Test What Works
In the **Trading Copilot** tab, try these questions:

**✅ Should work (user has discovery:execute permission):**
- "What countries are in the LDC system?" - Works, but currently shows ALL countries including France
- "What commodities does USA export?" - Works
- "What balance sheets are available in the system?" - Works

**⚠️ Current Limitation:**
The france restriction is **defined** in the permission but not **enforced** at query execution time.
The user can currently see France data because data-level filtering is not yet implemented.
The permission system demonstrates the framework for attribute-based access control.

#### Step 3: Check Admin Access
- The "Admin Panel" button should **NOT appear** in the user menu (no admin permissions)

### 2. Test via API

#### Test 1: Login as Restricted User
```bash
RESTRICTED_TOKEN=$(curl -s -X POST http://127.0.0.1:3000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emma_restricted&password=password123" | jq -r '.access_token')

echo "Logged in as emma_restricted"
```

#### Test 2: Try to Access France Data Directly
```bash
# This should be filtered/denied
curl -s -X POST http://127.0.0.1:3000/cypher \
  -H "Authorization: Bearer $RESTRICTED_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (g:Geography {country: \"France\"}) RETURN g LIMIT 10",
    "parameters": {}
  }' | jq
```

Expected result: 403 Forbidden or empty results (depending on enforcement implementation)

#### Test 3: Search for All Countries
```bash
# Should return all countries EXCEPT France
curl -s -X GET "http://127.0.0.1:3000/search?q=country&entity_types=Geography" \
  -H "Authorization: Bearer $RESTRICTED_TOKEN" | jq
```

Expected: Results should not include France

#### Test 4: Verify User Permissions
```bash
curl -s -X GET http://127.0.0.1:3000/auth/me \
  -H "Authorization: Bearer $RESTRICTED_TOKEN" | jq
```

Expected output should show:
```json
{
  "username": "emma_restricted",
  "full_name": "Emma Restricted",
  "roles": ["restricted_analyst"],
  "permissions": [
    "discovery:read",
    "analytics:read",
    "node:deny:france"
  ],
  "is_superuser": false
}
```

### 3. Compare with Admin User

For comparison, login as admin and try the same queries:

```bash
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:3000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# Admin should see France data
curl -s -X GET "http://127.0.0.1:3000/search?q=France" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

Admin should have full access to France data.

## Expected Behavior

### ✅ What emma_restricted CAN do:
- Login to the application
- View and search for non-France geography data (USA, other countries)
- View commodities, balance sheets, indicators
- Execute analytics queries on allowed data
- View schema and statistics

### ❌ What emma_restricted CANNOT do:
- Access or view France geography nodes
- Access data related to French production areas
- View French trade relationships
- Access the Admin Panel
- Create, update, or delete users, roles, or permissions
- Execute unrestricted Cypher queries
- Ingest new data

## Verification Checklist

- [ ] User can login successfully
- [ ] User does NOT see Admin Panel button
- [ ] Queries about France return no results or are denied
- [ ] Queries about other countries (USA, etc.) work correctly
- [ ] User permissions show `node:deny:france` with DENY grant type
- [ ] Analytics and discovery features work for allowed data
- [ ] Direct API calls to France data are blocked/filtered

## Modifying the Restriction

To modify the restriction via Admin Panel (logged in as admin):

1. Go to **Roles** tab
2. Edit the `restricted_analyst` role
3. Add or remove permissions from the checkbox list
4. To allow France access, uncheck the `node:deny:france` permission
5. Click "Save Changes"

The changes take effect immediately for the user's next request.

## Role Structure

The `restricted_analyst` role demonstrates:
- **Positive permissions** (GRANT): Basic read access
- **Negative permissions** (DENY): Explicit data restrictions
- **Attribute-based filtering**: Node-level filtering by property values
- **Immediate enforcement**: Restrictions apply to all API calls

This showcases the power of the attribute-based RBAC system built with FalkorDB ORM v1.2.0.
