"""Check EM90 lookup."""
import asyncio
import json
from src.database import get_db

async def main():
    db = await get_db()
    row = await db.fetchrow(
        "SELECT model_name, specs, ai_summary, pdf_source FROM products WHERE UPPER(model_name) LIKE UPPER('%EM90%') ORDER BY model_name LIMIT 1"
    )
    if row:
        print(f"Model: {row['model_name']}")
        specs = row['specs']
        if isinstance(specs, str):
            specs = json.loads(specs)
        print(f"Specs keys: {list(specs.keys())}")
        print(f"sensitivity_db: {specs.get('sensitivity_db', 'NOT PRESENT')}")
        print(f"Full specs: {json.dumps(specs, indent=2, default=str)}")
    else:
        print("EM90 not found even with LIKE")
    await db.close()

asyncio.run(main())
