"""
Test script for the RAG Query Engine.
Tests all 4 query types: direct lookup, semantic search, similarity, and calculation.

Usage:
    python test_query_engine.py              # Run all automated tests
    python test_query_engine.py --interactive # Interactive REPL mode
"""

import asyncio
import json
import logging
import sys
import time
import io

# Fix Windows console encoding for Unicode characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.WARNING, format="%(levelname)s - %(message)s")


async def test_direct_lookup(engine):
    """Test 1: Direct product lookup by model name."""
    print("\n" + "=" * 60)
    print("TEST 1: Direct Product Lookup")
    print("=" * 60)

    queries = [
        "What are the specs of the DesignMax DM3C?",
        "Tell me about the AMM108",
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        start = time.time()
        result = await engine.query(q)
        elapsed = time.time() - start

        print(f"  Type: {result.query_type}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Answer: {result.answer[:200]}...")
        if result.products_used:
            print(f"  Products: {result.products_used}")
        if result.citations:
            print(f"  Citations: {len(result.citations)}")
        print(f"  {'PASS' if result.answer and 'error' not in result.query_type else 'FAIL'}")


async def test_semantic_search(engine):
    """Test 2: Semantic vector search."""
    print("\n" + "=" * 60)
    print("TEST 2: Semantic Search")
    print("=" * 60)

    queries = [
        "Find speakers suitable for conference rooms",
        "High power ceiling speakers",
        "Outdoor speakers with weather resistance",
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        start = time.time()
        result = await engine.query(q)
        elapsed = time.time() - start

        print(f"  Type: {result.query_type}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Products: {result.products_used}")
        print(f"  Answer: {result.answer[:200]}...")
        print(f"  {'PASS' if result.products_used else 'FAIL'}")


async def test_similarity(engine):
    """Test 3: Find similar products."""
    print("\n" + "=" * 60)
    print("TEST 3: Similar Products")
    print("=" * 60)

    model = "AMM.AMM108"
    print(f"\nFinding products similar to: {model}")
    start = time.time()
    results = await engine.find_similar(model, limit=5)
    elapsed = time.time() - start

    print(f"  Time: {elapsed:.2f}s")
    print(f"  Found: {len(results)} similar products")
    for r in results:
        print(f"    - {r.model_name} (similarity: {r.similarity_score:.3f})")
    print(f"  {'PASS' if results else 'FAIL'}")


async def test_calculation(engine):
    """Test 4: Electrical calculation."""
    print("\n" + "=" * 60)
    print("TEST 4: Electrical Calculation")
    print("=" * 60)

    queries = [
        "Can I connect 4 speakers at 30 watts each to a 150 watt transformer?",
        "What is the impedance of 3 speakers at 8 ohms in parallel?",
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        start = time.time()
        result = await engine.query(q)
        elapsed = time.time() - start

        print(f"  Type: {result.query_type}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Answer: {result.answer[:300]}")
        print(f"  {'PASS' if 'error' not in result.query_type else 'FAIL'}")


async def test_retriever_stats(engine):
    """Show database statistics."""
    print("\n" + "=" * 60)
    print("DATABASE STATISTICS")
    print("=" * 60)

    stats = await engine.retriever.get_stats()
    print(f"  Total products:      {stats['total_products']}")
    print(f"  With embeddings:     {stats['with_embeddings']}")
    print(f"  Categories:          {json.dumps(stats['by_category'], indent=4)}")


async def interactive_mode(engine):
    """Interactive REPL for testing queries."""
    print("\n" + "=" * 60)
    print("INTERACTIVE MODE")
    print("Type queries to test. Commands: /stats, /similar <model>, /quit")
    print("=" * 60)

    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query:
            continue
        if query.lower() in ("/quit", "/exit", "/q"):
            break
        if query.lower() == "/stats":
            await test_retriever_stats(engine)
            continue
        if query.lower().startswith("/similar "):
            model = query[9:].strip()
            results = await engine.find_similar(model, limit=5)
            for r in results:
                print(f"  - {r.model_name} (score: {r.similarity_score:.3f})")
            continue

        start = time.time()
        result = await engine.query(query)
        elapsed = time.time() - start

        print(f"\n[{result.query_type}] ({elapsed:.2f}s)")
        print(result.answer)
        if result.products_used:
            print(f"\nProducts referenced: {result.products_used}")
        if result.citations:
            print(f"Citations: {len(result.citations)}")


async def main():
    from src.rag.engine import QueryEngine

    interactive = "--interactive" in sys.argv or "-i" in sys.argv

    print("Initializing RAG Query Engine...")
    engine = QueryEngine()

    try:
        if interactive:
            # Show stats then drop into REPL
            await test_retriever_stats(engine)
            await interactive_mode(engine)
        else:
            # Run all automated tests
            await test_retriever_stats(engine)
            await test_direct_lookup(engine)
            await test_semantic_search(engine)
            await test_similarity(engine)
            await test_calculation(engine)

            print("\n" + "=" * 60)
            print("ALL TESTS COMPLETE")
            print("=" * 60)
    finally:
        await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
