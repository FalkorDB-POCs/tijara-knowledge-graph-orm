"""
Tijara Knowledge Graph API
FastAPI application providing REST API for the knowledge graph
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import yaml
import os

from src.core.knowledge_graph import TijaraKnowledgeGraph

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Set OpenAI API key from config if available
if 'openai' in config and 'api_key' in config['openai']:
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

# Initialize knowledge graph (singleton)
kg = TijaraKnowledgeGraph(config)

# Mount static files for web interface
web_dir = os.path.join(os.path.dirname(__file__), '..', 'web')
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=os.path.join(web_dir, "static")), name="static")


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
async def query_natural_language(request: QueryRequest):
    """
    Answer natural language questions using GraphRAG.
    
    Example:
    ```json
    {
        "question": "What are the relevant information on the demand of corn in Germany?",
        "return_sources": true
    }
    ```
    """
    try:
        result = await kg.query_natural_language(
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


@app.post("/ingest")
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


@app.post("/ingest/document")
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


@app.post("/analytics")
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


@app.post("/impact")
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
async def execute_cypher(request: CypherRequest):
    """
    Execute raw Cypher query.
    
    ⚠️ This endpoint should be restricted in production.
    
    Example:
    ```json
    {
        "query": "MATCH (n:Production) RETURN n LIMIT 10",
        "parameters": {}
    }
    ```
    """
    try:
        results = kg.falkordb.execute_query(request.query)
        return {"query": request.query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/clear")
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
