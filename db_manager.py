"""
db_manager.py
Database manager with connection pooling and async support.
"""
import json
import sqlite3
import aiosqlite
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
import time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class DBManager:
    """
    A manager for database operations with connection pooling.
    """
    def __init__(self, db_path: str, max_connections: int = 5):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database
            max_connections: Maximum number of connections in the pool
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.connection_pool = asyncio.Queue(maxsize=max_connections)
        self.active_connections = 0
        
        # Ensure the database directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the database schema
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema synchronously."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create rank_data table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rank_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT UNIQUE,
                    queue_type TEXT,
                    tier TEXT NOT NULL,
                    rank TEXT NOT NULL,
                    lp INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create summoner_cache table for caching summoner data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS summoner_cache (
                    puuid TEXT PRIMARY KEY,
                    summoner_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    data TEXT NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create indices for efficient querying
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rank_queue ON rank_data(queue_type);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rank_timestamp ON rank_data(timestamp);')
            
            conn.commit()
            conn.close()
            logger.info("Database schema initialized")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise

    async def _get_connection(self) -> aiosqlite.Connection:
        """
        Get a connection from the pool, or create a new one if needed.
        
        Returns:
            aiosqlite.Connection: Database connection
        """
        try:
            # Try to get a connection from the pool
            return await asyncio.wait_for(self.connection_pool.get(), timeout=0.1)
        except asyncio.TimeoutError:
            # If the pool is empty and we haven't reached max connections, create a new one
            if self.active_connections < self.max_connections:
                self.active_connections += 1
                try:
                    conn = await aiosqlite.connect(self.db_path)
                    # Enable foreign keys
                    await conn.execute("PRAGMA foreign_keys = ON")
                    # Set busy timeout to avoid database locked errors
                    await conn.execute("PRAGMA busy_timeout = 5000")
                    return conn
                except Exception as e:
                    self.active_connections -= 1
                    logger.error(f"Error creating database connection: {e}")
                    raise
            else:
                # If we've reached max connections, wait for one to become available
                return await self.connection_pool.get()

    async def _release_connection(self, conn: aiosqlite.Connection) -> None:
        """
        Release a connection back to the pool.
        
        Args:
            conn: The connection to release
        """
        try:
            await self.connection_pool.put(conn)
        except Exception as e:
            logger.error(f"Error releasing connection: {e}")
            self.active_connections -= 1
            await conn.close()

    async def execute(self, query: str, params: tuple = ()) -> Optional[int]:
        """
        Execute a query and return the last row id.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Optional[int]: Last row id if applicable
        """
        conn = await self._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Database execution error: {query}, {params}, {e}")
            raise
        finally:
            await self._release_connection(conn)

    async def executemany(self, query: str, params_list: List[tuple]) -> None:
        """
        Execute many queries.
        
        Args:
            query: SQL query
            params_list: List of query parameters
        """
        conn = await self._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.executemany(query, params_list)
                await conn.commit()
        except Exception as e:
            logger.error(f"Database executemany error: {query}, {e}")
            raise
        finally:
            await self._release_connection(conn)

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[tuple]:
        """
        Fetch one row.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Optional[tuple]: Result row or None
        """
        conn = await self._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Database fetch_one error: {query}, {params}, {e}")
            raise
        finally:
            await self._release_connection(conn)

    async def fetch_all(self, query: str, params: tuple = ()) -> List[tuple]:
        """
        Fetch all rows.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List[tuple]: Result rows
        """
        conn = await self._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Database fetch_all error: {query}, {params}, {e}")
            raise
        finally:
            await self._release_connection(conn)

    async def close_all(self) -> None:
        """Close all connections in the pool."""
        while not self.connection_pool.empty():
            conn = await self.connection_pool.get()
            await conn.close()
        
        logger.info("All database connections closed")

    # Specific methods for rank tracking

    async def store_rank_data(self, match_id: Optional[str], queue_type: str, 
                             tier: str, rank: str, lp: int) -> bool:
        """
        Store rank data in the database.
        
        Args:
            match_id: Optional match ID
            queue_type: Queue type (e.g., 'RANKED_SOLO_5x5')
            tier: Rank tier (e.g., 'GOLD')
            rank: Rank division (e.g., 'IV')
            lp: League points
            
        Returns:
            bool: True if data was inserted, False otherwise
        """
        try:
            # Check if current rank data exists and if it's the same
            current = await self.get_latest_rank(queue_type)
            if current and current[0] == tier and current[1] == rank and current[2] == lp:
                logger.info(f"No rank change detected for {queue_type}")
                return False
            
            # Insert new rank data
            await self.execute(
                '''
                INSERT INTO rank_data (match_id, queue_type, tier, rank, lp)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (match_id, queue_type, tier, rank, lp)
            )
            
            logger.info(f"Stored new rank data for {queue_type}: {tier} {rank} {lp}LP")
            return True
            
        except Exception as e:
            logger.error(f"Error storing rank data: {e}")
            return False

    async def get_latest_rank(self, queue_type: str) -> Optional[Tuple[str, str, int]]:
        """
        Get the latest rank information for a queue type.
        
        Args:
            queue_type: Queue type (e.g., 'RANKED_SOLO_5x5')
            
        Returns:
            Optional[Tuple[str, str, int]]: (tier, rank, lp) or None
        """
        try:
            result = await self.fetch_one(
                '''
                SELECT tier, rank, lp, timestamp
                FROM rank_data
                WHERE queue_type = ?
                ORDER BY timestamp DESC
                LIMIT 1
                ''',
                (queue_type,)
            )
            
            if result:
                return (result[0], result[1], result[2])
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest rank: {e}")
            return None

    async def get_rank_history(self, queue_type: str = None, days: int = 30) -> List[tuple]:
        """
        Get rank history for a specified period.
        
        Args:
            queue_type: Optional queue type filter
            days: Number of days to look back
            
        Returns:
            List[tuple]: Rank history records
        """
        try:
            if queue_type:
                return await self.fetch_all(
                    '''
                    SELECT tier, rank, lp, timestamp, match_id
                    FROM rank_data
                    WHERE queue_type = ? AND timestamp >= datetime('now', '-? days')
                    ORDER BY timestamp ASC
                    ''',
                    (queue_type, days)
                )
            else:
                return await self.fetch_all(
                    '''
                    SELECT tier, rank, lp, timestamp, match_id
                    FROM rank_data
                    WHERE timestamp >= datetime('now', '-? days')
                    ORDER BY timestamp ASC
                    ''',
                    (days,)
                )
        except Exception as e:
            logger.error(f"Error getting rank history: {e}")
            return []
            
    async def store_summoner_data(self, puuid: str, summoner_id: str, 
                                 account_id: str, name: str, data: Dict) -> None:
        """
        Store summoner data in cache.
        
        Args:
            puuid: Player UUID
            summoner_id: Summoner ID
            account_id: Account ID
            name: Summoner name
            data: Full summoner data
        """
        try:
            json_data = json.dumps(data)
            await self.execute(
                '''
                INSERT OR REPLACE INTO summoner_cache 
                (puuid, summoner_id, account_id, name, data, last_updated)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                ''',
                (puuid, summoner_id, account_id, name, json_data)
            )
        except Exception as e:
            logger.error(f"Error storing summoner data: {e}")
            
    async def get_summoner_by_name(self, name: str, max_age_hours: int = 24) -> Optional[Dict]:
        """
        Get summoner data from cache by name.
        
        Args:
            name: Summoner name
            max_age_hours: Maximum age of cached data in hours
            
        Returns:
            Optional[Dict]: Summoner data or None
        """
        try:
            result = await self.fetch_one(
                '''
                SELECT data, last_updated
                FROM summoner_cache
                WHERE LOWER(name) = LOWER(?)
                ''',
                (name,)
            )
            
            if result:
                data_str, last_updated = result
                # Check if data is still fresh
                last_updated_time = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - last_updated_time < timedelta(hours=max_age_hours):
                    return json.loads(data_str)
            return None
            
        except Exception as e:
            logger.error(f"Error getting summoner by name: {e}")
            return None