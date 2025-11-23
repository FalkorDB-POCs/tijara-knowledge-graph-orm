"""Test confidence scores for all quick questions"""
import asyncio
import aiohttp
import json

API_URL = "http://localhost:8000"

QUESTIONS = [
    "Compare corn production in Iowa, exports from USA to China, and demand in Germany for 2024",
    "What are the top 3 wheat producing countries, their average yields, and primary export destinations?",
    "How do Brazil's soybean production volumes, export prices, and shipment frequencies to China compare year-over-year?",
    "Analyze France wheat production trends, export volumes to Morocco, and correlation with MARS yield forecasts",
    "Which commodities show increasing production, rising exports, and growing demand across multiple regions in 2024-2025?",
    "Compare USA corn production by state, total export volumes by destination, and USDA source data reliability"
]


async def test_question(session, question, index):
    """Test a single question and return confidence info."""
    print(f"\n{'='*80}")
    print(f"QUESTION {index + 1}/{len(QUESTIONS)}")
    print(f"{'='*80}")
    print(f"{question}")
    print(f"{'='*80}")
    
    try:
        async with session.post(
            f"{API_URL}/query",
            json={"question": question, "return_sources": True},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            if response.status == 200:
                data = await response.json()
                
                confidence = data.get('confidence', 0)
                sources = data.get('sources', [])
                entities = data.get('retrieved_entities', [])
                subgraph = data.get('subgraph', [])
                
                print(f"\n📊 RESULTS:")
                print(f"   Confidence: {confidence*100:.0f}% ({confidence:.2f})")
                print(f"   Sources found: {len(sources)}")
                print(f"   Entities extracted: {len(entities)}")
                print(f"   Subgraph data points: {len(subgraph)}")
                
                if sources:
                    print(f"\n   Source types:")
                    for i, source in enumerate(sources[:5], 1):
                        source_type = source.get('type', 'unknown')
                        source_name = source.get('name', source.get('source', 'unnamed'))
                        print(f"     {i}. {source_type}: {source_name}")
                
                if entities:
                    print(f"\n   Entities: {', '.join(entities[:10])}")
                
                # Analyze why confidence might be low
                print(f"\n   Confidence breakdown:")
                if sources:
                    print(f"     ✓ Sources found: +0.5")
                else:
                    print(f"     ✗ No sources found: +0.0")
                
                if subgraph:
                    print(f"     ✓ Subgraph data: +0.3")
                else:
                    print(f"     ✗ No subgraph data: +0.0")
                
                if len(sources) >= 3:
                    print(f"     ✓ Multiple sources (≥3): +0.2")
                else:
                    print(f"     ✗ Few sources (<3): +0.0")
                
                expected_confidence = 0.0
                if sources:
                    expected_confidence += 0.5
                if subgraph:
                    expected_confidence += 0.3
                if len(sources) >= 3:
                    expected_confidence += 0.2
                
                print(f"     Expected: {expected_confidence:.2f} (max 1.0)")
                print(f"     Actual: {confidence:.2f}")
                
                # Show snippet of answer
                answer = data.get('answer', '')
                print(f"\n   Answer preview:")
                print(f"     {answer[:200]}...")
                
                return {
                    'question': question,
                    'confidence': confidence,
                    'sources_count': len(sources),
                    'entities_count': len(entities),
                    'subgraph_count': len(subgraph),
                    'expected_confidence': expected_confidence
                }
            else:
                error_text = await response.text()
                print(f"\n   ✗ Error {response.status}: {error_text}")
                return None
    except Exception as e:
        print(f"\n   ✗ Exception: {str(e)}")
        return None


async def main():
    print("="*80)
    print("TESTING CONFIDENCE SCORES FOR ALL QUICK QUESTIONS")
    print("="*80)
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i, question in enumerate(QUESTIONS):
            result = await test_question(session, question, i)
            if result:
                results.append(result)
            
            # Small delay between questions
            if i < len(QUESTIONS) - 1:
                await asyncio.sleep(2)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for i, result in enumerate(results, 1):
        confidence_pct = result['confidence'] * 100
        expected_pct = result['expected_confidence'] * 100
        badge = '🟢' if confidence_pct >= 70 else '🟡' if confidence_pct >= 40 else '🔴'
        
        print(f"\n{badge} Q{i}: {confidence_pct:.0f}% (expected {expected_pct:.0f}%)")
        print(f"   Sources: {result['sources_count']}, Entities: {result['entities_count']}, Data: {result['subgraph_count']}")
        print(f"   Question: {result['question'][:70]}...")
    
    # Average confidence
    if results:
        avg_confidence = sum(r['confidence'] for r in results) / len(results)
        avg_expected = sum(r['expected_confidence'] for r in results) / len(results)
        print(f"\n📈 AVERAGE CONFIDENCE: {avg_confidence*100:.0f}% (expected {avg_expected*100:.0f}%)")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if avg_confidence < 0.5:
            print("   - Confidence is LOW - consider adjusting calculation")
            print("   - Current formula may be too conservative")
            print("   - Suggested: Increase weights or lower thresholds")
        elif avg_confidence < 0.7:
            print("   - Confidence is MEDIUM - reasonable but could be higher")
            print("   - Consider: Reward entity matching or answer completeness")
        else:
            print("   - Confidence is HIGH - formula is working well")
            print("   - Current calculation accurately reflects data quality")


if __name__ == "__main__":
    asyncio.run(main())
