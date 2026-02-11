"""Check database content directly with asyncpg."""
import asyncio
import asyncpg
from src.config import settings

async def check_db():
    print(f"Connecting to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db} as {settings.postgres_user}...")
    try:
        conn = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            host=settings.postgres_host,
            port=settings.postgres_port
        )
        print("Connected successfully!")
        
        # Check count
        count = await conn.fetchval("SELECT COUNT(*) FROM products")
        print(f"\nTotal Products in DB: {count}")
        
        if count > 0:
            # Check a few rows
            rows = await conn.fetch(
                """
                SELECT 
                    model_name, 
                    watts_int, 
                    ohms_int, 
                    embedding IS NOT NULL as has_vector 
                FROM products 
                LIMIT 5
                """
            )
            print("\nSample Data:")
            for row in rows:
                print(f"- {row['model_name']}: {row['watts_int']}W, {row['ohms_int']} ohms, Vector={row['has_vector']}")
        else:
            print("\nTable is empty! You need to run the ETL pipeline load step.")
            
        await conn.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
