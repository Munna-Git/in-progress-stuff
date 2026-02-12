"""Check AM10/60 with LIKE."""
import asyncio
from src.database import get_db

async def main():
    db = await get_db()
    row = await db.fetchrow(
        "SELECT model_name FROM products WHERE model_name ILIKE '%AM10/60%'"
    )
    if row:
        print(f"Found: {row['model_name']}")
    else:
        print("AM10/60 not found even with LIKE")
    
    # Check what IS there
    rows = await db.fetch("SELECT model_name FROM products WHERE model_name ILIKE '%Arena%' LIMIT 5")
    print("Sample ArenaMatch models:")
    for r in rows:
        print(f"- {r['model_name']}")
        
    await db.close()

asyncio.run(main())
