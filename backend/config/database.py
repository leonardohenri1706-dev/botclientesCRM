import asyncpg
from config.settings import get_settings
from typing import Optional, Any
from contextlib import asynccontextmanager

_settings = get_settings()
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            _settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
    return _pool


@asynccontextmanager
async def get_connection():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def execute(query: str, *args) -> str:
    async with get_connection() as conn:
        return await conn.execute(query, *args)


async def fetch(query: str, *args) -> list[asyncpg.Record]:
    async with get_connection() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args) -> Optional[asyncpg.Record]:
    async with get_connection() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args) -> Any:
    async with get_connection() as conn:
        return await conn.fetchval(query, *args)


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None