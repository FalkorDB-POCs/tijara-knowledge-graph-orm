/**
 * Theme Switcher - Dynamically loads the appropriate theme based on active dataset
 * Fetches config from API and applies the correct CSS theme
 */

(async function() {
    'use strict';
    
    const THEME_CONFIG = {
        ldc: {
            css: '/static/css/theme-ldc.css',
            name: 'LDC Production',
            icon: 'fa-building',
            badge: 'LDC Production Data'
        },
        demo: {
            css: '/static/css/theme-demo.css',
            name: 'Demo Mode',
            icon: 'fa-flask',
            badge: 'Demo Dataset'
        }
    };
    
    /**
     * Fetch active dataset configuration from API
     */
    async function fetchConfig() {
        try {
            const response = await fetch('/config');
            if (!response.ok) {
                throw new Error('Failed to fetch config');
            }
            return await response.json();
        } catch (error) {
            console.warn('Could not fetch config, defaulting to demo theme:', error);
            return {
                dataset_type: 'demo',
                graph_name: 'tijara_graph',
                theme: 'theme-demo.css'
            };
        }
    }
    
    /**
     * Load the appropriate theme CSS
     */
    function loadTheme(datasetType) {
        const themeConfig = THEME_CONFIG[datasetType] || THEME_CONFIG.demo;
        
        // Check if theme is already loaded
        const existingTheme = document.getElementById('dynamic-theme');
        if (existingTheme) {
            existingTheme.href = themeConfig.css;
        } else {
            // Create and append theme link
            const link = document.createElement('link');
            link.id = 'dynamic-theme';
            link.rel = 'stylesheet';
            link.href = themeConfig.css;
            document.head.appendChild(link);
        }
        
        // Store theme in body data attribute for potential JS use
        document.body.setAttribute('data-theme', datasetType);
        document.body.setAttribute('data-dataset', datasetType);
        
        console.log(`✓ Loaded ${themeConfig.name} theme`);
        return themeConfig;
    }
    
    /**
     * Add dataset badge to header if element exists
     */
    function addDatasetBadge(themeConfig) {
        // Look for a designated badge container or header-info
        const badgeContainer = document.querySelector('.header-info .dataset-badge-container') 
                            || document.querySelector('.header-info');
        
        if (badgeContainer) {
            // Remove existing badge if any
            const existingBadge = badgeContainer.querySelector('.dataset-badge');
            if (existingBadge) {
                existingBadge.remove();
            }
            
            // Create new badge
            const badge = document.createElement('div');
            badge.className = 'dataset-badge';
            badge.innerHTML = `<i class="fas ${themeConfig.icon}"></i> ${themeConfig.badge}`;
            
            // Insert before settings button if it exists
            const settingsBtn = badgeContainer.querySelector('#settingsBtn');
            if (settingsBtn) {
                badgeContainer.insertBefore(badge, settingsBtn);
            } else {
                badgeContainer.appendChild(badge);
            }
        }
    }
    
    /**
     * Update quick questions based on dataset type
     */
    function updateQuickQuestions(datasetType) {
        const quickQuestionsContainer = document.querySelector('.quick-questions');
        if (!quickQuestionsContainer) return;
        
        const ldcQuestions = [
            "What countries are in the LDC system?",
            "What commodities does France export to the United States?",
            "What commodities does USA export to France?",
            "What balance sheets are available in the system?",
            "What weather indicators are tracked for production areas?",
            "Which commodities have production areas in France and USA?"
        ];
        
        const demoQuestions = [
            "What commodities are tracked in the system?",
            "Show me production data for corn",
            "What countries have wheat production?",
            "Compare production volumes by commodity",
            "What data types are available?",
            "Show me export data for soybeans"
        ];
        
        const questions = datasetType === 'ldc' ? ldcQuestions : demoQuestions;
        
        // Update button text
        const buttons = quickQuestionsContainer.querySelectorAll('.quick-question-btn');
        buttons.forEach((btn, index) => {
            if (questions[index]) {
                btn.textContent = questions[index];
                btn.setAttribute('data-question', questions[index]);
            }
        });
    }
    
    /**
     * Update page title based on dataset
     */
    function updatePageTitle(datasetType) {
        const titleSuffix = datasetType === 'ldc' ? 'LDC Commodity Intelligence' : 'Demo & Testing';
        document.title = `Tijara Knowledge Graph - ${titleSuffix}`;
    }
    
    /**
     * Emit custom event for other scripts to react to theme change
     */
    function emitThemeChangeEvent(config) {
        const event = new CustomEvent('themeLoaded', {
            detail: {
                datasetType: config.dataset_type,
                graphName: config.graph_name,
                theme: config.theme
            }
        });
        document.dispatchEvent(event);
    }
    
    /**
     * Initialize theme system
     */
    async function initialize() {
        try {
            // Fetch config
            const config = await fetchConfig();
            console.log('Dataset configuration:', config);
            
            // Load theme
            const themeConfig = loadTheme(config.dataset_type);
            
            // Update UI elements
            updatePageTitle(config.dataset_type);
            
            // Wait for DOM to be fully ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    addDatasetBadge(themeConfig);
                    updateQuickQuestions(config.dataset_type);
                });
            } else {
                addDatasetBadge(themeConfig);
                updateQuickQuestions(config.dataset_type);
            }
            
            // Emit event for other scripts
            emitThemeChangeEvent(config);
            
            // Store config globally for other scripts
            window.TIJARA_CONFIG = config;
            
        } catch (error) {
            console.error('Theme initialization error:', error);
        }
    }
    
    // Initialize immediately
    initialize();
    
    // Expose API for manual theme switching (for testing)
    window.TijaraTheme = {
        switch: async function(datasetType) {
            if (THEME_CONFIG[datasetType]) {
                const themeConfig = loadTheme(datasetType);
                updatePageTitle(datasetType);
                addDatasetBadge(themeConfig);
                updateQuickQuestions(datasetType);
                console.log(`Manually switched to ${datasetType} theme`);
            } else {
                console.error('Invalid dataset type:', datasetType);
            }
        },
        reload: initialize,
        getConfig: () => window.TIJARA_CONFIG
    };
    
})();
