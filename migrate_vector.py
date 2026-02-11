"""Migrate database to use 1024-dimension vectors for bge-m3."""
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
        
        # 1. Drop dependent views/indexes first
        print("Dropping dependent views/indexes...")
        await conn.execute("DROP VIEW IF EXISTS products_with_embeddings CASCADE")
        await conn.execute("DROP INDEX IF EXISTS idx_products_embedding_ivfflat")
        
        # 2. Alter column type to vector(1024)
        print("Altering products.embedding to vector(1024)...")
        # Need to use USING to convert if data exists, but it's likely empty or we can just cast (but data is incompatible).
        # Since table has only 86 rows and embeddings are broken/null, we can just drop/recreate column or use explicit CAST if compatible (no).
        # Actually, simpler to drop column and add back. Since data is invalid/null anyway.
        await conn.execute("ALTER TABLE products DROP COLUMN IF EXISTS embedding")
        await conn.execute("ALTER TABLE products ADD COLUMN embedding vector(1024)")
        
        # 3. Alter embedding_cache table too
        print("Altering embedding_cache.embedding to vector(1024)...")
        await conn.execute("ALTER TABLE embedding_cache DROP COLUMN IF EXISTS embedding")
        await conn.execute("ALTER TABLE embedding_cache ADD COLUMN embedding vector(1024)")
        
        # 4. Recreate View products_with_embeddings
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
