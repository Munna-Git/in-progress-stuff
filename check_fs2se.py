"""Check FS2SE in DB."""
import asyncio
from src.database import get_db

async def main():
    db = await get_db()
    # Check exact match
    row = await db.fetchrow("SELECT model_name FROM products WHERE model_name = 'FS2SE'")
    if row:
        print("FS2SE found (exact match)")
    else:
        print("FS2SE not found (exact match)")
        
    # Check partial
    rows = await db.fetch("SELECT model_name FROM products WHERE model_name ILIKE '%FS2SE%'")
    if rows:
        print(f"Found partial matches: {[r['model_name'] for r in rows]}")
    else:
        print("FS2SE not found (partial match)")
        
    await db.close()

asyncio.run(main())
