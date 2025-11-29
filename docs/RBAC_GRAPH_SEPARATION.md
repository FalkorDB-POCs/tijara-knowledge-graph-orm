# RBAC Graph Separation

## Overview

The RBAC (Role-Based Access Control) system data has been successfully separated from the application data graph into a dedicated security graph. This follows best practices for data isolation and security.

## Implementation

### Graph Configuration

Added RBAC configuration section to `config/config.yaml`:

```yaml
rbac:
  host: "localhost"
  port: 6379
  graph_name: "tijara_rbac"  # Separate graph for security data
  username: null
  password: null
  ssl: false
```

### Changes Made

1. **Configuration Updates**
   - Added `rbac` section to `config/config.yaml` with separate graph configuration
   - Default graph name: `tijara_rbac`

2. **Init Script Updates** (`scripts/init_rbac.py`)
   - Loads RBAC graph name from configuration
   - Removed hardcoded `ldc_graph` default
   - Uses `config['rbac']['graph_name']` to determine target graph
   - Accepts optional `--graph` CLI argument to override config

3. **API Updates** (`api/main.py`)
   - Added separate FalkorDB connection for RBAC operations
   - Created dedicated `rbac_graph` instance from config
   - Replaced all RBAC queries to use `rbac_graph` instead of `kg.falkordb.graph`
   - Authentication, user management, and admin operations now isolated

### Graph Structure

#### Application Graph (`ldc_graph`)
Contains business data only:
- Geography nodes (3,310)
- Commodity nodes (37)
- Component nodes (60)
- ProductionArea nodes (16)
- BalanceSheet nodes (12)
- Indicator nodes (9)
- DataPoint nodes (3)
- Source nodes (1)
- **No RBAC nodes** ✓

#### RBAC Graph (`tijara_rbac`)
Contains security metadata only:
- User nodes (5)
- Role nodes (5)
- Permission nodes (23)
- HAS_ROLE relationships
- HAS_PERMISSION relationships

## Benefits

1. **Data Isolation**: Security metadata completely separated from application data
2. **Scalability**: RBAC operations don't impact application graph performance
3. **Security**: Reduces risk of accidental data exposure or corruption
4. **Maintainability**: Clear separation of concerns
5. **Flexibility**: Can apply different backup/replication strategies per graph

## Migration Process

The migration involved:

1. Removing all User, Role, and Permission nodes from `ldc_graph`
2. Initializing RBAC data in `tijara_rbac` graph
3. Updating all API endpoints to query the separate RBAC graph
4. Verifying no RBAC data remains in application graph

## Usage

### Initialize RBAC Data

```bash
# Uses graph name from config (tijara_rbac)
python3 scripts/init_rbac.py

# Override with custom graph name
python3 scripts/init_rbac.py --graph my_custom_rbac_graph
```

### Verify Separation

```python
from falkordb import FalkorDB

db = FalkorDB(host='localhost', port=6379)

# Check application graph
ldc_graph = db.select_graph('ldc_graph')
rbac_count = ldc_graph.query(
    'MATCH (n) WHERE n:User OR n:Role OR n:Permission RETURN count(n)'
).result_set[0][0]
print(f"RBAC nodes in ldc_graph: {rbac_count}")  # Should be 0

# Check RBAC graph
rbac_graph = db.select_graph('tijara_rbac')
users = rbac_graph.query('MATCH (u:User) RETURN count(u)').result_set[0][0]
roles = rbac_graph.query('MATCH (r:Role) RETURN count(r)').result_set[0][0]
perms = rbac_graph.query('MATCH (p:Permission) RETURN count(p)').result_set[0][0]
print(f"Users: {users}, Roles: {roles}, Permissions: {perms}")
```

## Demo Users

All demo users are created in the `tijara_rbac` graph:

| Username | Password | Role | Superuser |
|----------|----------|------|-----------|
| admin | admin123 | admin | Yes |
| alice_analyst | password | analyst | No |
| bob_trader | password | trader | No |
| charlie_engineer | password | data_engineer | No |
| dave_viewer | password | viewer | No |

## Technical Details

### API Initialization

```python
# Initialize separate RBAC graph connection
from falkordb import FalkorDB

rbac_db = FalkorDB(
    host=config['rbac'].get('host', 'localhost'),
    port=config['rbac'].get('port', 6379)
)
rbac_graph = rbac_db.select_graph(config['rbac']['graph_name'])
```

### Authentication Flow

1. User submits login credentials to `/auth/login`
2. API queries `tijara_rbac` graph for user credentials
3. Password verified, JWT token generated
4. Subsequent requests authenticated via JWT
5. Authorization checks query `tijara_rbac` for user permissions
6. Application data queries go to `ldc_graph`

## Status

✅ **Complete and operational**

- RBAC data successfully isolated in `tijara_rbac` graph
- Application data graph contains no security metadata
- Authentication and authorization working correctly
- Admin panel functional with separated graphs
- All CRUD operations for users, roles, and permissions operational
