"""Verify fixes for semantic search and edge cases."""
import asyncio
from src.rag.engine import query

async def main():
    print("\n--- Test 1: Semantic Search (Should return products, not 'Sorry') ---")
    q1 = "Find 70V speakers for conference rooms"
    ans1 = await query(q1)
    print(f"Query: {q1}")
    print(f"Answer:\n{ans1.answer[:200]}...")
    print(f"Products Used: {ans1.products_used}")
    
    print("\n\n--- Test 2: Edge Case (Should say 'couldn't find') ---")
    q2 = "What's the wattage of a nonexistent model XYZ123?"
    ans2 = await query(q2)
    print(f"Query: {q2}")
    print(f"Answer:\n{ans2.answer}")
    
    # Check if improved messages are used
    if "couldn't find" in ans2.answer.lower() or "not found" in ans2.answer.lower():
        print("\nSUCCESS: Edge case handled correctly.")
    else:
        print("\nFAILURE: Edge case message incorrect.")

if __name__ == "__main__":
    asyncio.run(main())
