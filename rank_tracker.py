import aiohttp
import sqlite3
import logging
import sys
from typing import Optional, List, Dict, Tuple
import asyncio
from datetime import datetime
from pathlib import Path

from config_manager import ConfigManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class RankTracker:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.config
        self.initialize_database()

    def initialize_database(self) -> None:
        """Initialize the SQLite database and create tables if they don't exist"""
        try:
            # Ensure the database directory exists
            db_path = Path(self.config.database.path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(self.config.database.path)
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
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise

    async def fetch_rank_data(self) -> Optional[List[Dict]]:
        """Fetch current rank data from Riot API"""
        url = (f'https://{self.config.riot.region}.api.riotgames.com/lol/league/v4/'
               f'entries/by-summoner/{self.config.riot.summoner_id}')
        
        headers = {"X-Riot-Token": self.config.riot.api_key}
        logger.info(f"Fetching rank data from: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Raw rank data response: {data}")
                        if not data:  # Empty array check
                            logger.error("Received empty rank data from API")
                            return None
                        return data
                    else:
                        logger.error(f"Failed to fetch rank data: Status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching rank data: {e}")
            return None

    async def get_current_rank(self, queue_type: str) -> Optional[Tuple[str, str, int]]:
        """Get the current rank information for a specific queue type"""
        try:
            conn = sqlite3.connect(self.config.database.path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tier, rank, lp, timestamp
                FROM rank_data
                WHERE queue_type = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (queue_type,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                logger.info(f"Current rank for {queue_type}: {result}")
                return result[0], result[1], result[2]
            logger.info(f"No current rank found for {queue_type}")
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Database error in get_current_rank: {e}")
            return None

    async def store_rank_data(self, queue_type: str, tier: str, rank: str, 
                            lp: int, match_id: Optional[str] = None) -> bool:
        """Store rank data in the database"""
        try:
            conn = sqlite3.connect(self.config.database.path)
            cursor = conn.cursor()

            # Check if values have changed
            current_rank = await self.get_current_rank(queue_type)
            if current_rank:
                current_tier, current_rank_div, current_lp = current_rank
                if (current_tier == tier and 
                    current_rank_div == rank and 
                    current_lp == lp):
                    logger.info(f"No rank change detected for {queue_type}")
                    conn.close()
                    return False

            # Insert new rank data
            cursor.execute('''
                INSERT INTO rank_data (match_id, queue_type, tier, rank, lp)
                VALUES (?, ?, ?, ?, ?)
            ''', (match_id, queue_type, tier, rank, lp))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored new rank data for {queue_type}: {tier} {rank} {lp}LP")
            return True

        except sqlite3.Error as e:
            logger.error(f"Database error in store_rank_data: {e}")
            return False

    async def track_rank(self, match_id: Optional[str] = None) -> None:
        """Main function to track and update rank data"""
        try:
            rank_data = await self.fetch_rank_data()
            if not rank_data:
                logger.error("No rank data received from API")
                return

            # Process both solo and flex queue data
            solo_queue = next((entry for entry in rank_data 
                             if entry['queueType'] == 'RANKED_SOLO_5x5'), None)
            flex_queue = next((entry for entry in rank_data 
                             if entry['queueType'] == 'RANKED_FLEX_SR'), None)

            for queue_data in [solo_queue, flex_queue]:
                if queue_data:
                    try:
                        queue_type = queue_data['queueType']
                        tier = queue_data['tier']
                        rank = queue_data['rank']
                        lp = queue_data['leaguePoints']
                        
                        logger.info(f"Processing {queue_type} data - Tier: {tier}, Rank: {rank}, LP: {lp}")
                        await self.store_rank_data(
                            queue_type=queue_type,
                            tier=tier,
                            rank=rank,
                            lp=lp,
                            match_id=match_id
                        )
                    except KeyError as e:
                        logger.error(f"Missing required field in queue data: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error in track_rank: {e}")

    async def get_rank_history(self, days: int = 30) -> List[Tuple]:
        """Get rank history for a specified number of days"""
        try:
            conn = sqlite3.connect(self.config.database.path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tier, rank, lp, timestamp, match_id
                FROM rank_data
                WHERE timestamp >= datetime('now', '-? days')
                ORDER BY timestamp ASC
            ''', (days,))
            
            result = cursor.fetchall()
            conn.close()
            
            return result
            
        except sqlite3.Error as e:
            logger.error(f"Database error in get_rank_history: {e}")
            return []

async def track_rank_after_game(match_id: str) -> None:
    """Convenience function to track rank after a game"""
    config_manager = ConfigManager()
    tracker = RankTracker(config_manager)
    await tracker.track_rank(match_id)

async def track_rank_hourly() -> None:
    """Convenience function to track rank on an hourly basis"""
    config_manager = ConfigManager()
    tracker = RankTracker(config_manager)
    await tracker.track_rank()

if __name__ == "__main__":
    # When run directly, track rank hourly
    asyncio.run(track_rank_hourly())