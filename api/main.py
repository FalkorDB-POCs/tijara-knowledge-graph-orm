"""
Tijara Knowledge Graph API
FastAPI application providing REST API for the knowledge graph
"""

from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import yaml
import os

from src.core.orm_knowledge_graph import ORMKnowledgeGraph
from src.security.auth import create_access_token, verify_password
from api.dependencies import get_current_user, require_permission, get_security_context
from src.security.context import SecurityContext
from src.security.query_rewriter_enhanced import EnhancedQueryRewriter

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Set OpenAI API key from config if available
if 'openai' in config and 'api_key' in config['openai'] and config['openai']['api_key']:
    os.environ['OPENAI_API_KEY'] = config['openai']['api_key']

# Initialize FastAPI app
app = FastAPI(
    title="Tijara Knowledge Graph API (ORM)",
    description="API for LDC's commodity trading knowledge graph with ORM layer",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config['api']['cors_origins'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize separate RBAC graph connection
from falkordb import FalkorDB
rbac_db = FalkorDB(
    host=config['rbac'].get('host', 'localhost'),
    port=config['rbac'].get('port', 6379)
)
rbac_graph = rbac_db.select_graph(config['rbac']['graph_name'])

# Initialize global knowledge graph for non-secured endpoints (health, stats, etc.)
# Secured endpoints will create their own instance with SecurityContext per-request
from src.security.context import ANONYMOUS_CONTEXT
kg = ORMKnowledgeGraph(config, security_context=ANONYMOUS_CONTEXT)

# Store RBAC graph in app state for dependency injection
app.state.rbac_graph = rbac_graph
app.state.config = config

# Mount static files for web interface
web_dir = os.path.join(os.path.dirname(__file__), '..', 'web')
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=os.path.join(web_dir, "static")), name="static")


# ========== Helper Function ==========

def get_knowledge_graph(security_context: SecurityContext) -> ORMKnowledgeGraph:
    """
    Create knowledge graph instance with security context.
    
    Args:
        security_context: Security context for data-level filtering
        
    Returns:
        ORMKnowledgeGraph instance
    """
    return ORMKnowledgeGraph(config, security_context=security_context)


# ========== Request/Response Models ==========

class QueryRequest(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = {}
    return_sources: bool = True


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    retrieved_entities: List[str]
    subgraph: Optional[List[Dict[str, Any]]] = None
    query_graph: Optional[List[Dict[str, Any]]] = None


class IngestionRequest(BaseModel):
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    validate: bool = True


class DocumentIngestionRequest(BaseModel):
    text: str
    source: Optional[str] = "user_input"
    metadata: Optional[Dict[str, Any]] = None


class AnalyticsRequest(BaseModel):
    algorithm: str
    filters: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None


class ImpactAnalysisRequest(BaseModel):
    event_geometry: Dict[str, Any]  # GeoJSON
    event_type: str
    max_hops: int = 5
    impact_threshold: float = 0.1


# ========== API Endpoints ==========

# ========== Authentication Endpoints ==========

@app.post("/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """
    Authenticate user and return JWT token.
    
    Form parameters:
    - username: User's username
    - password: User's password
    
    Returns:
    - access_token: JWT token for authentication
    - token_type: "bearer"
    - user_info: Basic user information
    """
    try:
        # Query user from database
        query = """
        MATCH (u:User {username: $username})
        RETURN u.password_hash as password_hash,
               u.is_superuser as is_superuser,
               u.is_active as is_active,
               u.full_name as full_name,
               u.email as email,
               id(u) as user_id
        """
        result = rbac_graph.query(query, {'username': username})
        
        if not result.result_set:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        row = result.result_set[0]
        password_hash = row[0]
        is_superuser = row[1]
        is_active = row[2]
        full_name = row[3]
        email = row[4]
        user_id = row[5]
        
        # Check if user is active
        if not is_active:
            raise HTTPException(
                status_code=403,
                detail="User account is disabled"
            )
        
        # Verify password
        if not verify_password(password, password_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Create JWT token
        token_data = {
            'sub': username,
            'user_id': user_id,
            'is_superuser': is_superuser
        }
        access_token = create_access_token(token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_info": {
                "username": username,
                "full_name": full_name,
                "email": email,
                "is_superuser": is_superuser
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}"
        )


@app.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Returns:
    - User information including username, roles, and permissions
    """
    try:
        username = current_user['sub']
        
        # Query detailed user information with roles and permissions
        query = """
        MATCH (u:User {username: $username})
        OPTIONAL MATCH (u)-[:HAS_ROLE]->(r:Role)
        OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(p:Permission)
        RETURN u.username as username,
               u.full_name as full_name,
               u.email as email,
               u.is_superuser as is_superuser,
               collect(DISTINCT r.name) as roles,
               collect(DISTINCT p.name) as permissions
        """
        result = rbac_graph.query(query, {'username': username})
        
        if not result.result_set:
            raise HTTPException(status_code=404, detail="User not found")
        
        row = result.result_set[0]
        return {
            "username": row[0],
            "full_name": row[1],
            "email": row[2],
            "is_superuser": row[3],
            "roles": [r for r in row[4] if r],  # Filter out None values
            "permissions": [p for p in row[5] if p]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch user info: {str(e)}"
        )


@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout endpoint (client should discard token).
    
    Note: JWT tokens are stateless, so logout is handled client-side
    by discarding the token. In a production system, you might want
    to implement token blacklisting.
    """
    return {
        "status": "success",
        "message": "Logged out successfully. Please discard your token."
    }


# ========== Public Endpoints ==========

@app.get("/")
async def root():
    """Serve the web interface."""
    web_index = os.path.join(os.path.dirname(__file__), '..', 'web', 'index.html')
    if os.path.exists(web_index):
        return FileResponse(web_index)
    else:
        # Fallback to API info if web UI not found
        return {
            "name": "Tijara Knowledge Graph API (ORM)",
            "version": "1.0.0",
            "description": "Commodity trading intelligence platform with ORM layer",
            "endpoints": {
                "query": "/query - Natural language questions",
                "ingest": "/ingest - Data ingestion",
                "analytics": "/analytics - Graph analytics",
                "impact": "/impact - Impact analysis",
                "health": "/health - Health check",
                "stats": "/stats - Graph statistics"
            },
            "ui": "Web UI not found. Place the web directory at the project root."
        }


@app.get("/login.html")
async def login_page():
    """Serve the login page."""
    login_html = os.path.join(os.path.dirname(__file__), '..', 'web', 'login.html')
    if os.path.exists(login_html):
        return FileResponse(login_html)
    else:
        raise HTTPException(status_code=404, detail="Login page not found")


@app.get("/admin.html")
async def admin_page():
    """Serve the admin page."""
    admin_html = os.path.join(os.path.dirname(__file__), '..', 'web', 'admin.html')
    if os.path.exists(admin_html):
        return FileResponse(admin_html)
    else:
        raise HTTPException(status_code=404, detail="Admin page not found")


@app.get("/test_health.html")
async def test_health_page():
    """Serve the test health page."""
    test_html = os.path.join(os.path.dirname(__file__), '..', 'test_health_ui.html')
    if os.path.exists(test_html):
        return FileResponse(test_html)
    else:
        raise HTTPException(status_code=404, detail="Test page not found")


@app.get("/config")
async def get_config():
    """Get system configuration including active dataset."""
    graph_name = config['falkordb'].get('graph_name', 'tijara_graph')
    dataset_type = 'ldc' if 'ldc' in graph_name.lower() else 'demo'
    return {
        "graph_name": graph_name,
        "dataset_type": dataset_type,
        "theme": f"theme-{dataset_type}.css",
        "version": "2.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health = kg.health_check()
    # Only fail if FalkorDB is down (Graphiti is optional)
    if not health.get('falkordb', False):
        raise HTTPException(status_code=503, detail="Service unavailable")
    return health


@app.get("/stats")
async def get_statistics():
    """Get graph statistics."""
    return kg.get_statistics()


@app.post("/query", response_model=QueryResponse)
async def query_natural_language(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
    security_context: SecurityContext = Depends(get_security_context)
):
    """
    Answer natural language questions using GraphRAG.
    
    The query respects data-level security and only returns results
    the user is permitted to see.
    
    Example:
    ```json
    {
        "question": "What are the relevant information on the demand of corn in Germany?",
        "return_sources": true
    }
    ```
    """
    try:
        # Use security-aware knowledge graph instance
        user_kg = get_knowledge_graph(security_context)
        
        result = await user_kg.query_natural_language(
            question=request.question,
            context=request.context,
            return_sources=request.return_sources
        )
        # Map query_graph to subgraph for backward compatibility
        if 'query_graph' in result:
            result['subgraph'] = result['query_graph']
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest", dependencies=[Depends(require_permission("ingestion:write"))])
async def ingest_data(request: IngestionRequest):
    """
    Ingest data with automatic ontology placement.
    
    Example:
    ```json
    {
        "data": [{"value": 1000, "year": 2023}],
        "metadata": {
            "region": "Picardie",
            "country": "France",
            "type": "Production",
            "commodity": "Wheat",
            "source": "USDA"
        },
        "validate": true
    }
    ```
    """
    try:
        result = await kg.ingest_data(
            data=request.data,
            metadata=request.metadata,
            validate=request.validate
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ingest/document", dependencies=[Depends(require_permission("ingestion:write"))])
async def ingest_document(request: DocumentIngestionRequest):
    """
    Ingest unstructured text documents using Graphiti.
    Graphiti will extract entities, relationships, and facts from the text
    and integrate them into the knowledge graph.
    
    Example:
    ```json
    {
        "text": "Brazil's soybean production reached 150 million metric tons in 2023, with exports to China increasing by 15%.",
        "source": "Market Report",
        "metadata": {
            "report_date": "2023-12-01",
            "author": "Market Analyst"
        }
    }
    ```
    """
    try:
        from datetime import datetime
        
        # Check if Graphiti is available
        if not kg.graphiti or not kg.graphiti.client:
            raise HTTPException(
                status_code=503,
                detail="Graphiti service not available. Ensure OpenAI API key is configured."
            )
        
        # Add the text as an episode to Graphiti
        # Graphiti will automatically extract entities and relationships
        # Using the correct API signature matching the official demo
        from graphiti_core.nodes import EpisodeType
        
        await kg.graphiti.client.add_episode(
            name=f"document_{request.source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            episode_body=request.text,
            source=EpisodeType.text,
            source_description=request.source,
            reference_time=datetime.now()
        )
        
        # Search for entities that were extracted
        search_results = await kg.graphiti.client.search(
            query=request.text[:500],  # Use first 500 chars as query
            num_results=20
        )
        
        # Collect extracted entities
        extracted_entities = []
        for result in search_results:
            entity_info = {
                'name': getattr(result, 'name', ''),
                'type': getattr(result, 'labels', ['Unknown'])[0] if hasattr(result, 'labels') else 'Unknown',
                'content': getattr(result, 'summary', '') or getattr(result, 'name', ''),
                'uuid': str(getattr(result, 'uuid', ''))
            }
            if entity_info['name']:
                extracted_entities.append(entity_info)
        
        return {
            'status': 'success',
            'message': f'Document ingested successfully. Graphiti extracted and integrated entities into the graph.',
            'text_length': len(request.text),
            'source': request.source,
            'entities_found': len(extracted_entities),
            'extracted_entities': extracted_entities[:10]  # Return first 10
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")


@app.post("/analytics", dependencies=[Depends(require_permission("analytics:execute"))])
async def run_analytics(request: AnalyticsRequest):
    """
    Execute graph analytics algorithms.
    
    Supported algorithms:
    - pagerank: PageRank centrality
    - centrality: Various centrality measures
    - community: Community detection
    - pathfinding: Shortest paths
    
    Example:
    ```json
    {
        "algorithm": "pagerank",
        "filters": {
            "commodity": "Corn",
            "indicator": "Exports"
        }
    }
    ```
    """
    try:
        result = kg.analyze_graph(
            algorithm=request.algorithm,
            filters=request.filters,
            parameters=request.parameters
        )
        return {"algorithm": request.algorithm, "results": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/impact", dependencies=[Depends(require_permission("impact:execute"))])
async def analyze_impact(request: ImpactAnalysisRequest):
    """
    Analyze impact of events on commodities and markets.
    
    Example:
    ```json
    {
        "event_geometry": {
            "type": "Polygon",
            "coordinates": [[[...]]]
        },
        "event_type": "drought",
        "max_hops": 5
    }
    ```
    """
    try:
        # Convert GeoJSON to Shapely geometry
        from shapely.geometry import shape
        geometry = shape(request.event_geometry)
        
        result = kg.find_impacts(
            event_geometry=geometry,
            event_type=request.event_type,
            max_hops=request.max_hops,
            impact_threshold=request.impact_threshold
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/search")
async def search_entities(
    q: str,
    entity_types: Optional[str] = None,
    limit: int = 20
):
    """
    Search for entities by name or properties.
    
    Query parameters:
    - q: Search term
    - entity_types: Comma-separated entity types (optional)
    - limit: Maximum results (default: 20)
    """
    try:
        types = entity_types.split(',') if entity_types else None
        results = kg.search_entities(
            search_term=q,
            entity_types=types,
            limit=limit
        )
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/debug/filters")
async def debug_filters(label: str = "Geography", security_context: SecurityContext = Depends(get_security_context)):
    try:
        return {
            "user": security_context.username,
            "is_superuser": security_context.is_superuser,
            "roles": security_context.get_roles(),
            "row_filters": security_context.get_row_filters(label, 'read')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schema")
async def get_schema():
    """Get ontology schema for exploration."""
    return kg.explore_schema()


@app.get("/entity/{entity_id}")
async def get_entity(entity_id: str, include_history: bool = False):
    """
    Get entity details and optionally its history.
    
    Query parameters:
    - include_history: Include version history (default: false)
    """
    try:
        if include_history:
            return kg.get_entity_history(entity_id, include_relationships=True)
        else:
            # Get current entity
            query = "MATCH (n) WHERE id(n) = $entity_id RETURN n"
            results = kg.execute_cypher(query, {'entity_id': int(entity_id)})
            if not results:
                raise HTTPException(status_code=404, detail="Entity not found")
            return results[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class CypherRequest(BaseModel):
    query: str
    parameters: Optional[Dict[str, Any]] = None


@app.post("/cypher")
async def execute_cypher(
    request: CypherRequest,
    current_user: dict = Depends(get_current_user),
    security_context: SecurityContext = Depends(get_security_context)
):
    """
    Execute Cypher query with data-level security filtering.
    
    The query will be automatically filtered based on the user's permissions.
    Superusers bypass all filtering.
    
    Example:
    ```json
    {
        "query": "MATCH (n:Production) RETURN n LIMIT 10",
        "parameters": {}
    }
    ```
    """
    try:
        # Create knowledge graph instance with user's security context
        user_kg = get_knowledge_graph(security_context)
        
        # Rewrite query with data-level filtering for non-superusers
        rewritten_query = request.query
        rewritten_params = request.parameters or {}
        if not security_context.is_superuser:
            rewriter = EnhancedQueryRewriter(security_context)
            rewritten_query, rewritten_params = rewriter.rewrite(request.query, rewritten_params)
        
        # Execute rewritten query
        result = user_kg.graph.query(rewritten_query, rewritten_params)
        
        # Convert result set
        results = []
        if result.result_set:
            for row in result.result_set:
                results.append(list(row))
        
        return {"query": rewritten_query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/clear", dependencies=[Depends(require_permission("rbac:admin"))])
async def clear_all_data():
    """
    Clear all data from the knowledge graph.
    
    ⚠️ This is a destructive operation and should be restricted in production.
    
    Clears both FalkorDB and Graphiti data.
    """
    try:
        result = await kg.clear_all_data()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== RBAC Management Endpoints ==========

class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_superuser: bool = False


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class RoleAssignmentRequest(BaseModel):
    username: str
    role_name: str


@app.get("/admin/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    """
    List all users with their roles and permissions.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        query = """
        MATCH (u:User)
        OPTIONAL MATCH (u)-[:HAS_ROLE]->(r:Role)
        OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(p:Permission)
        RETURN u.username as username,
               u.full_name as full_name,
               u.email as email,
               u.is_superuser as is_superuser,
               u.is_active as is_active,
               u.created_at as created_at,
               collect(DISTINCT r.name) as roles,
               collect(DISTINCT p.name) as permissions
        ORDER BY u.username
        """
        result = rbac_graph.query(query)
        
        users = []
        for row in result.result_set:
            users.append({
                "username": row[0],
                "full_name": row[1],
                "email": row[2],
                "is_superuser": row[3],
                "is_active": row[4],
                "created_at": row[5],
                "roles": [r for r in row[6] if r],
                "permissions": [p for p in row[7] if p]
            })
        
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@app.get("/admin/roles")
async def list_roles(current_user: dict = Depends(get_current_user)):
    """
    List all roles with their permissions.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        query = """
        MATCH (r:Role)
        OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(p:Permission)
        RETURN r.name as name,
               r.description as description,
               collect(DISTINCT p.name) as permissions
        ORDER BY r.name
        """
        result = rbac_graph.query(query)
        
        roles = []
        for row in result.result_set:
            roles.append({
                "name": row[0],
                "description": row[1],
                "permissions": [p for p in row[2] if p]
            })
        
        return {"roles": roles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list roles: {str(e)}")


@app.get("/admin/permissions")
async def list_permissions(current_user: dict = Depends(get_current_user)):
    """
    List all available permissions.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        query = """
        MATCH (p:Permission)
        RETURN p.name as name,
               p.description as description,
               p.resource as resource,
               p.action as action,
               p.grant_type as grant_type,
               p.node_label as node_label,
               p.edge_type as edge_type,
               p.property_name as property_name,
               p.property_filter as property_filter,
               p.attribute_conditions as attribute_conditions
        ORDER BY p.name
        """
        result = rbac_graph.query(query)
        
        permissions = []
        for row in result.result_set:
            permissions.append({
                "name": row[0],
                "description": row[1],
                "resource": row[2],
                "action": row[3],
                "grant_type": row[4],
                "node_label": row[5],
                "edge_type": row[6],
                "property_name": row[7],
                "property_filter": row[8],
                "attribute_conditions": row[9]
            })
        
        return {"permissions": permissions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list permissions: {str(e)}")


@app.post("/admin/users")
async def create_user(
    request: UserCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new user.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        from src.security.auth import hash_password
        from datetime import datetime
        
        # Check if user already exists
        check_query = "MATCH (u:User {username: $username}) RETURN u"
        result = rbac_graph.query(check_query, {'username': request.username})
        if result.result_set:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create user
        password_hash = hash_password(request.password)
        create_query = """
        CREATE (u:User {
            username: $username,
            password_hash: $password_hash,
            full_name: $full_name,
            email: $email,
            is_superuser: $is_superuser,
            is_active: true,
            created_at: $created_at
        })
        RETURN u.username as username
        """
        
        result = rbac_graph.query(create_query, {
            'username': request.username,
            'password_hash': password_hash,
            'full_name': request.full_name,
            'email': request.email,
            'is_superuser': request.is_superuser,
            'created_at': datetime.now().isoformat()
        })
        
        return {
            "status": "success",
            "message": f"User '{request.username}' created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@app.put("/admin/users/{username}")
async def update_user(
    username: str,
    request: UserUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user information.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        # Build update query dynamically based on provided fields
        updates = []
        params = {'username': username}
        
        if request.full_name is not None:
            updates.append("u.full_name = $full_name")
            params['full_name'] = request.full_name
        
        if request.email is not None:
            updates.append("u.email = $email")
            params['email'] = request.email
        
        if request.is_active is not None:
            updates.append("u.is_active = $is_active")
            params['is_active'] = request.is_active
        
        if request.is_superuser is not None:
            updates.append("u.is_superuser = $is_superuser")
            params['is_superuser'] = request.is_superuser
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_query = f"""
        MATCH (u:User {{username: $username}})
        SET {', '.join(updates)}
        RETURN u.username as username
        """
        
        result = rbac_graph.query(update_query, params)
        
        if not result.result_set:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "status": "success",
            "message": f"User '{username}' updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")


@app.post("/admin/users/{username}/roles")
async def assign_role(
    username: str,
    request: RoleAssignmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Assign a role to a user.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        # Check if relationship already exists
        check_query = """
        MATCH (u:User {username: $username})-[rel:HAS_ROLE]->(r:Role {name: $role_name})
        RETURN rel
        """
        result = rbac_graph.query(check_query, {
            'username': username,
            'role_name': request.role_name
        })
        
        if result.result_set:
            raise HTTPException(status_code=400, detail="User already has this role")
        
        # Create relationship
        assign_query = """
        MATCH (u:User {username: $username})
        MATCH (r:Role {name: $role_name})
        CREATE (u)-[:HAS_ROLE]->(r)
        RETURN u.username as username, r.name as role
        """
        
        result = rbac_graph.query(assign_query, {
            'username': username,
            'role_name': request.role_name
        })
        
        if not result.result_set:
            raise HTTPException(status_code=404, detail="User or role not found")
        
        return {
            "status": "success",
            "message": f"Role '{request.role_name}' assigned to user '{username}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign role: {str(e)}")


@app.delete("/admin/users/{username}/roles/{role_name}")
async def remove_role(
    username: str,
    role_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a role from a user.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        remove_query = """
        MATCH (u:User {username: $username})-[rel:HAS_ROLE]->(r:Role {name: $role_name})
        DELETE rel
        RETURN u.username as username, r.name as role
        """
        
        result = rbac_graph.query(remove_query, {
            'username': username,
            'role_name': role_name
        })
        
        if not result.result_set:
            raise HTTPException(status_code=404, detail="User, role, or assignment not found")
        
        return {
            "status": "success",
            "message": f"Role '{role_name}' removed from user '{username}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove role: {str(e)}")


@app.delete("/admin/users/{username}")
async def delete_user(
    username: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a user.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    # Prevent deleting yourself
    if username == current_user.get('sub'):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    try:
        delete_query = """
        MATCH (u:User {username: $username})
        DETACH DELETE u
        RETURN count(u) as deleted
        """
        
        result = rbac_graph.query(delete_query, {'username': username})
        
        if not result.result_set or result.result_set[0][0] == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "status": "success",
            "message": f"User '{username}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


# ========== Role Management Endpoints ==========

class RoleCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []


class RoleUpdateRequest(BaseModel):
    description: Optional[str] = None


@app.post("/admin/roles")
async def create_role(
    request: RoleCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new role.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        from datetime import datetime
        
        # Check if role already exists
        check_query = "MATCH (r:Role {name: $name}) RETURN r"
        result = rbac_graph.query(check_query, {'name': request.name})
        if result.result_set:
            raise HTTPException(status_code=400, detail="Role already exists")
        
        # Create role
        create_query = """
        CREATE (r:Role {
            name: $name,
            description: $description,
            is_system: false,
            created_at: $created_at
        })
        RETURN id(r) as id
        """
        
        result = rbac_graph.query(create_query, {
            'name': request.name,
            'description': request.description,
            'created_at': datetime.now().isoformat()
        })
        
        role_id = result.result_set[0][0] if result.result_set else None
        
        # Assign permissions to role
        for perm_name in request.permissions:
            link_query = """
            MATCH (r:Role), (p:Permission {name: $perm_name})
            WHERE id(r) = $role_id
            MERGE (r)-[:HAS_PERMISSION]->(p)
            """
            rbac_graph.query(link_query, {
                'role_id': role_id,
                'perm_name': perm_name
            })
        
        return {
            "status": "success",
            "message": f"Role '{request.name}' created successfully with {len(request.permissions)} permissions"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create role: {str(e)}")


@app.put("/admin/roles/{role_name}")
async def update_role(
    role_name: str,
    request: RoleUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update role information.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        # Check if role is system role
        check_query = "MATCH (r:Role {name: $name}) RETURN r.is_system as is_system"
        result = rbac_graph.query(check_query, {'name': role_name})
        
        if not result.result_set:
            raise HTTPException(status_code=404, detail="Role not found")
        
        is_system = result.result_set[0][0]
        if is_system:
            raise HTTPException(status_code=400, detail="Cannot modify system roles")
        
        # Update role
        update_query = """
        MATCH (r:Role {name: $name})
        SET r.description = $description
        RETURN r.name as name
        """
        
        result = rbac_graph.query(update_query, {
            'name': role_name,
            'description': request.description
        })
        
        return {
            "status": "success",
            "message": f"Role '{role_name}' updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update role: {str(e)}")


@app.post("/admin/roles/{role_name}/permissions")
async def assign_permission_to_role(
    role_name: str,
    permission_name: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Assign a permission to a role.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        # Check if relationship already exists
        check_query = """
        MATCH (r:Role {name: $role_name})-[rel:HAS_PERMISSION]->(p:Permission {name: $permission_name})
        RETURN rel
        """
        result = rbac_graph.query(check_query, {
            'role_name': role_name,
            'permission_name': permission_name
        })
        
        if result.result_set:
            raise HTTPException(status_code=400, detail="Role already has this permission")
        
        # Create relationship
        assign_query = """
        MATCH (r:Role {name: $role_name})
        MATCH (p:Permission {name: $permission_name})
        CREATE (r)-[:HAS_PERMISSION]->(p)
        RETURN r.name as role, p.name as permission
        """
        
        result = rbac_graph.query(assign_query, {
            'role_name': role_name,
            'permission_name': permission_name
        })
        
        if not result.result_set:
            raise HTTPException(status_code=404, detail="Role or permission not found")
        
        return {
            "status": "success",
            "message": f"Permission '{permission_name}' assigned to role '{role_name}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign permission: {str(e)}")


@app.delete("/admin/roles/{role_name}/permissions/{permission_name}")
async def remove_permission_from_role(
    role_name: str,
    permission_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a permission from a role.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        remove_query = """
        MATCH (r:Role {name: $role_name})-[rel:HAS_PERMISSION]->(p:Permission {name: $permission_name})
        DELETE rel
        RETURN r.name as role, p.name as permission
        """
        
        result = rbac_graph.query(remove_query, {
            'role_name': role_name,
            'permission_name': permission_name
        })
        
        if not result.result_set:
            raise HTTPException(status_code=404, detail="Role, permission, or assignment not found")
        
        return {
            "status": "success",
            "message": f"Permission '{permission_name}' removed from role '{role_name}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove permission: {str(e)}")


@app.delete("/admin/roles/{role_name}")
async def delete_role(
    role_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a role.
    Requires superuser access. Cannot delete system roles.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        # Check if role is system role
        check_query = "MATCH (r:Role {name: $name}) RETURN r.is_system as is_system"
        result = rbac_graph.query(check_query, {'name': role_name})
        
        if not result.result_set:
            raise HTTPException(status_code=404, detail="Role not found")
        
        is_system = result.result_set[0][0]
        if is_system:
            raise HTTPException(status_code=400, detail="Cannot delete system roles")
        
        # Delete role
        delete_query = """
        MATCH (r:Role {name: $name})
        DETACH DELETE r
        RETURN count(r) as deleted
        """
        
        result = rbac_graph.query(delete_query, {'name': role_name})
        
        return {
            "status": "success",
            "message": f"Role '{role_name}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete role: {str(e)}")


# ========== Permission Management Endpoints ==========

class PermissionCreateRequest(BaseModel):
    name: str
    resource: str
    action: str
    description: Optional[str] = None
    grant_type: str = "GRANT"
    node_label: Optional[str] = None
    edge_type: Optional[str] = None
    property_name: Optional[str] = None
    property_filter: Optional[str] = None
    attribute_conditions: Optional[str] = None


class PermissionUpdateRequest(BaseModel):
    description: Optional[str] = None
    grant_type: Optional[str] = None
    node_label: Optional[str] = None
    edge_type: Optional[str] = None
    property_name: Optional[str] = None
    property_filter: Optional[str] = None
    attribute_conditions: Optional[str] = None


@app.post("/admin/permissions")
async def create_permission(
    request: PermissionCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new permission.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        from datetime import datetime
        
        # Check if permission already exists
        check_query = "MATCH (p:Permission {name: $name}) RETURN p"
        result = rbac_graph.query(check_query, {'name': request.name})
        if result.result_set:
            raise HTTPException(status_code=400, detail="Permission already exists")
        
        # Create permission
        create_query = """
        CREATE (p:Permission {
            name: $name,
            resource: $resource,
            action: $action,
            description: $description,
            grant_type: $grant_type,
            node_label: $node_label,
            edge_type: $edge_type,
            property_name: $property_name,
            property_filter: $property_filter,
            attribute_conditions: $attribute_conditions,
            created_at: $created_at
        })
        RETURN p.name as name
        """
        
        result = rbac_graph.query(create_query, {
            'name': request.name,
            'resource': request.resource,
            'action': request.action,
            'description': request.description,
            'grant_type': request.grant_type,
            'node_label': request.node_label,
            'edge_type': request.edge_type,
            'property_name': request.property_name,
            'property_filter': request.property_filter,
            'attribute_conditions': request.attribute_conditions,
            'created_at': datetime.now().isoformat()
        })
        
        return {
            "status": "success",
            "message": f"Permission '{request.name}' created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create permission: {str(e)}")


@app.put("/admin/permissions/{permission_name}")
async def update_permission(
    permission_name: str,
    request: PermissionUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update permission information.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        # Build update query dynamically
        updates = []
        params = {'name': permission_name}
        
        if request.description is not None:
            updates.append("p.description = $description")
            params['description'] = request.description
        
        if request.grant_type is not None:
            updates.append("p.grant_type = $grant_type")
            params['grant_type'] = request.grant_type
        
        if request.node_label is not None:
            updates.append("p.node_label = $node_label")
            params['node_label'] = request.node_label
        
        if request.edge_type is not None:
            updates.append("p.edge_type = $edge_type")
            params['edge_type'] = request.edge_type
        
        if request.property_name is not None:
            updates.append("p.property_name = $property_name")
            params['property_name'] = request.property_name
        
        if request.property_filter is not None:
            updates.append("p.property_filter = $property_filter")
            params['property_filter'] = request.property_filter
        
        if request.attribute_conditions is not None:
            updates.append("p.attribute_conditions = $attribute_conditions")
            params['attribute_conditions'] = request.attribute_conditions
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_query = f"""
        MATCH (p:Permission {{name: $name}})
        SET {', '.join(updates)}
        RETURN p.name as name
        """
        
        result = rbac_graph.query(update_query, params)
        
        if not result.result_set:
            raise HTTPException(status_code=404, detail="Permission not found")
        
        return {
            "status": "success",
            "message": f"Permission '{permission_name}' updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update permission: {str(e)}")


@app.delete("/admin/permissions/{permission_name}")
async def delete_permission(
    permission_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a permission.
    Requires superuser access.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        delete_query = """
        MATCH (p:Permission {name: $name})
        DETACH DELETE p
        RETURN count(p) as deleted
        """
        
        result = rbac_graph.query(delete_query, {'name': permission_name})
        
        if not result.result_set or result.result_set[0][0] == 0:
            raise HTTPException(status_code=404, detail="Permission not found")
        
        return {
            "status": "success",
            "message": f"Permission '{permission_name}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete permission: {str(e)}")


@app.get("/admin/schema-metadata")
async def get_schema_metadata(
    current_user: dict = Depends(get_current_user)
):
    """
    Get schema metadata for admin panel dropdowns.
    Returns available node labels, edge types, and properties.
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    try:
        # Get all node labels from the application graph
        labels_query = "CALL db.labels()"
        labels_result = kg.graph.query(labels_query)
        
        node_labels = []
        if labels_result.result_set:
            node_labels = [row[0] for row in labels_result.result_set if row[0] not in ['User', 'Role', 'Permission']]
        
        # Get all relationship types
        rels_query = "CALL db.relationshipTypes()"
        rels_result = kg.graph.query(rels_query)
        
        edge_types = []
        if rels_result.result_set:
            edge_types = [row[0] for row in rels_result.result_set if row[0] not in ['HAS_ROLE', 'HAS_PERMISSION']]
        
        # Get properties from a sample of nodes (top 100 to avoid performance issues)
        props_query = """
        MATCH (n)
        WHERE NOT n:User AND NOT n:Role AND NOT n:Permission
        WITH n LIMIT 100
        UNWIND keys(n) as key
        RETURN DISTINCT key
        ORDER BY key
        """
        props_result = kg.graph.query(props_query)
        
        properties = []
        if props_result.result_set:
            properties = [row[0] for row in props_result.result_set]
        
        return {
            "node_labels": sorted(node_labels),
            "edge_types": sorted(edge_types),
            "properties": sorted(properties)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch schema metadata: {str(e)}")


# ========== Startup/Shutdown Events ==========

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    print("🚀 Tijara Knowledge Graph API (ORM) starting...")
    health = kg.health_check()
    if health['overall']:
        print("✅ All systems operational")
    else:
        print("⚠️  Some systems are not ready:", health)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("👋 Tijara Knowledge Graph API (ORM) shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config['api']['host'],
        port=config['api']['port'],
        reload=config['api']['reload']
    )
