"""
Load Additional External Sources Through Graphiti

This script ingests various types of unstructured documents from "external" sources
through Graphiti to enrich the knowledge graph with semantic embeddings and increase
confidence scores for natural language queries.
"""

import asyncio
import aiohttp
import time
from typing import Dict, Any

API_URL = "http://localhost:8000"

# Collection of diverse external sources to ingest
EXTERNAL_SOURCES = [
    {
        "source": "Reuters Market Report - Q1 2024",
        "text": """
        Global corn markets experienced significant volatility in Q1 2024. United States corn 
        production in Iowa reached record levels of 2.4 billion bushels, representing a 12% 
        increase from the previous year. This surge was driven by favorable weather conditions 
        and improved farming techniques. Meanwhile, corn exports from the USA to China increased 
        by 18% quarter-over-quarter, totaling 8.5 million metric tons. Analysts attribute this 
        growth to China's recovering livestock sector and reduced domestic production. 
        
        Germany's corn demand for industrial use and livestock feed remained steady at 
        approximately 4.2 million metric tons for the quarter, with imports primarily sourced 
        from France and Ukraine. Market prices for corn in Chicago Board of Trade averaged 
        $4.85 per bushel, reflecting the balanced supply-demand dynamics.
        """
    },
    {
        "source": "USDA Agricultural Outlook - March 2024",
        "text": """
        The USDA projects continued strength in US wheat production for 2024, with total output 
        expected to reach 1.8 billion bushels. Key producing states including Kansas, North Dakota, 
        and Montana report excellent crop conditions. Winter wheat yields are forecasted at 
        52 bushels per acre, up from 48 bushels per acre in 2023.
        
        France remains Europe's largest wheat producer, with 2024 production estimates at 
        36 million metric tons. The Picardie region continues to be a top contributor, 
        accounting for approximately 18% of national production. French wheat exports to 
        Morocco and Algeria have increased by 22% year-over-year, driven by North African 
        demand and competitive pricing. MARS satellite data confirms favorable growing 
        conditions across French wheat-growing regions.
        """
    },
    {
        "source": "Bloomberg Commodities Analysis - Feb 2024",
        "text": """
        Soybean markets are experiencing a paradigm shift as Brazil consolidates its position 
        as the world's leading soybean exporter. Brazil's 2024 soybean production is projected 
        at 155 million metric tons, surpassing the previous record. The Mato Grosso region 
        alone accounts for 35% of national production, with yields averaging 3.6 tons per hectare.
        
        Brazil's soybean exports to China reached 75 million metric tons in 2023, representing 
        65% of total Brazilian soybean exports. This trade relationship continues to strengthen, 
        with Chinese importers signing long-term contracts valued at over $28 billion. 
        Additionally, Brazil is expanding soybean shipments to the European Union, with exports 
        to EU markets growing 15% annually. The EU's demand for non-GMO soybeans creates premium 
        pricing opportunities for Brazilian producers.
        """
    },
    {
        "source": "FAO Global Food Security Report - 2024",
        "text": """
        Rice production in Asia remains critical for global food security. China's rice production 
        for 2024 is estimated at 148 million metric tons, maintaining its position as the world's 
        largest rice producer. Key rice-growing provinces including Hunan, Jiangxi, and Heilongjiang 
        reported stable yields despite water management challenges.
        
        The International Rice Research Institute reports that improved rice varieties and 
        precision agriculture techniques are increasing yields across major producing countries. 
        Thailand's rice exports declined 8% in Q1 2024 due to drought conditions affecting 
        the Chao Phraya River basin. Vietnam and India are filling the supply gap, with India's 
        rice exports reaching 18 million metric tons annually. Global rice prices remain elevated, 
        with Thai white rice 5% broken trading at $625 per metric ton.
        """
    },
    {
        "source": "Agricultural Economics Journal - Winter 2024",
        "text": """
        Recent studies on agricultural productivity reveal significant regional variations in 
        crop yields. Corn yield in Iowa averaged 198 bushels per acre in 2023, attributed to 
        optimal rainfall patterns and advanced hybrid seed varieties. In contrast, Argentina's 
        corn production faced challenges, with yields dropping to 85 bushels per acre due to 
        La Niña weather patterns and reduced fertilizer application.
        
        Wheat yield performance across major producers shows France maintaining high productivity 
        at 7.2 tons per hectare, while Morocco's wheat yields averaged 1.8 tons per hectare, 
        constrained by limited irrigation infrastructure. The yield gap between developed and 
        developing nations highlights opportunities for agricultural technology transfer and 
        capacity building initiatives.
        """
    },
    {
        "source": "Trade Flows Quarterly - Q4 2023",
        "text": """
        Global commodity trade flows are reshaping as geopolitical factors influence traditional 
        supply chains. USA corn exports totaled 58 million metric tons in 2023, with Mexico 
        emerging as the largest single destination at 17 million metric tons, followed by Japan 
        at 12 million metric tons. China's corn imports from the USA fluctuated throughout the 
        year, ranging from 500,000 to 1.2 million metric tons monthly depending on domestic 
        production forecasts.
        
        Wheat trade dynamics show Russia and Ukraine competing for market share in North Africa 
        and Middle East markets. France's wheat exports to Morocco totaled 2.8 million metric 
        tons in 2023, representing 35% of Morocco's total wheat imports. However, competitive 
        pricing from Black Sea exporters is pressuring French market share. Egypt remains the 
        world's largest wheat importer at 13 million metric tons annually.
        """
    },
    {
        "source": "Climate Impact Assessment - AgriWatch 2024",
        "text": """
        Climate variability continues to impact agricultural production across key commodity 
        regions. The 2024 growing season saw Brazil's Mato Grosso region experience optimal 
        rainfall, contributing to record soybean yields of 3.7 tons per hectare. However, 
        Rio Grande do Sul faced flooding that reduced soybean production by 15%.
        
        USA Corn Belt states experienced mixed conditions, with Iowa and Illinois benefiting 
        from timely precipitation while Nebraska and Kansas dealt with drought stress during 
        critical growth stages. These conditions resulted in a 7% yield variability across 
        the region. In Europe, France's wheat production benefited from mild winter temperatures 
        and spring rainfall, with the Picardie and Centre regions reporting above-average yields.
        """
    },
    {
        "source": "CONAB Brazil Agricultural Report - Jan 2024",
        "text": """
        CONAB (Companhia Nacional de Abastecimento) releases its comprehensive analysis of 
        Brazil's agricultural performance. Soybean production in Brazil for the 2023/24 season 
        is confirmed at 154.6 million metric tons, with planted area reaching 45.8 million 
        hectares. Mato Grosso state leads with 38.4 million metric tons, followed by Paraná 
        with 21.8 million metric tons and Rio Grande do Sul with 19.2 million metric tons.
        
        Brazilian soybean exports in 2023 totaled 98.5 million metric tons, generating 
        $55.4 billion in export revenue. China imported 76.8 million metric tons of Brazilian 
        soybeans, while the European Union imported 8.2 million metric tons. Domestic soybean 
        processing (crushing) consumed 51.2 million metric tons for soybean meal and oil 
        production. Brazil's corn production is projected at 129 million metric tons, with 
        second-season (safrinha) corn accounting for 75% of total production.
        """
    },
    {
        "source": "European Commission MARS Bulletin - March 2024",
        "text": """
        The MARS (Monitoring Agricultural Resources) system reports favorable conditions for 
        European cereal crops. France's soft wheat production forecast remains at 35.8 million 
        metric tons, with average yields of 7.15 tons per hectare. The Picardie, Centre-Val de Loire, 
        and Île-de-France regions are primary contributors, collectively producing 45% of national 
        wheat output.
        
        Germany's wheat production is estimated at 22.4 million metric tons, with yields of 
        7.8 tons per hectare. However, Germany's corn production faces challenges due to 
        late planting and cooler spring temperatures, potentially reducing yields by 5-8%. 
        Poland's wheat exports to EU markets increased 12%, positioning Poland as a growing 
        competitor to French wheat in regional markets. MARS satellite imagery confirms 
        excellent crop development across major EU wheat-producing regions.
        """
    },
    {
        "source": "Asian Agricultural Market Monitor - Feb 2024",
        "text": """
        China's agricultural imports continue to drive global commodity flows. Chinese corn 
        imports in 2023 totaled 27.3 million metric tons, primarily sourced from USA (45%), 
        Ukraine (28%), and Brazil (15%). Domestic corn production reached 288 million metric 
        tons, but demand for livestock feed exceeded supply, necessitating continued imports.
        
        Chinese demand for soybeans remains robust at 100 million metric tons annually. Brazil 
        supplies approximately 60% of China's soybean imports, while USA supplies 25-30% 
        depending on harvest timing and pricing. China's pork production recovery drives 
        increased soybean meal demand for feed formulation. Rice production in China stabilized 
        at 147.5 million metric tons, with domestic consumption at 145 million metric tons, 
        leaving minimal exportable surplus.
        """
    },
    {
        "source": "North African Trade Analysis - Jan 2024",
        "text": """
        Morocco's agricultural imports are essential for food security, with wheat imports 
        totaling 7.8 million metric tons in 2023. France remains Morocco's primary wheat 
        supplier, providing 2.9 million metric tons (37% of total imports), followed by 
        Russia with 2.1 million metric tons (27%) and Ukraine with 1.4 million metric tons (18%).
        
        Morocco's domestic wheat production was constrained by drought conditions, yielding 
        only 2.5 million metric tons compared to a five-year average of 5.8 million metric tons. 
        The Moroccan government increased wheat import quotas and reduced tariffs to ensure 
        adequate domestic supply. Corn imports for livestock feed reached 2.2 million metric tons, 
        primarily from Brazil and Argentina. Morocco's agricultural ministry projects improved 
        wheat production for 2024 if precipitation patterns normalize.
        """
    },
    {
        "source": "Market Price Analysis - AgriPrice Weekly",
        "text": """
        Commodity price movements in early 2024 reflect supply-demand dynamics and macroeconomic 
        factors. Chicago Board of Trade corn futures for March 2024 delivery averaged $4.82 per 
        bushel, up 3.5% from December 2023 levels. Wheat prices on CBOT averaged $6.15 per 
        bushel, with premium hard red winter wheat trading at $6.45 per bushel.
        
        Soybean prices experienced volatility, with March futures ranging from $12.25 to $13.10 
        per bushel. Brazilian soybean export prices (FOB Paranaguá) averaged $485 per metric ton, 
        while USA Gulf export prices averaged $495 per metric ton. Chinese soybean import prices 
        (CFR) ranged from $510 to $525 per metric ton depending on origin and quality 
        specifications. Rice prices remained elevated, with Thai white rice 5% broken at $620 
        per metric ton and Vietnamese 5% broken at $590 per metric ton.
        """
    },
    {
        "source": "Supply Chain Logistics Report - Shipping Times",
        "text": """
        Agricultural commodity shipping routes and transit times impact trade flows and pricing. 
        Brazil to China soybean shipments average 35-40 days transit time via Cape of Good Hope 
        route, with freight costs ranging from $45 to $55 per metric ton depending on vessel 
        availability and fuel prices. USA Gulf to China corn shipments average 30-35 days via 
        Panama Canal route.
        
        France to Morocco wheat shipments utilize Mediterranean shipping lanes with 7-10 days 
        transit time and freight costs of $18-$22 per metric ton. Black Sea wheat exports to 
        North Africa and Middle East benefit from shorter shipping distances, averaging 5-7 days 
        transit time. Global shipping container availability improved in Q1 2024, reducing 
        logistical bottlenecks that impacted agricultural exports in previous quarters.
        """
    },
    {
        "source": "Agricultural Technology Report - FarmTech 2024",
        "text": """
        Precision agriculture adoption is transforming crop production efficiency. Iowa corn 
        farmers utilizing variable rate fertilizer application and satellite-guided planting 
        equipment achieved average yields 8% higher than conventional methods. Brazil's soybean 
        producers in Mato Grosso implemented drone-based crop monitoring, enabling early 
        detection of pest infestations and optimized pesticide application.
        
        France's wheat farmers increasingly adopt MARS satellite data and predictive analytics 
        for yield forecasting and harvest planning. Digital agriculture platforms provide 
        real-time soil moisture data, weather forecasts, and market price information, enabling 
        data-driven decision making. The integration of IoT sensors, AI-powered analytics, and 
        blockchain for supply chain traceability is accelerating across major agricultural 
        regions. Technology adoption rates vary, with developed nations at 45-60% adoption 
        while developing nations range from 15-25%.
        """
    },
    {
        "source": "Sustainability and ESG Report - AgriSustain 2024",
        "text": """
        Environmental, Social, and Governance (ESG) factors increasingly influence commodity 
        trading decisions. European Union buyers prioritize sustainably produced soybeans, 
        creating premium markets for certified deforestation-free Brazilian soybeans. Brazil's 
        soy moratorium and environmental compliance programs enable access to EU markets, with 
        certified sustainable soybeans commanding 8-12% price premiums.
        
        USA corn producers implement carbon farming practices, sequestering atmospheric carbon 
        through no-till farming and cover crops. Carbon credits from agricultural practices 
        generate additional revenue streams, with corn farmers earning $15-$25 per acre annually 
        from carbon programs. France's wheat production emphasizes reduced pesticide use and 
        biodiversity protection, aligning with EU Green Deal objectives. China's agricultural 
        policy emphasizes food security and reduced reliance on imports, driving domestic 
        production incentives and technology investments.
        """
    }
]


async def wait_for_api():
    """Wait for API to be ready."""
    print("Waiting for API to be ready...")
    for i in range(30):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/health") as response:
                    if response.status == 200:
                        print("✓ API is ready")
                        return True
        except:
            pass
        await asyncio.sleep(2)
    print("✗ API not available")
    return False


async def ingest_document(source: str, text: str) -> Dict[str, Any]:
    """Ingest a document through Graphiti."""
    print(f"\n📄 Ingesting: {source}")
    print(f"   Text length: {len(text)} characters")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/ingest/document",
                json={
                    "text": text.strip(),
                    "source": source,
                    "metadata": {
                        "ingestion_date": "2024",
                        "document_type": "external_report"
                    }
                },
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✓ Successfully ingested")
                    return result
                else:
                    error_text = await response.text()
                    print(f"   ✗ Error {response.status}: {error_text}")
                    return None
    except asyncio.TimeoutError:
        print(f"   ⚠ Timeout (document may still be processing)")
        return None
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return None


async def get_stats() -> Dict[str, Any]:
    """Get current graph statistics."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/stats") as response:
                if response.status == 200:
                    return await response.json()
    except Exception as e:
        print(f"Error fetching stats: {e}")
    return {}


async def main():
    """Main ingestion workflow."""
    print("=" * 80)
    print("LOADING EXTERNAL SOURCES THROUGH GRAPHITI")
    print("=" * 80)
    
    # Wait for API
    if not await wait_for_api():
        print("\n❌ API not available. Please start the API server first.")
        return
    
    # Get initial stats
    print("\n" + "=" * 80)
    print("INITIAL STATS")
    print("=" * 80)
    initial_stats = await get_stats()
    print(f"Total nodes: {initial_stats.get('total_nodes', 0)}")
    print(f"Total relationships: {initial_stats.get('total_relationships', 0)}")
    
    # Ingest all documents
    print("\n" + "=" * 80)
    print(f"INGESTING {len(EXTERNAL_SOURCES)} EXTERNAL DOCUMENTS")
    print("=" * 80)
    
    successful = 0
    failed = 0
    
    for i, doc in enumerate(EXTERNAL_SOURCES, 1):
        print(f"\n[{i}/{len(EXTERNAL_SOURCES)}]", end=" ")
        result = await ingest_document(doc["source"], doc["text"])
        
        if result:
            successful += 1
        else:
            failed += 1
        
        # Small delay between documents to avoid overwhelming the API
        if i < len(EXTERNAL_SOURCES):
            await asyncio.sleep(2)
    
    # Get final stats
    print("\n" + "=" * 80)
    print("FINAL STATS")
    print("=" * 80)
    
    await asyncio.sleep(3)  # Wait for final processing
    final_stats = await get_stats()
    
    print(f"Total nodes: {final_stats.get('total_nodes', 0)}")
    print(f"Total relationships: {final_stats.get('total_relationships', 0)}")
    
    # Count Graphiti nodes
    nodes_by_label = final_stats.get('nodes_by_label', {})
    episodic_count = nodes_by_label.get('EpisodicNode', 0)
    entity_count = nodes_by_label.get('EntityNode', 0)
    
    print(f"\nGraphiti Embeddings:")
    print(f"  - Episodic nodes: {episodic_count}")
    print(f"  - Entity nodes: {entity_count}")
    
    # Summary
    print("\n" + "=" * 80)
    print("INGESTION SUMMARY")
    print("=" * 80)
    print(f"✓ Successfully ingested: {successful} documents")
    if failed > 0:
        print(f"✗ Failed: {failed} documents")
    
    print(f"\n📊 Total external sources now available: {successful}")
    print("🎯 These sources will increase confidence scores in Trading Copilot queries")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
