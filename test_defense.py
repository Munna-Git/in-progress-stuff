"""
Test script for Phase 4: Liability Prevention (Three-Layer Defense).
Verifies that the system correctly intercepts purchase intent and domain violations.
"""

import asyncio
import sys
import io
import logging

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configure logging
logging.basicConfig(level=logging.ERROR)

from src.rag.engine import get_engine

async def test_defense():
    print("="*60)
    print("LIABILITY PREVENTION TEST (Phase 4)")
    print("="*60)
    
    engine = await get_engine()
    
    # Test Cases
    test_cases = [
        {
            "name": "Purchase Intent - Price",
            "query": "How much is the DesignMax DM3C?",
            "expected_type": "purchase_intent",
            "expected_text": "pricing and availability"
        },
        {
            "name": "Purchase Intent - Stock",
            "query": "Do you have DM5C in stock?",
            "expected_type": "purchase_intent",
            "expected_text": "pricing and availability"
        },
        {
            "name": "Purchase Intent - Buying",
            "query": "Where can I buy the AM10?",
            "expected_type": "purchase_intent",
            "expected_text": "pricing and availability"
        },
        {
            "name": "Domain Violation - Competitor",
            "query": "How does this compare to Sonos speakers?",
            "expected_type": "domain_violation",
            "expected_text": "Bose Professional products"
        },
        {
            "name": "Domain Violation - Brand",
            "query": "Is JBL better than Bose?",
            "expected_type": "domain_violation",
            "expected_text": "Bose Professional products"
        },
        {
            "name": "Standard Query (Regression Test)",
            "query": "What is the power handling of DM3C?",
            "expected_type": "direct_lookup",  # or semantic_search depending on router
            "expected_text": "Power"
        }
    ]
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        print(f"\nTest Case: {case['name']}")
        print(f"Query: {case['query']}")
        
        result = await engine.query(case['query'])
        
        print(f"Result Type: {result.query_type}")
        print(f"Result Text: {result.answer}")
        
        # Verification
        type_match = True
        if case['expected_type'] == "direct_lookup" and result.query_type == "direct_lookup":
            type_match = True
        elif case['expected_type'] in ["purchase_intent", "domain_violation"]:
            type_match = result.query_type == case['expected_type']
        
        text_match = case['expected_text'] in result.answer
        
        if type_match and text_match:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            print(f"  Expected Type: {case['expected_type']}, Got: {result.query_type}")
            print(f"  Expected Text content: '{case['expected_text']}'")
            failed += 1
            
    print("\n" + "="*60)
    print(f"SUMMARY: {passed} Passed, {failed} Failed")
    print("="*60)
    
    await engine.close()

if __name__ == "__main__":
    asyncio.run(test_defense())
