
import asyncio
import logging
from src.database import get_db
from src.rag.router import QueryRouter

async def debug():
    # 1. Check DB Content
    db = await get_db()
    
    print("\n--- DB Content Check ---")
    rows = await db.fetch("SELECT model_name, voltage_type, category FROM products LIMIT 20")
    for row in rows:
        print(f"{row['model_name']}: V='{row['voltage_type']}', C='{row['category']}'")
        
    print("\n--- SQL Filter Check ---")
    # Simulate the query used in retrieval
    count = await db.fetchval("""
        SELECT COUNT(*) 
        FROM products 
        WHERE voltage_type ILIKE '%70V%' 
          AND category ILIKE 'loudspeaker'
    """)
    print(f"Products matching ILIKE '%70V%' AND 'loudspeaker': {count}")

    # 2. Check Router Extraction
    print("\n--- Router Extraction ---")
    router = QueryRouter(use_llm=False)
    query = "Find 70V ceiling speakers for conference rooms"
    filters = router.extract_filters(query)
    print(f"Query: {query}")
    print(f"Extracted Filters: {filters}")
    
    await router.close()

if __name__ == "__main__":
    asyncio.run(debug())
