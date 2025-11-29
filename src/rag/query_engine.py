"""
Query Engine for natural language processing with GraphRAG
"""

from typing import Dict, Any, Optional, List
import logging
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain.chat_models import ChatOpenAI
try:
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    from langchain.prompts import ChatPromptTemplate

from ..repositories import (
    CommodityRepository,
    GeographyRepository,
    BalanceSheetRepository,
    ProductionAreaRepository
)

logger = logging.getLogger(__name__)


class QueryEngine:
    """Engine for processing natural language queries using GraphRAG."""
    
    def __init__(self, falkordb, graphiti, config: Dict[str, Any]):
        """Initialize query engine."""
        self.falkordb = falkordb
        self.graphiti = graphiti
        self.config = config
        
        # Use ORM repositories from parent KnowledgeGraph (these are already security-aware)
        # This ensures QueryEngine respects data-level filtering
        self.commodity_repo = falkordb.commodity_repo
        self.geography_repo = falkordb.geography_repo
        self.balance_sheet_repo = falkordb.balance_sheet_repo
        # production_area_repo may not exist in all deployments
        self.production_area_repo = getattr(falkordb, 'production_area_repo', None)
        
        # Initialize LLM (optional - requires API key)
        try:
            import os
            if os.environ.get('OPENAI_API_KEY') or config.get('openai_api_key'):
                self.llm = ChatOpenAI(
                    model=config.get('model', 'gpt-4-turbo-preview'),
                    temperature=config.get('temperature', 0.1),
                    api_key=config.get('openai_api_key')
                )
            else:
                logger.warning("OpenAI API key not found. LLM features will be disabled.")
                self.llm = None
        except Exception as e:
            logger.warning(f"Could not initialize LLM: {e}. LLM features will be disabled.")
            self.llm = None
        
        # Define prompts
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an AI assistant for LDC, a global commodity trading company.
You have access to a knowledge graph containing information about:
- Commodities (wheat, corn, soybean, etc.)
- Geographic regions and trade zones
- Supply and demand indicators
- Market prices and trade flows
- Weather and crop conditions

Use the provided context from the knowledge graph to answer questions accurately.
If you don't have enough information, say so clearly.

Context:
{context}
"""),
            ("human", "{question}")
        ])
        
        logger.info("Query engine initialized")
    
    def _get_denied_entity_names(self, entity_label: str = 'Geography') -> List[str]:
        """Get list of denied entity names based on security filters."""
        denied_names = []
        
        # Check if security context exists and get row filters
        if not self.falkordb.security_context or self.falkordb.security_context.is_superuser:
            return []  # No filtering for superusers
        
        try:
            # Get row filters for the entity label
            row_filters = self.falkordb.security_context.get_row_filters(entity_label, 'read')
            
            # Parse filters to extract denied entity names
            # Format: "NOT (name = 'France')" -> extract 'France'
            import re
            for filter_cond in row_filters:
                # Match patterns like: NOT (name = 'EntityName') or NOT (g.name = 'EntityName')
                matches = re.findall(r"NOT\s*\([^=]+=\s*'([^']+)'\)", filter_cond, re.IGNORECASE)
                denied_names.extend(matches)
            
            if denied_names:
                logger.info(f"Denied entity names for {entity_label}: {denied_names}")
        except Exception as e:
            logger.warning(f"Failed to extract denied entity names: {e}")
        
        return denied_names
    
    def _filter_graphiti_results(self, results: List, denied_names: List[str]) -> List:
        """Filter Graphiti results to remove denied entities."""
        if not denied_names:
            return results
        
        filtered = []
        for result in results:
            # Check if result mentions any denied entity
            result_text = ''
            if hasattr(result, 'name'):
                result_text += str(getattr(result, 'name', '')) + ' '
            if hasattr(result, 'summary'):
                result_text += str(getattr(result, 'summary', '')) + ' '
            if hasattr(result, 'fact'):
                result_text += str(getattr(result, 'fact', '')) + ' '
            if hasattr(result, 'content'):
                result_text += str(getattr(result, 'content', '')) + ' '
            
            # Check if any denied name appears in the result text
            contains_denied = any(denied_name.lower() in result_text.lower() 
                                 for denied_name in denied_names)
            
            if not contains_denied:
                filtered.append(result)
            else:
                logger.debug(f"Filtered out Graphiti result mentioning denied entity")
        
        logger.info(f"Filtered Graphiti results: {len(results)} -> {len(filtered)}")
        return filtered
    
    def _filter_context_text(self, context_text: str, denied_names: List[str]) -> str:
        """Remove sentences mentioning denied entities from context text."""
        if not denied_names or not context_text:
            return context_text
        
        # Split into sentences
        import re
        sentences = re.split(r'(?<=[.!?])\s+', context_text)
        
        filtered_sentences = []
        for sentence in sentences:
            # Check if sentence mentions any denied entity
            contains_denied = any(denied_name.lower() in sentence.lower() 
                                 for denied_name in denied_names)
            if not contains_denied:
                filtered_sentences.append(sentence)
        
        filtered_text = ' '.join(filtered_sentences)
        logger.info(f"Filtered context text: {len(context_text)} -> {len(filtered_text)} chars")
        return filtered_text
    
    async def process_query(
        self,
        question: str,
        context: Dict[str, Any],
        return_sources: bool = True
    ) -> Dict[str, Any]:
        """Process a natural language query."""
        logger.info(f"Processing query: {question}")
        
        # Step 1: Extract entities using Graphiti if available
        graphiti_entities = []
        if self.graphiti and self.graphiti.is_ready():
            try:
                graphiti_entities = await self.graphiti.extract_entities_from_text(question)
                logger.info(f"Graphiti extracted {len(graphiti_entities)} entities")
            except Exception as e:
                logger.warning(f"Graphiti entity extraction failed: {e}")
        
        # Step 2: Also use simple keyword extraction as fallback
        keyword_entities = self._extract_entities(question)
        
        # Combine entities from both methods
        all_entities = keyword_entities.copy()
        for ge in graphiti_entities:
            if ge.get('name'):
                all_entities.append(ge['name'])
        all_entities = list(set(all_entities))  # Deduplicate
        
        # Get denied entity names for post-filtering
        denied_geography_names = self._get_denied_entity_names('Geography')
        
        # Step 3: First search using Graphiti for semantic results
        graphiti_results = []
        if self.graphiti and self.graphiti.is_ready():
            try:
                # Use Graphiti's semantic search to find relevant entities
                search_results = await self.graphiti.client.search(
                    query=question,
                    num_results=10
                )
                # Apply post-filtering to remove denied entities
                graphiti_results = self._filter_graphiti_results(search_results, denied_geography_names)
                logger.info(f"Graphiti search found {len(graphiti_results)} semantic matches (after filtering)")
            except Exception as e:
                logger.warning(f"Graphiti search failed: {e}")
        
        # Step 4: Search FalkorDB for relevant data using ORM repositories
        subgraph_data = []
        for entity in all_entities[:5]:  # Limit to top 5 entities
            try:
                # Query 1: Search for Geography nodes using ORM
                geographies = self.geography_repo.search_case_insensitive(entity, limit=3)
                if geographies:
                    logger.info(f"Found {len(geographies)} geography results for: {entity}")
                    for g in geographies:
                        subgraph_data.append({
                            "type": "Geography",
                            "name": g.name,
                            "labels": ["Geography"],
                            "code": g.gid_code
                        })
                
                # Query 2: Search for Commodity nodes using ORM
                commodities = self.commodity_repo.search_case_insensitive(entity, limit=3)
                if commodities:
                    logger.info(f"Found {len(commodities)} commodity results for: {entity}")
                    for c in commodities:
                        subgraph_data.append({
                            "type": "Commodity",
                            "name": c.name,
                            "labels": ["Commodity"]
                        })
                
                # Query 3: Search for trade flows
                # Use falkordb's execute_cypher which respects security context
                try:
                    cypher = """
                    MATCH (g1:Geography)-[t:TRADES_WITH]->(g2:Geography)
                    WHERE toLower(g1.name) CONTAINS toLower($search_term) OR toLower(g2.name) CONTAINS toLower($search_term)
                    RETURN g1.name as from, g2.name as to, t.commodity as commodity, t.flow_type as flow_type
                    LIMIT 5
                    """
                    # Use falkordb instance's method which applies security filtering
                    results = self.falkordb.execute_query(cypher, {'search_term': entity})
                    if results:
                        logger.info(f"Found {len(results)} trade flow results for: {entity}")
                        for row in results:
                            # Extract values from result row dict
                            subgraph_data.append({
                                "type": "TradeFlow",
                                "from": row.get('from'),
                                "to": row.get('to'),
                                "commodity": row.get('commodity'),
                                "flow_type": row.get('flow_type')
                            })
                except Exception as e:
                    logger.warning(f"Trade flow search failed: {e}")
                
                # Query 4: Search for production areas using ORM (if available)
                if self.production_area_repo:
                    production_areas = self.production_area_repo.search_case_insensitive(entity, limit=3)
                    if production_areas:
                        logger.info(f"Found {len(production_areas)} production area results for: {entity}")
                        for pa in production_areas:
                            # Get commodity info via relationship
                            subgraph_data.append({
                                "type": "ProductionArea",
                                "area_name": pa.name,
                                "commodity": "N/A"  # Would need to eager load relationship
                            })
                
                # Query 5: Search for balance sheets using ORM
                balance_sheets = self.balance_sheet_repo.search_case_insensitive(entity, limit=3)
                if balance_sheets:
                    logger.info(f"Found {len(balance_sheets)} balance sheet results for: {entity}")
                    for bs in balance_sheets:
                        subgraph_data.append({
                            "type": "BalanceSheet",
                            "id": bs.balance_sheet_id,
                            "commodity": "N/A",  # Would need to eager load relationship
                            "geography": "N/A"   # Would need to eager load relationship
                        })
                
            except Exception as e:
                logger.warning(f"FalkorDB search for '{entity}' failed: {e}")
            
            # Stop if we have enough results
            if len(subgraph_data) >= 25:
                break
        
        # Step 5: Use Graphiti to retrieve semantic context (additional context)
        graph_context = {'context': '', 'sources': []}
        if self.graphiti and self.graphiti.is_ready():
            try:
                graph_context = await self.graphiti.build_context(
                    query=question,
                    max_context_items=self.config.get('retrieval_top_k', 10)
                )
                
                # Apply post-filtering to context text to remove denied entity mentions
                if 'context' in graph_context and graph_context['context']:
                    graph_context['context'] = self._filter_context_text(
                        graph_context['context'], 
                        denied_geography_names
                    )
                
                # Ensure graph_context has sources array
                if 'sources' not in graph_context:
                    graph_context['sources'] = []
                
                # Process sources from build_context - these come from semantic_search
                # Each source has: entity_id, content, score, metadata
                existing_sources = graph_context.get('sources', [])
                for source in existing_sources:
                    # Extract metadata to identify source type and name
                    metadata = source.get('metadata', {})
                    content = source.get('content', '')
                    
                    # Format source entry for confidence calculation and display
                    formatted_source = {
                        'type': 'graphiti_episodic',
                        'entity_id': source.get('entity_id', 'unknown'),
                        'name': metadata.get('source', 'Knowledge Graph'),
                        'content': content[:200] if len(content) > 200 else content,  # Truncate for display
                        'relevance_score': source.get('score', 0.0)
                    }
                    # Replace with formatted version
                    graph_context['sources'][existing_sources.index(source)] = formatted_source
                
                # Also add search results from step 3 if they're not already in sources
                for result in graphiti_results:
                    # Check if this result is already in sources
                    result_id = str(getattr(result, 'uuid', getattr(result, 'id', '')))
                    if not any(s.get('entity_id') == result_id for s in graph_context['sources']):
                        # Extract information from search result
                        source_entry = {
                            'type': 'graphiti_search',
                            'entity_id': result_id,
                            'name': getattr(result, 'name', 'Entity') or 'Semantic Match',
                            'content': str(getattr(result, 'fact', getattr(result, 'summary', getattr(result, 'content', 'Relevant context'))))[:200],
                            'relevance_score': getattr(result, 'score', 0.0)
                        }
                        # Only add if we have meaningful content
                        if source_entry['content'] and len(source_entry['content']) > 10:
                            graph_context['sources'].append(source_entry)
                
                logger.info(f"Built context with {len(graph_context.get('context', ''))} chars and {len(graph_context['sources'])} sources")
                logger.info(f"Sources breakdown: {[s.get('type') for s in graph_context['sources']]}")
            except Exception as e:
                logger.warning(f"Graphiti context building failed: {e}")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")
        
        # Step 6: Generate answer using LLM if available
        if self.llm:
            try:
                # Build final context including Graphiti results
                full_context = self._build_final_context(
                    graphiti_context=graph_context['context'],
                    subgraph_data=subgraph_data,
                    graphiti_results=graphiti_results
                )
                
                # Generate answer
                prompt = self.prompt_template.format_messages(
                    context=full_context,
                    question=question
                )
                
                response = await self.llm.agenerate([prompt])
                answer = response.generations[0][0].text
                
                result = {
                    'answer': answer,
                    'confidence': self._calculate_confidence(graph_context, subgraph_data)
                }
                
                if return_sources:
                    result['sources'] = graph_context['sources']
                    result['entities'] = all_entities
                    result['subgraph'] = subgraph_data
                
                return result
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}")
        
        # Fallback: Return structured data without LLM
        answer = self._generate_basic_answer(question, all_entities, subgraph_data)
        
        result = {
            'answer': answer,
            'confidence': 0.6 if subgraph_data else 0.2
        }
        
        if return_sources:
            result['sources'] = graph_context.get('sources', [])
            result['entities'] = all_entities
            result['subgraph'] = subgraph_data
        
        return result
    
    def _extract_entities(self, question: str) -> List[str]:
        """Extract entity mentions from question."""
        # Simple keyword extraction - enhanced for LDC graph
        keywords = []
        question_lower = question.lower()
        
        # LDC Commodities (from actual graph data)
        commodities = [
            'wheat', 'corn', 'soybean', 'barley', 'sorghum', 'rice', 
            'durum wheat', 'common wheat', 'hard red wheat', 'soft red wheat',
            'yellow corn', 'white corn', 'dried distillers grains',
            'chickpeas', 'lentils', 'peas', 'pulses', 'redgram',
            'flour', 'cotton', 'coffee'
        ]
        for commodity in commodities:
            if commodity in question_lower:
                keywords.append(commodity)
        
        # Geographies (LDC focus: France and USA)
        geographies = [
            'france', 'usa', 'united states', 'us', 'america',
            'picardie', 'normandy', 'brittany', 'ile-de-france',  # French regions
            'iowa', 'illinois', 'nebraska', 'kansas', 'texas'  # US states
        ]
        for geo in geographies:
            if geo in question_lower:
                keywords.append(geo)
        
        # Trade and flow keywords
        trade_keywords = ['export', 'import', 'trade', 'flow', 'ship']
        for keyword in trade_keywords:
            if keyword in question_lower:
                keywords.append(keyword)
        
        # Production and supply keywords
        supply_keywords = ['production', 'produce', 'supply', 'harvest', 'yield', 'area']
        for keyword in supply_keywords:
            if keyword in question_lower:
                keywords.append(keyword)
        
        # Balance sheet and component keywords
        balance_keywords = ['balance', 'sheet', 'carry', 'stock', 'inventory']
        for keyword in balance_keywords:
            if keyword in question_lower:
                keywords.append(keyword)
        
        # Weather indicator keywords
        weather_keywords = ['weather', 'temperature', 'precipitation', 'rain', 'drought']
        for keyword in weather_keywords:
            if keyword in question_lower:
                keywords.append(keyword)
        
        return list(set(keywords))
    
    def _build_final_context(
        self,
        graphiti_context: str,
        subgraph_data: List[Dict],
        graphiti_results: List[Any] = None
    ) -> str:
        """Build final context for LLM including Graphiti search results."""
        parts = []
        
        # Add Graphiti search results first (most relevant semantic matches)
        if graphiti_results:
            parts.append("📊 Semantic Search Results (from documents and episodic data):")
            for result in graphiti_results[:5]:  # Top 5 semantic matches
                fact = getattr(result, 'fact', getattr(result, 'summary', 'No description'))
                if fact:
                    parts.append(f"- {fact}")
            parts.append("")
        
        # Add Graphiti semantic context
        if graphiti_context:
            parts.append("📖 Additional Context:")
            parts.append(graphiti_context)
            parts.append("")
        
        # Add structured data from graph
        if subgraph_data:
            parts.append("📈 Structured Data Points:")
            for item in subgraph_data[:5]:  # Limit to top 5
                parts.append(f"- {item}")
            parts.append("")
        
        return "\n".join(parts)
    
    def _calculate_confidence(
        self,
        graph_context: Dict[str, Any],
        subgraph_data: List[Dict]
    ) -> float:
        """Calculate confidence score for the answer."""
        # Enhanced scoring based on available context quality
        score = 0.0
        
        # 1. Graphiti semantic context (0-0.4 points)
        if graph_context.get('context'):
            context_length = len(graph_context['context'])
            if context_length > 500:
                score += 0.4  # Rich semantic context
            elif context_length > 200:
                score += 0.3  # Moderate context
            elif context_length > 0:
                score += 0.2  # Some context
        
        # 2. Structured data from FalkorDB (0-0.4 points)
        if subgraph_data:
            data_count = len(subgraph_data)
            if data_count >= 15:
                score += 0.4  # Many data points
            elif data_count >= 10:
                score += 0.3  # Good amount of data
            elif data_count >= 5:
                score += 0.2  # Some data
            else:
                score += 0.1  # Minimal data
        
        # 3. Source diversity bonus (0-0.2 points)
        sources_count = len(graph_context.get('sources', []))
        if sources_count >= 5:
            score += 0.2  # Excellent source diversity
        elif sources_count >= 3:
            score += 0.15  # Good source diversity
        elif sources_count >= 1:
            score += 0.1  # Some sources
        
        return min(score, 1.0)
    
    def _generate_basic_answer(
        self,
        question: str,
        entities: List[str],
        subgraph_data: List[Dict]
    ) -> str:
        """Generate a basic answer without LLM based on retrieved data."""
        if not subgraph_data:
            return f"I found references to {', '.join(entities) if entities else 'the query'}, but no specific data is available in the knowledge graph. Please try refining your question or check if the data has been ingested."
        
        # Build a simple structured answer
        answer_parts = []
        answer_parts.append(f"Based on the available data about {', '.join(entities) if entities else 'your query'}:")
        answer_parts.append("")
        
        # Group data by indicator type
        data_by_type = {}
        for item in subgraph_data[:20]:  # Limit to 20 items
            # Data is now returned as flat dictionaries with field names
            indicator = item.get('n.indicator_type', 'data')
            if indicator not in data_by_type:
                data_by_type[indicator] = []
            data_by_type[indicator].append(item)
        
        # Format each type
        for indicator, items in data_by_type.items():
            if indicator and indicator != 'None':
                answer_parts.append(f"**{indicator}:**")
                for item in items[:5]:  # Top 5 per type
                    commodity = item.get('n.commodity', 'N/A')
                    country = item.get('n.country', item.get('n.region', 'N/A'))
                    value = item.get('n.value')
                    year = item.get('n.year')
                    month = item.get('n.month', '')
                    unit = item.get('n.unit', '')
                    
                    if value is not None and year:
                        time_str = f"{year}"
                        if month:
                            time_str = f"{month}/{year}"
                        answer_parts.append(f"  - {commodity} in {country}: {value} {unit} ({time_str})")
                answer_parts.append("")
        
        answer_parts.append(f"\nFound {len(subgraph_data)} total data points. For more detailed analysis, please ensure OpenAI API key is configured for LLM-powered insights.")
        
        return "\n".join(answer_parts)
