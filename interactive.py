"""
Interactive Q&A with Bose Product Engine.
Provides a command-line REPL for testing queries in real-time.
"""

import asyncio
import sys
import io
import logging

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configure logging (suppress INFO logs for cleaner output)
logging.basicConfig(level=logging.WARNING)

from src.rag.engine import get_engine

async def interactive_qa():
    print("="*60)
    print("BOSE PRODUCT ENGINE - Interactive Q&A")
    print("="*60)
    print()
    print("Ask technical questions about Bose Professional products.")
    print("The system will classify and route your query automatically.")
    print()
    print("Examples:")
    print("  - What is the power of DesignMax DM3C?")
    print("  - Find 70V speakers for conference rooms")
    print("  - Can I connect 4 speakers at 30W to a 150W transformer?")
    print()
    print("Type 'help' for more commands, 'exit' or 'quit' to stop.")
    print("="*60)
    print()
    
    engine = await get_engine()
    
    while True:
        try:
            # Get user input
            query = input("\n🎤 You: ").strip()
            
            if not query:
                continue
                
            # Handle commands
            if query.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye! 👋")
                break
                
            if query.lower() == 'help':
                print("\nAvailable Commands:")
                print("  help    - Show this help message")
                print("  clear   - Clear screen")
                print("  stats   - Show system statistics")
                print("  exit    - Exit the program")
                print("\nQuery Types:")
                print("  Direct Lookup    - Ask about specific product specs")
                print("  Semantic Search  - Find products matching criteria")
                print("  Calculation      - Electrical calculations (70V, impedance)")
                print("  Purchase Intent  - Pricing/buying (BLOCKED)")
                print("  Domain Violation - Competitor mentions (BLOCKED)")
                continue
                
            if query.lower() == 'clear':
                print("\n" * 50)
                continue
                
            if query.lower() == 'stats':
                print("\n📊 System Statistics:")
                # Get product count
                from src.database import get_pool
                pool = await get_pool()
                async with pool.acquire() as conn:
                    count = await conn.fetchval("SELECT COUNT(*) FROM products")
                    categories = await conn.fetch(
                        "SELECT category, COUNT(*) as cnt FROM products GROUP BY category ORDER BY cnt DESC"
                    )
                print(f"  Total Products: {count}")
                print(f"  Categories:")
                for row in categories:
                    print(f"    - {row['category']}: {row['cnt']}")
                continue
            
            # Process query
            print("\n🤖 Assistant: ", end="", flush=True)
            result = await engine.query(query)
            
            # Display result
            print(result.answer)
            
            # Show metadata
            print(f"\n   [Type: {result.query_type} | Confidence: {result.confidence:.2f}]", end="")
            if result.products_used:
                print(f" [Products: {', '.join(result.products_used[:3])}]", end="")
            print()
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit.")
            continue
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            logging.exception("Query error")
    
    await engine.close()

if __name__ == "__main__":
    try:
        asyncio.run(interactive_qa())
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
