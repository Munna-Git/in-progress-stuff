"""Migrate database to include watts_int and ohms_int columns."""
import asyncio
import asyncpg
from src.config import settings

async def migrate():
    print(f"Connecting to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}...")
    try:
        conn = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            host=settings.postgres_host,
            port=settings.postgres_port
        )
        print("Connected.")
        
        # 1. Drop generated watts_int column (cascade to drop indexes/views)
        print("Dropping existing watts_int column (cascade)...")
        await conn.execute("ALTER TABLE products DROP COLUMN IF EXISTS watts_int CASCADE")
        
        # 2. Add columns
        print("Adding watts_int and ohms_int columns...")
        await conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS watts_int INTEGER")
        await conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS ohms_int INTEGER")
        
        # 3. Recreate Index
        print("Recreating index on watts_int...")
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_products_watts ON products(watts_int) WHERE watts_int IS NOT NULL"
        )
        
        # 4. Recreate View (category_stats)
        print("Recreating category_stats view...")
        await conn.execute("""
            CREATE OR REPLACE VIEW category_stats AS
            SELECT 
                category,
                COUNT(*) as product_count,
                AVG(watts_int) as avg_watts,
                MIN(watts_int) as min_watts,
                MAX(watts_int) as max_watts
            FROM products
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY product_count DESC
        """)
        
        # 5. Recreate products_with_embeddings view (it was likely dropped by cascade too)
        print("Recreating products_with_embeddings view...")
        await conn.execute("""
            CREATE OR REPLACE VIEW products_with_embeddings AS
            SELECT 
                id,
                model_name,
                category,
                series,
                watts_int,
                ohms_int,
                voltage_type,
                ai_summary,
                embedding IS NOT NULL as has_embedding
            FROM products
        """)
        
        print("Migration complete!")
        await conn.close()
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
