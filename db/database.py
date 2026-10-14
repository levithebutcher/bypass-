"""Async SQLite database for caching bypassed URLs and tracking statistics."""

import time
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any
import aiosqlite
from config import DATABASE_PATH, CACHE_ENABLED, CACHE_TTL_DAYS

logger = logging.getLogger(__name__)


def _hash_url(url: str) -> str:
    """Generates a SHA-256 hash for a given URL."""
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


class Database:
    """Manages SQLite operations using aiosqlite."""

    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self) -> None:
        """Initializes tables and indexes."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS link_cache (
                    url_hash TEXT PRIMARY KEY,
                    original_url TEXT NOT NULL,
                    bypassed_url TEXT NOT NULL,
                    bypasser_name TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    hits INTEGER NOT NULL DEFAULT 1
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    first_seen INTEGER NOT NULL,
                    last_seen INTEGER NOT NULL,
                    total_requests INTEGER NOT NULL DEFAULT 1
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_created ON link_cache (created_at)
            """)
            await db.commit()
        logger.info("Database initialized at %s", self.db_path)

    async def get_cached(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Retrieves cached bypassed link if still within TTL.
        Returns: (bypassed_url, bypasser_name) or None.
        """
        if not CACHE_ENABLED:
            return None

        url_hash = _hash_url(url)
        now = int(time.time())
        cutoff = now - (CACHE_TTL_DAYS * 86400)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT bypassed_url, bypasser_name, created_at FROM link_cache WHERE url_hash = ?",
                (url_hash,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    bypassed_url, bypasser_name, created_at = row
                    if created_at >= cutoff:
                        # Increment hit count
                        await db.execute(
                            "UPDATE link_cache SET hits = hits + 1 WHERE url_hash = ?",
                            (url_hash,)
                        )
                        await db.commit()
                        return bypassed_url, bypasser_name
                    else:
                        # Expired entry
                        await db.execute(
                            "DELETE FROM link_cache WHERE url_hash = ?",
                            (url_hash,)
                        )
                        await db.commit()

        return None

    async def set_cached(self, original_url: str, bypassed_url: str, bypasser_name: str) -> None:
        """Saves a successfully bypassed URL to cache."""
        if not CACHE_ENABLED or not bypassed_url:
            return

        url_hash = _hash_url(original_url)
        now = int(time.time())

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO link_cache (url_hash, original_url, bypassed_url, bypasser_name, created_at, hits)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(url_hash) DO UPDATE SET
                    bypassed_url = excluded.bypassed_url,
                    bypasser_name = excluded.bypasser_name,
                    created_at = excluded.created_at,
                    hits = hits + 1
            """, (url_hash, original_url, bypassed_url, bypasser_name, now))
            await db.commit()

    async def record_user(self, user_id: int) -> None:
        """Updates user usage metrics."""
        now = int(time.time())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_stats (user_id, first_seen, last_seen, total_requests)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    total_requests = total_requests + 1
            """, (user_id, now, now))
            await db.commit()

    async def get_stats(self) -> Dict[str, Any]:
        """Calculates global service statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            # Total unique links cached
            async with db.execute("SELECT COUNT(*), SUM(hits) FROM link_cache") as cur:
                cache_row = await cur.fetchone()
                total_unique_cached = cache_row[0] or 0
                total_cache_hits = cache_row[1] or 0

            # Total unique users
            async with db.execute("SELECT COUNT(*), SUM(total_requests) FROM user_stats") as cur:
                user_row = await cur.fetchone()
                total_users = user_row[0] or 0
                total_requests = user_row[1] or 0

            # Top bypassers
            async with db.execute("""
                SELECT bypasser_name, COUNT(*) as cnt
                FROM link_cache
                GROUP BY bypasser_name
                ORDER BY cnt DESC
                LIMIT 5
            """) as cur:
                top_bypassers = await cur.fetchall()

        return {
            "total_users": total_users,
            "total_requests": total_requests,
            "unique_links_cached": total_unique_cached,
            "total_cache_hits": total_cache_hits,
            "top_bypassers": top_bypassers,
        }


# Global database instance
db = Database()
