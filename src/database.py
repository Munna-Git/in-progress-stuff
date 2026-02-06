"""
Async PostgreSQL database connection manager using asyncpg.
Provides connection pooling and context managers for safe usage.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

import asyncpg
from asyncpg import Pool, Connection

from src.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Async database connection manager with connection pooling.
    
    Usage:
        db = DatabaseManager()
        await db.initialize()
        
        async with db.connection() as conn:
            result = await conn.fetch("SELECT * FROM products")
        
        await db.close()
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
    ):
        """Initialize database manager with connection parameters."""
        self.host = host or settings.postgres_host
        self.port = port or settings.postgres_port
        self.user = user or settings.postgres_user
        self.password = password or settings.postgres_password
        self.database = database or settings.postgres_db
        self.min_size = min_size or settings.min_db_connections
        self.max_size = max_size or settings.max_db_connections
        
        self._pool: Optional[Pool] = None
        self._lock = asyncio.Lock()
    
    @property
    def is_connected(self) -> bool:
        """Check if pool is initialized and not closed."""
        return self._pool is not None and not self._pool._closed
    
    async def initialize(self) -> None:
        """
        Initialize the connection pool.
        Safe to call multiple times - will only initialize once.
        """
        async with self._lock:
            if self._pool is not None:
                return
            
            logger.info(
                f"Initializing database pool: {self.host}:{self.port}/{self.database}"
            )
            
            try:
                self._pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    command_timeout=settings.query_timeout_seconds,
                    # Enable pgvector type support
                    init=self._init_connection,
                )
                logger.info(f"Database pool initialized with {self.min_size}-{self.max_size} connections")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise
    
    async def _init_connection(self, conn: Connection) -> None:
        """
        Initialize each connection with custom type codecs.
        Called automatically by asyncpg for each new connection.
        """
        # Register vector type codec for pgvector
        await conn.set_type_codec(
            'vector',
            encoder=self._encode_vector,
            decoder=self._decode_vector,
            schema='public',
            format='text',
        )
    
    @staticmethod
    def _encode_vector(vector: list[float]) -> str:
        """Encode Python list to PostgreSQL vector format."""
        return f"[{','.join(str(v) for v in vector)}]"
    
    @staticmethod
    def _decode_vector(data: str) -> list[float]:
        """Decode PostgreSQL vector to Python list."""
        # Remove brackets and split by comma
        return [float(x) for x in data.strip('[]').split(',')]
    
    async def close(self) -> None:
        """Close the connection pool."""
        async with self._lock:
            if self._pool is not None:
                logger.info("Closing database pool")
                await self._pool.close()
                self._pool = None
    
    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[Connection, None]:
        """
        Get a connection from the pool as an async context manager.
        
        Usage:
            async with db.connection() as conn:
                await conn.execute("...")
        """
        if not self.is_connected:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Connection, None]:
        """
        Get a connection with an active transaction.
        
        Usage:
            async with db.transaction() as conn:
                await conn.execute("INSERT ...")
                await conn.execute("UPDATE ...")
                # Commits on success, rolls back on exception
        """
        async with self.connection() as conn:
            async with conn.transaction():
                yield conn
    
    async def execute(self, query: str, *args: Any) -> str:
        """Execute a query and return status."""
        async with self.connection() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        """Fetch multiple rows."""
        async with self.connection() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        """Fetch a single row."""
        async with self.connection() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args: Any) -> Any:
        """Fetch a single value."""
        async with self.connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def executemany(self, query: str, args: list[tuple]) -> None:
        """Execute a query with multiple parameter sets."""
        async with self.connection() as conn:
            await conn.executemany(query, args)
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            result = await self.fetchval("SELECT 1")
            return result == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global database instance
db = DatabaseManager()


async def get_db() -> DatabaseManager:
    """
    Get the global database manager instance.
    Initializes pool if not already done.
    """
    if not db.is_connected:
        await db.initialize()
    return db


@asynccontextmanager
async def get_connection() -> AsyncGenerator[Connection, None]:
    """
    Convenience function to get a database connection.
    
    Usage:
        async with get_connection() as conn:
            await conn.fetch("SELECT * FROM products")
    """
    database = await get_db()
    async with database.connection() as conn:
        yield conn


@asynccontextmanager
async def get_transaction() -> AsyncGenerator[Connection, None]:
    """
    Convenience function to get a transactional connection.
    
    Usage:
        async with get_transaction() as conn:
            await conn.execute("INSERT ...")
    """
    database = await get_db()
    async with database.transaction() as conn:
        yield conn
