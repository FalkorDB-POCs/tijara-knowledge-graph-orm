// Tijara Knowledge Graph - Web Interface JavaScript

// Configuration
let API_BASE_URL = localStorage.getItem('apiBaseUrl') || 'http://localhost:8080';

// Utility Functions
const $ = (id) => document.getElementById(id);
const $$ = (selector) => document.querySelectorAll(selector);

function showToast(message, type = 'success') {
    const container = $('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? 'fa-check-circle' : 
                 type === 'error' ? 'fa-exclamation-circle' : 
                 'fa-info-circle';
    
    toast.innerHTML = `
        <i class="fas ${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function showLoader(loaderId) {
    $(loaderId).style.display = 'flex';
}

function hideLoader(loaderId) {
    $(loaderId).style.display = 'none';
}

function showResult(resultId) {
    $(resultId).style.display = 'block';
}

function hideResult(resultId) {
    $(resultId).style.display = 'none';
}

async function apiCall(endpoint, options = {}) {
    try {
        const headers = { ...(options.headers || {}) };
        // Only set Content-Type for non-GET requests to avoid unnecessary CORS preflight
        const method = (options.method || 'GET').toUpperCase();
        if (method !== 'GET' && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Navigation
function initNavigation() {
    $$('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tabName = item.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Update nav items
    $$('.nav-item').forEach(item => item.classList.remove('active'));
    $$(`.nav-item[data-tab="${tabName}"]`).forEach(item => item.classList.add('active'));
    
    // Update tab content
    $$('.tab-content').forEach(tab => tab.classList.remove('active'));
    $(tabName).classList.add('active');
    
    // Load data for specific tabs
    if (tabName === 'schema') {
        loadSchema();
    } else if (tabName === 'stats') {
        loadStatistics();
    }
}

// Health Check
async function checkHealth() {
    try {
        const data = await apiCall('/health');
        console.log('Health check response:', data);
        
        // Update FalkorDB status
        const falkordbDot = $('falkordbDot');
        const falkordbText = $('falkordbText');
        console.log('FalkorDB element:', falkordbDot, 'Status:', data.falkordb);
        if (data.falkordb) {
            falkordbDot.classList.add('online');
            falkordbDot.classList.remove('offline');
            falkordbText.textContent = 'FalkorDB (ORM)';
        } else {
            falkordbDot.classList.add('offline');
            falkordbDot.classList.remove('online');
            falkordbText.textContent = 'FalkorDB (ORM - Offline)';
        }
        
        // Update Graphiti status
        const graphitiDot = $('graphitiDot');
        const graphitiText = $('graphitiText');
        console.log('Graphiti element:', graphitiDot, 'Status:', data.graphiti);
        if (data.graphiti) {
            graphitiDot.classList.add('online');
            graphitiDot.classList.remove('offline');
            graphitiText.textContent = 'Graphiti';
        } else {
            graphitiDot.classList.add('offline');
            graphitiDot.classList.remove('online');
            graphitiText.textContent = 'Graphiti (Offline)';
        }
    } catch (error) {
        // Mark both as offline on error
        const falkordbDot = $('falkordbDot');
        const falkordbText = $('falkordbText');
        const graphitiDot = $('graphitiDot');
        const graphitiText = $('graphitiText');
        
        falkordbDot.classList.add('offline');
        falkordbDot.classList.remove('online');
        falkordbText.textContent = 'FalkorDB (ORM - Error)';
        
        graphitiDot.classList.add('offline');
        graphitiDot.classList.remove('online');
        graphitiText.textContent = 'Graphiti (Error)';
        
        console.error('Health check failed:', error);
    }
}

// Use Case 1: Trading Copilot
let chatHistory = [];

function initCopilot() {
    // Quick questions
    $$('.quick-question-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const question = btn.dataset.question;
            $('copilotQuery').value = question;
            askQuestion();
        });
    });
    
    // Ask button
    $('askBtn').addEventListener('click', askQuestion);
    
    // Clear chat button
    $('clearChatBtn').addEventListener('click', clearChat);
    
    // Enter key (without Ctrl sends message)
    $('copilotQuery').addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            askQuestion();
        }
    });
}

async function askQuestion() {
    const question = $('copilotQuery').value.trim();
    
    if (!question) {
        showToast('Please enter a question', 'warning');
        return;
    }
    
    const returnSources = $('returnSources').checked;
    
    // Add user message to chat
    addChatMessage('user', question);
    
    // Clear input
    $('copilotQuery').value = '';
    
    // Show loader
    showLoader('copilotLoader');
    
    try {
        const data = await apiCall('/query', {
            method: 'POST',
            body: JSON.stringify({
                question,
                return_sources: returnSources
            })
        });
        
        // Add assistant response to chat
        addChatMessage('assistant', data.answer, data);
        
        // Store in history
        chatHistory.push({
            question,
            answer: data.answer,
            confidence: data.confidence,
            sources: data.sources,
            entities: data.retrieved_entities,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        addChatMessage('error', `Error: ${error.message}`);
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        hideLoader('copilotLoader');
    }
}

function addChatMessage(type, content, metadata = null) {
    const messagesContainer = $('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    
    const timestamp = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    
    if (type === 'user') {
        messageDiv.innerHTML = `
            <i class="fas fa-user"></i>
            <div class="message-content">
                <div class="message-header">
                    <strong>You</strong>
                    <span class="message-time">${timestamp}</span>
                </div>
                <p>${content}</p>
            </div>
        `;
    } else if (type === 'assistant') {
        const returnSources = $('returnSources').checked;
        const confidence = metadata?.confidence || 0;
        const confidenceClass = confidence >= 0.7 ? 'high' : confidence >= 0.4 ? 'medium' : 'low';
        const confidenceBadge = `<span class="confidence-badge ${confidenceClass}">${(confidence * 100).toFixed(0)}%</span>`;
        
        let sourcesHtml = '';
        if (returnSources && metadata?.sources && metadata.sources.length > 0) {
            sourcesHtml = `
                <div class="message-sources" style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border-color);">
                    <h5 style="font-size: 0.875rem; margin-bottom: 0.5rem;"><i class="fas fa-link"></i> Sources (${metadata.sources.length})</h5>
                    <div style="font-size: 0.8rem; max-height: 150px; overflow-y: auto;">
                        ${metadata.sources.slice(0, 3).map((source, i) => `
                            <div style="margin-bottom: 0.5rem; padding: 0.5rem; background: var(--bg-secondary); border-radius: 4px;">
                                <strong>${i + 1}.</strong> ${source.type || 'Unknown'}
                                ${source.content ? `<div style="margin-top: 0.25rem; color: var(--text-secondary);">${source.content.substring(0, 100)}${source.content.length > 100 ? '...' : ''}</div>` : ''}
                            </div>
                        `).join('')}
                        ${metadata.sources.length > 3 ? `<div style="color: var(--text-secondary); font-size: 0.75rem;">... and ${metadata.sources.length - 3} more sources</div>` : ''}
                    </div>
                </div>
            `;
        }
        
        let entitiesHtml = '';
        if (metadata?.entities && metadata.entities.length > 0) {
            entitiesHtml = `
                <div class="message-entities" style="margin-top: 0.75rem;">
                    <h5 style="font-size: 0.875rem; margin-bottom: 0.5rem;"><i class="fas fa-tags"></i> Related Entities</h5>
                    <div style="display: flex; flex-wrap: wrap; gap: 0.25rem;">
                        ${metadata.entities.slice(0, 5).map(entity => `
                            <span class="tag" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;">${entity}</span>
                        `).join('')}
                        ${metadata.entities.length > 5 ? `<span class="tag" style="font-size: 0.75rem; padding: 0.25rem 0.5rem; opacity: 0.6;">+${metadata.entities.length - 5} more</span>` : ''}
                    </div>
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <i class="fas fa-robot"></i>
            <div class="message-content">
                <div class="message-header">
                    <strong>Trading Copilot</strong>
                    ${confidenceBadge}
                    <span class="message-time">${timestamp}</span>
                </div>
                <p>${content}</p>
                ${sourcesHtml}
                ${entitiesHtml}
            </div>
        `;
    } else if (type === 'error') {
        messageDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <div class="message-content">
                <div class="message-header">
                    <strong>Error</strong>
                    <span class="message-time">${timestamp}</span>
                </div>
                <p style="color: var(--danger-color);">${content}</p>
            </div>
        `;
    }
    
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function clearChat() {
    const messagesContainer = $('chatMessages');
    messagesContainer.innerHTML = `
        <div class="chat-message system-message">
            <i class="fas fa-robot"></i>
            <div class="message-content">
                <strong>Trading Copilot</strong>
                <p>Hello! I'm your LDC Trading Copilot. Ask me anything about commodities, markets, trade flows, or production data.</p>
            </div>
        </div>
    `;
    chatHistory = [];
    showToast('Chat conversation cleared', 'info');
}

// Use Case 2: Data Analytics
function initAnalytics() {
    $('runAnalyticsBtn').addEventListener('click', runAnalytics);
    $('extractBtn').addEventListener('click', extractData);
    $('exportAnalyticsBtn').addEventListener('click', () => exportToCSV('analyticsTable'));
    $('exportExtractBtn').addEventListener('click', () => exportToCSV('extractTable'));
    
    // Node ID Finder
    $('findNodesBtn').addEventListener('click', findNodes);
    $('copyNodeIdsBtn').addEventListener('click', copyNodeIds);
    
    // Algorithm selection change handler - update parameter template
    $('algorithmSelect').addEventListener('change', (e) => {
        const algorithm = e.target.value;
        const parametersTextarea = $('analyticsParameters');
        
        // Update placeholder with algorithm-specific example
        switch(algorithm) {
            case 'pagerank':
                parametersTextarea.placeholder = '{"node_label": "Geography", "relationship_type": "TRADES_WITH"}';
                parametersTextarea.value = JSON.stringify({
                    node_label: "Geography",
                    relationship_type: "TRADES_WITH"
                }, null, 2);
                break;
            case 'centrality':
                parametersTextarea.placeholder = '{"node_label": "Geography"}';
                parametersTextarea.value = JSON.stringify({
                    node_label: "Geography"
                }, null, 2);
                break;
            case 'community':
                parametersTextarea.placeholder = '{"relationship_type": "TRADES_WITH"}';
                parametersTextarea.value = JSON.stringify({
                    relationship_type: "TRADES_WITH"
                }, null, 2);
                break;
            case 'pathfinding':
                parametersTextarea.placeholder = '{"source": "123", "target": "456", "max_depth": 5, "relationship_type": "TRADES_WITH"}';
                // Pre-fill with template for pathfinding since it requires parameters
                parametersTextarea.value = JSON.stringify({
                    source: "123",
                    target: "456",
                    max_depth: 5,
                    relationship_type: "TRADES_WITH"
                }, null, 2);
                break;
        }
    });
    
    // Fill PageRank parameters button
    const fillPageRankBtn = $('fillPageRankParams');
    if (fillPageRankBtn) {
        fillPageRankBtn.addEventListener('click', () => {
            $('algorithmSelect').value = 'pagerank';
            $('analyticsParameters').value = JSON.stringify({
                node_label: "Geography",
                relationship_type: "TRADES_WITH"
            }, null, 2);
            showToast('Trade Network PageRank parameters filled!', 'info');
        });
    }
    
    // Quick analytics query buttons
    $$('.quick-analytics-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const query = btn.dataset.query;
            // Decode HTML entities
            const decodedQuery = query.replace(/&#10;/g, '\n');
            
            console.log('Running quick analytics query:', decodedQuery);
            
            hideResult('analyticsResult');
            showLoader('analyticsLoader');
            
            try {
                const data = await apiCall('/cypher', {
                    method: 'POST',
                    body: JSON.stringify({ query: decodedQuery })
                });
                
                console.log('Query response:', data);
                displayAnalyticsResults(data.results);
                showResult('analyticsResult');
                showToast('Analysis completed!');
            } catch (error) {
                console.error('Query error:', error);
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                hideLoader('analyticsLoader');
            }
        });
    });
}

async function runAnalytics() {
    const algorithm = $('algorithmSelect').value;
    const parametersText = $('analyticsParameters').value.trim();
    
    let parameters = null;
    if (parametersText) {
        try {
            parameters = JSON.parse(parametersText);
        } catch (error) {
            showToast('Invalid JSON in parameters', 'error');
            console.error('Parameters parsing error:', error);
            return;
        }
    }
    
    console.log('Running analytics:', { algorithm, parameters });
    
    hideResult('analyticsResult');
    showLoader('analyticsLoader');
    
    try {
        const data = await apiCall('/analytics', {
            method: 'POST',
            body: JSON.stringify({
                algorithm,
                filters: null,
                parameters
            })
        });
        
        console.log('Analytics response:', data);
        displayAnalyticsResults(data.results);
        showToast('Analysis completed successfully!');
    } catch (error) {
        console.error('Analytics error:', error);
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        hideLoader('analyticsLoader');
    }
}

function displayAnalyticsResults(results) {
    const table = $('analyticsTable');
    const thead = $('analyticsTableHead');
    const tbody = $('analyticsTableBody');
    
    if (!results || (Array.isArray(results) && results.length === 0) || (typeof results === 'object' && Object.keys(results).length === 0)) {
        tbody.innerHTML = '<tr><td colspan="100%">No results found</td></tr>';
        showResult('analyticsResult');
        return;
    }
    
    // Convert object results (e.g., PageRank) to array format
    let dataArray = results;
    if (!Array.isArray(results)) {
        dataArray = Object.entries(results).map(([key, value]) => ({
            node_id: key,
            score: typeof value === 'number' ? value.toFixed(6) : value
        }));
    }
    
    // Create header
    const keys = Object.keys(dataArray[0]);
    thead.innerHTML = `
        <tr>${keys.map(key => `<th>${key}</th>`).join('')}</tr>
    `;
    
    // Create rows
    tbody.innerHTML = dataArray.map(row => `
        <tr>${keys.map(key => `<td>${row[key]}</td>`).join('')}</tr>
    `).join('');
    
    showResult('analyticsResult');
}

async function extractData() {
    const entityType = $('entityTypeSelect').value;
    const dimensionsText = $('dimensionsInput').value.trim();
    const filtersText = $('extractFilters').value.trim();
    
    const dimensions = dimensionsText.split(',').map(d => d.trim()).filter(d => d);
    
    let filters = null;
    if (filtersText) {
        try {
            filters = JSON.parse(filtersText);
        } catch (error) {
            showToast('Invalid JSON in filters', 'error');
            return;
        }
    }
    
    hideResult('extractResult');
    showLoader('analyticsLoader');
    
    try {
        // Note: This would need a custom endpoint for extraction
        // For now, showing mock data
        const mockData = [
            { geography: 'USA', value: 354000000, unit: 'metric_ton', year: 2023 },
            { geography: 'Brazil', value: 125000000, unit: 'metric_ton', year: 2023 },
            { geography: 'Argentina', value: 55000000, unit: 'metric_ton', year: 2023 }
        ];
        
        displayExtractResults(mockData);
        showToast('Data extracted successfully!');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        hideLoader('analyticsLoader');
    }
}

function displayExtractResults(results) {
    const thead = $('extractTableHead');
    const tbody = $('extractTableBody');
    
    if (!results || results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="100%">No results found</td></tr>';
        showResult('extractResult');
        return;
    }
    
    const keys = Object.keys(results[0]);
    thead.innerHTML = `
        <tr>${keys.map(key => `<th>${key}</th>`).join('')}</tr>
    `;
    
    tbody.innerHTML = results.map(row => `
        <tr>${keys.map(key => `<td>${row[key]}</td>`).join('')}</tr>
    `).join('');
    
    showResult('extractResult');
}

// Node ID Finder for Pathfinding
async function findNodes() {
    const nodeType = $('nodeFinderType').value;
    const searchTerm = $('nodeFinderSearch').value.trim();
    const filtersText = $('nodeFinderFilters').value.trim();
    
    let filters = {};
    if (filtersText) {
        try {
            filters = JSON.parse(filtersText);
        } catch (error) {
            showToast('Invalid JSON in filters', 'error');
            return;
        }
    }
    
    hideResult('nodeFinderResult');
    showLoader('nodeFinderLoader');
    
    try {
        // Build Cypher query based on inputs
        let whereClause = '';
        const conditions = [];
        
        if (searchTerm) {
            conditions.push(`n.name CONTAINS '${searchTerm}'`);
        }
        
        Object.entries(filters).forEach(([key, value]) => {
            if (typeof value === 'string') {
                conditions.push(`n.${key} = '${value}'`);
            } else {
                conditions.push(`n.${key} = ${value}`);
            }
        });
        
        if (conditions.length > 0) {
            whereClause = 'WHERE ' + conditions.join(' AND ');
        }
        
        const labelClause = nodeType === 'all' ? '' : `:${nodeType}`;
        const query = `MATCH (n${labelClause}) ${whereClause} RETURN id(n) as node_id, n.name as name, labels(n) as labels, properties(n) as props LIMIT 100`;
        
        console.log('Node finder query:', query);
        
        const data = await apiCall('/cypher', {
            method: 'POST',
            body: JSON.stringify({ query })
        });
        
        if (data.results && data.results.length > 0) {
            displayNodeFinderResults(data.results);
            showToast(`Found ${data.results.length} nodes`);
        } else {
            displayNodeFinderResults([]);
            showToast('No nodes found', 'info');
        }
    } catch (error) {
        console.error('Node finder error:', error);
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        hideLoader('nodeFinderLoader');
    }
}

function displayNodeFinderResults(results) {
    const tbody = $('nodeFinderTableBody');
    
    if (!results || results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No nodes found. Try different search criteria.</td></tr>';
        showResult('nodeFinderResult');
        return;
    }
    
    tbody.innerHTML = results.map(row => {
        const nodeId = row.node_id;
        const name = row.name || 'N/A';
        const types = Array.isArray(row.labels) ? row.labels.join(', ') : row.labels || 'Unknown';
        const props = row.props ? JSON.stringify(row.props, null, 2) : '{}';
        
        return `
            <tr>
                <td><code>${nodeId}</code></td>
                <td>${name}</td>
                <td><span class="badge badge-primary">${types}</span></td>
                <td><pre style="max-height: 100px; overflow-y: auto; margin: 0; font-size: 0.75rem;">${props}</pre></td>
                <td>
                    <button class="btn btn-xs btn-secondary" onclick="copyToClipboard('${nodeId}')">
                        <i class="fas fa-copy"></i> Copy ID
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    showResult('nodeFinderResult');
}

function copyNodeIds() {
    const tbody = $('nodeFinderTableBody');
    const rows = tbody.querySelectorAll('tr');
    
    if (rows.length === 0 || (rows.length === 1 && rows[0].cells.length === 1)) {
        showToast('No nodes to copy', 'warning');
        return;
    }
    
    const nodeIds = [];
    rows.forEach(row => {
        const idCell = row.querySelector('code');
        if (idCell) {
            nodeIds.push(idCell.textContent);
        }
    });
    
    const idsText = nodeIds.join(', ');
    copyToClipboard(idsText);
    showToast(`Copied ${nodeIds.length} node IDs to clipboard!`);
}

function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showToast('Copied to clipboard!');
}

// Use Case 3: Data Ingestion
function initIngestion() {
    $('ingestBtn').addEventListener('click', ingestData);
    $('ingestDocumentBtn').addEventListener('click', ingestDocument);
    
    // LDC CSV format sample datasets
    const sampleDatasets = {
        commodity_hierarchy: {
            csv: `Level0,Level1,Level2,Level3
Grains,Wheat,Common Wheat,Hard Red Wheat
Grains,Wheat,Common Wheat,Soft Red Wheat
Grains,Wheat,Durum Wheat,
Grains,Corn,Yellow Corn,
Grains,Corn,White Corn,
Grains,Barley,,`,
            dataType: 'commodity_hierarchy'
        },
        trade_flows: {
            csv: `source_country,destination_country,commodity,commodity_season,source_country_ts_id,destination_country_ts_id
FRA,USA,Common Wheat,,12345,67890
USA,FRA,Yellow Corn,,12346,67891
FRA,USA,Durum Wheat,,12347,67892
USA,FRA,Peas,,12348,67893
FRA,USA,Barley,,12349,67894`,
            dataType: 'trade_flows'
        },
        balance_sheet: {
            csv: `id,gid,product_name,product_season
0,USA,Yellow Corn,
1,USA,Hard Red Wheat,Spring
2,USA,Soft Red Wheat,Winter
3,FRA,Common Wheat,
4,FRA,Durum Wheat,`,
            dataType: 'balance_sheet'
        },
        production_areas: {
            csv: `production_area_id,gid,commodity,commodity_season,area_ts_id
0,USA,Yellow Corn,,pa_001
1,USA,Hard Red Wheat,Spring,pa_002
2,FRA,Common Wheat,,pa_003
3,FRA,Durum Wheat,,pa_004`,
            dataType: 'production_areas'
        },
        geometries: {
            csv: `GID_0,NAME_0,Level,GID_1,NAME_1,GID_2,NAME_2
FRA,France,0,,,
FRA,France,1,FRA.1_1,Auvergne-Rhône-Alpes,,
FRA,France,1,FRA.2_1,Bourgogne-Franche-Comté,,
USA,United States,0,,,
USA,United States,1,USA.1_1,Alabama,,`,
            dataType: 'geometries'
        }
    };
    
    // Data type select change handler
    const dataTypeSelect = $('dataTypeSelect');
    const customMetadataGroup = $('customMetadataGroup');
    if (dataTypeSelect && customMetadataGroup) {
        dataTypeSelect.addEventListener('change', (e) => {
            if (e.target.value === 'custom') {
                customMetadataGroup.style.display = 'block';
            } else {
                customMetadataGroup.style.display = 'none';
            }
        });
    }
    
    // Sample data buttons
    $$('.sample-data-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const sampleKey = btn.dataset.sample;
            const sample = sampleDatasets[sampleKey];
            if (sample) {
                $('dataInput').value = sample.csv;
                if ($('dataTypeSelect')) {
                    $('dataTypeSelect').value = sample.dataType;
                    // Trigger change event to hide custom metadata if needed
                    $('dataTypeSelect').dispatchEvent(new Event('change'));
                }
                showToast(`Loaded ${btn.textContent.trim()} CSV sample`, 'info');
            }
        });
    });
    
    // LDC-focused sample document texts
    const sampleDocuments = {
        market_report: {
            text: `France maintained its position as a major wheat exporter to the United States in 2024, with Common Wheat and Durum Wheat leading the commodity flows. Trade data shows France exported approximately 2.5 million metric tons of Common Wheat to the US market, representing a 12% increase from the previous year.

In reverse trade flows, the United States shipped significant volumes of Yellow Corn to France, totaling 1.8 million metric tons. This bilateral trade relationship continues to strengthen, with both countries benefiting from complementary agricultural production cycles.

Production areas in northern France, particularly the Hauts-de-France and Île-de-France regions, reported favorable growing conditions for wheat varieties. Meanwhile, US corn belt states maintained steady Yellow Corn production despite variable weather patterns.`,
            source: 'LDC Quarterly Trade Report Q1 2024'
        },
        trade_news: {
            text: `Recent developments in France-USA agricultural trade show increasing diversity in commodity exchanges. Beyond traditional wheat flows, France has begun exporting Dried Distillers Grains and Barley to the United States, responding to growing demand in the US livestock sector.

The United States reciprocated with increased exports of Peas and Cotton to France, supporting France's food processing industry and textile manufacturers. Trade analysts note that this diversification strengthens the bilateral relationship and reduces dependency on single commodity flows.

Balance sheet data indicates both countries maintain healthy carry-in and carry-out levels for their major commodities, ensuring stable supply chains throughout the year.`,
            source: 'Agricultural Trade Bulletin - February 2024'
        },
        production_update: {
            text: `Weather indicators tracked across production areas show favorable conditions for both French wheat regions and US corn belt territories. Temperature and precipitation data collected from production areas indicate optimal growing conditions for the 2024 season.

French production areas for Common Wheat and Durum Wheat report above-average soil moisture levels, while US Yellow Corn production areas in the Midwest show adequate rainfall patterns. These weather indicators suggest strong harvest prospects for both countries.

The LDC system continues to monitor weather indicators including temperature, precipitation, and other climatic variables across all production areas to provide early warning of potential supply disruptions.`,
            source: 'LDC Production & Weather Update - March 2024'
        }
    };
    
    // Sample document buttons
    $$('.sample-doc-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const sampleKey = btn.dataset.sample;
            const sample = sampleDocuments[sampleKey];
            if (sample) {
                $('documentText').value = sample.text;
                $('documentSource').value = sample.source;
                showToast(`Loaded ${btn.textContent.trim()} sample document`);
            }
        });
    });
}

async function ingestData() {
    const dataText = $('dataInput').value.trim();
    const metadataText = $('metadataInput').value.trim();
    const validate = $('validateData').checked;
    
    if (!dataText || !metadataText) {
        showToast('Please provide both data and metadata', 'warning');
        return;
    }
    
    let data, metadata;
    try {
        data = JSON.parse(dataText);
        metadata = JSON.parse(metadataText);
    } catch (error) {
        showToast('Invalid JSON format', 'error');
        return;
    }
    
    hideResult('ingestionResult');
    showLoader('ingestionLoader');
    
    try {
        const result = await apiCall('/ingest', {
            method: 'POST',
            body: JSON.stringify({
                data: Array.isArray(data) ? data : [data],
                metadata,
                validate
            })
        });
        
        displayIngestionResults(result);
        showToast('Data ingested successfully!');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        hideLoader('ingestionLoader');
    }
}

function displayIngestionResults(result) {
    const stats = $('ingestionStats');
    stats.innerHTML = `
        <div class="stat-card">
            <div class="stat-label">Entities Created</div>
            <div class="stat-value">${result.entities_created}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Relationships Created</div>
            <div class="stat-value">${result.relationships_created}</div>
        </div>
    `;
    
    const details = $('ingestionDetails');
    details.innerHTML = `
        <div style="margin-top: 1rem;">
            <strong>Placement:</strong> ${result.placement?.entity_type || 'N/A'}<br>
            <strong>Entity IDs:</strong> ${result.entity_ids?.join(', ') || 'N/A'}
        </div>
    `;
    
    showResult('ingestionResult');
}

async function ingestDocument() {
    const text = $('documentText').value.trim();
    const source = $('documentSource').value.trim();
    
    if (!text) {
        showToast('Please provide document text', 'warning');
        return;
    }
    
    if (!source) {
        showToast('Please provide document source', 'warning');
        return;
    }
    
    hideResult('documentIngestionResult');
    showLoader('documentIngestionLoader');
    
    try {
        const result = await apiCall('/ingest/document', {
            method: 'POST',
            body: JSON.stringify({
                text,
                source,
                metadata: {}
            })
        });
        
        displayDocumentIngestionResults(result);
        showToast('Document processed successfully!');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        hideLoader('documentIngestionLoader');
    }
}

function displayDocumentIngestionResults(result) {
    const stats = $('documentIngestionStats');
    stats.innerHTML = `
        <div class="stat-card">
            <div class="stat-label">Text Length</div>
            <div class="stat-value">${result.text_length.toLocaleString()} chars</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Entities Found</div>
            <div class="stat-value">${result.entities_found}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Source</div>
            <div class="stat-value" style="font-size: 0.9rem;">${result.source}</div>
        </div>
    `;
    
    // Display extracted entities as tags
    const entitiesList = $('extractedEntitiesList');
    if (result.extracted_entities && result.extracted_entities.length > 0) {
        entitiesList.innerHTML = result.extracted_entities.map(entity => `
            <span class="entity-tag" style="
                padding: 0.25rem 0.75rem;
                background: var(--primary-color);
                color: white;
                border-radius: 12px;
                font-size: 0.85rem;
                display: inline-block;
            ">
                <strong>${entity.name}</strong> <span style="opacity: 0.8;">(${entity.type})</span>
            </span>
        `).join('');
    } else {
        entitiesList.innerHTML = '<p style="color: var(--text-secondary);">No entities extracted</p>';
    }
    
    showResult('documentIngestionResult');
}

// Use Case 4: Impact Analysis
function initImpact() {
    $('analyzeImpactBtn').addEventListener('click', analyzeImpact);
    
    // LDC Reference geometries for France and USA production areas
    const referenceGeometries = {
        // France Regions
        france_north: {
            type: "Polygon",
            coordinates: [[
                [2.0, 48.5], [4.5, 48.5],
                [4.5, 51.0], [2.0, 51.0],
                [2.0, 48.5]
            ]]
        },
        france_picardie: {
            type: "Polygon",
            coordinates: [[
                [1.5, 49.2], [3.5, 49.2],
                [3.5, 50.3], [1.5, 50.3],
                [1.5, 49.2]
            ]]
        },
        france_normandy: {
            type: "Polygon",
            coordinates: [[
                [-1.5, 48.4], [1.5, 48.4],
                [1.5, 49.7], [-1.5, 49.7],
                [-1.5, 48.4]
            ]]
        },
        france_all: {
            type: "Polygon",
            coordinates: [[
                [-5.0, 42.5], [8.2, 42.5],
                [8.2, 51.0], [-5.0, 51.0],
                [-5.0, 42.5]
            ]]
        },
        // USA Regions
        usa_midwest: {
            type: "Polygon",
            coordinates: [[
                [-96.5, 40.0], [-84.0, 40.0],
                [-84.0, 44.5], [-96.5, 44.5],
                [-96.5, 40.0]
            ]]
        },
        usa_wheat: {
            type: "Polygon",
            coordinates: [[
                [-104.0, 37.0], [-94.5, 37.0],
                [-94.5, 49.0], [-104.0, 49.0],
                [-104.0, 37.0]
            ]]
        },
        usa_south: {
            type: "Polygon",
            coordinates: [[
                [-106.0, 25.0], [-75.0, 25.0],
                [-75.0, 37.0], [-106.0, 37.0],
                [-106.0, 25.0]
            ]]
        },
        usa_all: {
            type: "Polygon",
            coordinates: [[
                [-125.0, 24.5], [-66.0, 24.5],
                [-66.0, 49.0], [-125.0, 49.0],
                [-125.0, 24.5]
            ]]
        }
    };
    
    // Handle reference geometry selection
    $('referenceGeometry').addEventListener('change', (e) => {
        const selectedRef = e.target.value;
        if (selectedRef && selectedRef !== 'custom' && referenceGeometries[selectedRef]) {
            $('eventGeometry').value = JSON.stringify(referenceGeometries[selectedRef], null, 2);
        } else if (selectedRef === 'custom') {
            // Keep current value or clear for custom input
        }
    });
}

async function analyzeImpact() {
    const eventType = $('eventTypeSelect').value;
    const geometryText = $('eventGeometry').value.trim();
    const maxHops = parseInt($('maxHops').value);
    const impactThreshold = parseFloat($('impactThreshold').value);
    
    if (!geometryText) {
        showToast('Please provide event geometry', 'warning');
        return;
    }
    
    let geometry;
    try {
        geometry = JSON.parse(geometryText);
    } catch (error) {
        showToast('Invalid GeoJSON format', 'error');
        return;
    }
    
    hideResult('impactResult');
    showLoader('impactLoader');
    
    try {
        const data = await apiCall('/impact', {
            method: 'POST',
            body: JSON.stringify({
                event_geometry: geometry,
                event_type: eventType,
                max_hops: maxHops,
                impact_threshold: impactThreshold
            })
        });
        
        displayImpactResults(data);
        showToast('Impact analysis completed!');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        hideLoader('impactLoader');
    }
}

function displayImpactResults(data) {
    const stats = $('impactStats');
    stats.innerHTML = `
        <div class="stat-card">
            <div class="stat-label">Total Impacts</div>
            <div class="stat-value">${data.total_impacts}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Affected Geographies</div>
            <div class="stat-value">${data.affected_geographies.length}</div>
        </div>
    `;
    
    const tbody = $('impactTableBody');
    tbody.innerHTML = data.impacted_entities.slice(0, 20).map(entity => `
        <tr>
            <td>${entity.entity_type}</td>
            <td>${(entity.impact_score * 100).toFixed(1)}%</td>
            <td>${entity.path?.length || 0} hops</td>
            <td>${entity.affected_geography}</td>
        </tr>
    `).join('');
    
    showResult('impactResult');
}

// Use Case 5: Data Discovery
function initDiscovery() {
    $('searchBtn').addEventListener('click', searchEntities);
    $('executeCypherBtn').addEventListener('click', executeCypher);
    
    $('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchEntities();
    });
    
    // Sample query buttons
    $$('.sample-query-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            // Decode HTML entities and newlines
            const decodedQuery = query
                .replace(/&#10;/g, '\n')
                .replace(/&apos;/g, "'");
            $('cypherQuery').value = decodedQuery;
        });
    });
}

async function searchEntities() {
    const searchTerm = $('searchInput').value.trim();
    const entityTypes = $('entityTypesFilter').value.trim();
    const limit = parseInt($('searchLimit').value);
    
    if (!searchTerm) {
        showToast('Please enter a search term', 'warning');
        return;
    }
    
    hideResult('searchResult');
    
    try {
        const params = new URLSearchParams({
            q: searchTerm,
            limit: limit
        });
        
        if (entityTypes) {
            params.append('entity_types', entityTypes);
        }
        
        const data = await apiCall(`/search?${params}`);
        
        displaySearchResults(data.results);
        $('searchCount').textContent = `${data.results.length} results`;
        showResult('searchResult');
        showToast('Search completed!');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

function displaySearchResults(results) {
    const container = $('searchResults');
    
    if (!results || results.length === 0) {
        container.innerHTML = '<p>No results found</p>';
        return;
    }
    
    container.innerHTML = results.map(result => `
        <div class="search-result-item" style="padding: 1rem; border: 1px solid var(--border-color); border-radius: 6px; margin-bottom: 0.75rem;">
            <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;">${JSON.stringify(result, null, 2)}</pre>
        </div>
    `).join('');
}

async function executeCypher() {
    const query = $('cypherQuery').value.trim();
    
    if (!query) {
        showToast('Please enter a Cypher query', 'warning');
        return;
    }
    
    hideResult('cypherResult');
    
    try {
        const data = await apiCall('/cypher', {
            method: 'POST',
            body: JSON.stringify({ query })
        });
        
        displayCypherResults(data.results);
        showResult('cypherResult');
        showToast('Query executed successfully!');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

function displayCypherResults(results) {
    const thead = $('cypherTableHead');
    const tbody = $('cypherTableBody');
    
    if (!results || results.length === 0) {
        tbody.innerHTML = '<tr><td>No results</td></tr>';
        return;
    }
    
    const keys = Object.keys(results[0]);
    thead.innerHTML = `
        <tr>${keys.map(key => `<th>${key}</th>`).join('')}</tr>
    `;
    
    tbody.innerHTML = results.map(row => `
        <tr>${keys.map(key => `<td>${JSON.stringify(row[key])}</td>`).join('')}</tr>
    `).join('');
}

// Schema Explorer
async function loadSchema() {
    const container = $('schemaContainer');
    container.innerHTML = '<div class="loader"><div class="spinner"></div><p>Loading schema...</p></div>';
    
    try {
        const data = await apiCall('/schema');
        displaySchema(data);
    } catch (error) {
        container.innerHTML = `<p>Error loading schema: ${error.message}</p>`;
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function displaySchema(schema) {
    const container = $('schemaContainer');
    let html = '';
    
    // Display concepts
    if (schema.concepts) {
        html += '<div class="schema-section"><h4>Concepts</h4><div class="schema-items">';
        for (const [name, details] of Object.entries(schema.concepts)) {
            html += `
                <div class="schema-item">
                    <strong>${name}</strong>
                    <small>${details.description || ''}</small>
                </div>
            `;
        }
        html += '</div></div>';
    }
    
    // Display relationships with counts from stats
    try {
        const stats = await apiCall('/stats');
        if (stats.relationships) {
            html += '<div class="schema-section">';
            html += '<h4>Relationships (Edges in Graph)</h4>';
            html += '<div class="stats-grid" style="grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem;">';
            
            for (const [relType, count] of Object.entries(stats.relationships)) {
                html += `
                    <div class="stat-card" style="padding: 1rem; background: var(--bg-color); border-radius: 6px; border: 1px solid var(--border-color);">
                        <div class="stat-label" style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                            <i class="fas fa-arrow-right" style="margin-right: 0.5rem;"></i>${relType}
                        </div>
                        <div class="stat-value" style="font-size: 1.5rem; font-weight: 600; color: var(--primary-color);">${count.toLocaleString()}</div>
                        <small style="color: var(--text-muted); font-size: 0.75rem;">edges</small>
                    </div>
                `;
            }
            html += '</div></div>';
        }
    } catch (error) {
        console.error('Error loading relationship stats:', error);
        // Fallback to basic relationship display
        if (schema.relationships) {
            html += '<div class="schema-section"><h4>Relationships</h4><div class="schema-items">';
            schema.relationships.forEach(rel => {
                html += `
                    <div class="schema-item">
                        <strong>${rel.name || rel}</strong>
                        <small>${rel.description || ''}</small>
                    </div>
                `;
            });
            html += '</div></div>';
        }
    }
    
    // Display data sources
    if (schema.data_sources) {
        html += '<div class="schema-section"><h4>Data Sources</h4><div class="schema-items">';
        schema.data_sources.forEach(source => {
            html += `
                <div class="schema-item">
                    <strong>${source.name}</strong>
                    <small>${source.description || ''}</small>
                </div>
            `;
        });
        html += '</div></div>';
    }
    
    container.innerHTML = html || '<p>No schema data available</p>';
}

// Statistics
async function loadStatistics() {
    const container = $('statsDashboard');
    container.innerHTML = '<div class="loader"><div class="spinner"></div><p>Loading statistics...</p></div>';
    
    try {
        const data = await apiCall('/stats');
        displayStatistics(data);
    } catch (error) {
        container.innerHTML = `<p>Error loading statistics: ${error.message}</p>`;
        showToast(`Error: ${error.message}`, 'error');
    }
}

function displayStatistics(stats) {
    const container = $('statsDashboard');
    let html = '';
    
    // Node statistics
    if (stats.nodes) {
        html += '<div class="card"><div class="card-header"><h3>Node Counts</h3></div><div class="card-body"><div class="stats-grid">';
        for (const [type, count] of Object.entries(stats.nodes)) {
            html += `
                <div class="stat-card">
                    <div class="stat-label">${type}</div>
                    <div class="stat-value">${count.toLocaleString()}</div>
                </div>
            `;
        }
        html += '</div></div></div>';
    }
    
    // Relationship statistics
    if (stats.relationships) {
        html += '<div class="card"><div class="card-header"><h3>Relationship Counts</h3></div><div class="card-body"><div class="stats-grid">';
        for (const [type, count] of Object.entries(stats.relationships)) {
            html += `
                <div class="stat-card">
                    <div class="stat-label">${type}</div>
                    <div class="stat-value">${count.toLocaleString()}</div>
                </div>
            `;
        }
        html += '</div></div></div>';
    }
    
    container.innerHTML = html || '<p>No statistics available</p>';
}

// Settings
function initSettings() {
    $('settingsBtn').addEventListener('click', () => {
        $('settingsModal').style.display = 'flex';
        $('apiUrlInput').value = API_BASE_URL;
    });
    
    $('closeSettingsBtn').addEventListener('click', closeSettings);
    $('cancelSettingsBtn').addEventListener('click', closeSettings);
    
    $('saveSettingsBtn').addEventListener('click', () => {
        API_BASE_URL = $('apiUrlInput').value;
        localStorage.setItem('apiBaseUrl', API_BASE_URL);
        closeSettings();
        showToast('Settings saved!');
        checkHealth();
    });
}

function closeSettings() {
    $('settingsModal').style.display = 'none';
}

// CSV Export
function exportToCSV(tableId) {
    const table = $(tableId);
    let csv = [];
    
    // Get headers
    const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent);
    csv.push(headers.join(','));
    
    // Get rows
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const cells = Array.from(row.querySelectorAll('td')).map(td => `"${td.textContent}"`);
        csv.push(cells.join(','));
    });
    
    // Download
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tableId}_export.csv`;
    a.click();
    URL.revokeObjectURL(url);
    
    showToast('CSV exported successfully!');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initCopilot();
    initAnalytics();
    initIngestion();
    initImpact();
    initDiscovery();
    initSettings();
    
    // Check health on load
    checkHealth();
    
    // Refresh health every 30 seconds
    setInterval(checkHealth, 30000);
    
    // Load schema button
    $('loadSchemaBtn').addEventListener('click', loadSchema);
});
