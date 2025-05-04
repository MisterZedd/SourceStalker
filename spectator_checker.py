"""
spectator_checker.py
Improved implementation of the SpectatorChecker class with better error handling and rate limiting.
"""
import asyncio
import logging
import sys
from typing import Optional, Tuple, Dict
from dataclasses import asdict
from datetime import datetime

from config_manager import ConfigManager
from riot_api_client import RiotAPIClient
from db_manager import DBManager
from utils.gamemodes import get_queue_type

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class SpectatorChecker:
    """
    Class for checking a summoner's active game and tracking results.
    Improved with proper error handling and rate limiting.
    """
    def __init__(self, config_manager: ConfigManager):
        """Initialize the spectator checker with configuration."""
        self.config_manager = config_manager  # Store the entire config_manager
        self.config = config_manager.config
        self.game_in_progress = False
        self.current_game_id = None
        self.current_queue_type = None
        self.pre_game_queue_type = None
        self.pre_game_lp = None
        self.game_check_lock = asyncio.Lock()  # Lock to prevent race conditions
        
        # Initialize API client
        self.api_client = RiotAPIClient(
            api_key=self.config.riot.api_key,
            region=self.config.riot.region,
            platform=self.config.riot.platform
        )
        
        # Initialize database manager
        self.db_manager = DBManager(self.config.database.path)
        
        # Emoji mappings
        self.emoji_map = {
            'win': '<:Victory:1317234409916731472>',
            'loss': '<:Defeat:1317234398202036314>',
            'monitoring': '<:monitoring:1317234422503833691>',
            'deaths': '<:death:1317234404543954944>',
            'copium': '<:Copium:1317234415851671642>',
            'lp_gain': '<:lpgain:1317242337948340294>',
            'lp_loss': '<:lploss:1317242323465142312>'
        }

    async def initialize_summoner_id(self) -> bool:
        """Initialize summoner ID and PUUID if not already set"""
        if self.config.riot.summoner_id:
            # If we have the summoner ID but not PUUID, get the PUUID
            if not self.config.riot.puuid:
                logger.info("PUUID not found in config, fetching it")
                puuid = await self.api_client.get_puuid_by_summoner_id(self.config.riot.summoner_id)
                if puuid:
                    self.config.riot.puuid = puuid
                    logger.info(f"Retrieved PUUID from summoner ID: {puuid[:10]}...")
                    
                    # Save to config file
                    config_dict = {
                        'discord': asdict(self.config.discord),
                        'riot': asdict(self.config.riot),
                        'database': asdict(self.config.database),
                        'messages': asdict(self.config.messages)
                    }
                    self.config_manager.save_config_dict(config_dict)
                    return True
            else:
                return True
                
        # Neither summoner ID nor name is set
        if not self.config.riot.summoner_name:
            logger.error("Summoner name is not set in configuration")
            return False
                
        try:
            logger.info(f"Fetching summoner data for {self.config.riot.summoner_name}")
            
            # First try getting the summoner directly by name
            summoner_data = await self.api_client.request(
                f"/lol/summoner/v4/summoners/by-name/{self.config.riot.summoner_name}",
                region_override=self.config.riot.region
            )
            
            if 'id' in summoner_data and 'puuid' in summoner_data:
                self.config.riot.summoner_id = summoner_data['id']
                self.config.riot.puuid = summoner_data['puuid']
                logger.info(f"Initialized summoner ID: {summoner_data['id']}")
                logger.info(f"Initialized PUUID: {summoner_data['puuid'][:10]}...")
                
                # Save to config file
                config_dict = {
                    'discord': asdict(self.config.discord),
                    'riot': asdict(self.config.riot),
                    'database': asdict(self.config.database),
                    'messages': asdict(self.config.messages)
                }
                self.config_manager.save_config_dict(config_dict)
                
                return True
            else:
                logger.error(f"Failed to get summoner data: {summoner_data}")
            
            return False
        except Exception as e:
            logger.error(f"Failed to initialize summoner ID and PUUID: {e}")
            return False

    def get_display_name(self) -> str:
        """Get the name to use in messages."""
        if hasattr(self.config, 'messages') and self.config.messages.nickname:
            return self.config.messages.nickname
        return self.config.riot.summoner_name

    async def get_latest_lp(self, queue_type: str, max_retries: int = 3, retry_delay: int = 1) -> Optional[int]:
        """
        Get the most recent LP value for the specific queue with retries.
        
        Args:
            queue_type: Queue type (e.g., 'RANKED_SOLO_5x5')
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Optional[int]: LP value or None
        """
        for attempt in range(max_retries):
            try:
                rank_data = await self.db_manager.get_latest_rank(queue_type)
                
                if rank_data is None:
                    logger.info(f"No data found for queue type: {queue_type}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        continue
                    return None

                tier, rank, lp = rank_data
                logger.info(f"Latest {queue_type} data - Tier: {tier}, Rank: {rank}, LP: {lp}")
                return lp

            except Exception as e:
                logger.error(f"Error in get_latest_lp: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return None

    def format_queue_type(self, queue_type: str, with_parentheses: bool = False) -> str:
        """
        Convert queue type to readable format.
        
        Args:
            queue_type: Queue type code
            with_parentheses: Whether to add parentheses
            
        Returns:
            str: Formatted queue type
        """
        mapping = {
            'RANKED_SOLO_5x5': "Solo Queue",
            'RANKED_FLEX_SR': "Flex",
            'TOURNAMENT': "Tournament",
            '5v5 ARAM games': "ARAM"
        }
        formatted = mapping.get(queue_type, "Unknown Queue")
        return f"({formatted})" if with_parentheses else formatted

    async def check_match_result(
        self, 
        game_id: str,
        queue_type: Optional[str] = None
    ) -> Tuple[str, Optional[int], str]:
        """
        Check the result of a match.
        
        Args:
            game_id: Game ID
            queue_type: Optional queue type
            
        Returns:
            Tuple[str, Optional[int], str]: (result, deaths, queue_type)
        """
        try:
            # Get recent match IDs for the player
            match_ids = await self.api_client.get_match_list(
                puuid=self.config.riot.summoner_id,
                count=1
            )
            
            if not match_ids:
                logger.error("Failed to get match IDs.")
                return "Unable to determine match result.", None, queue_type
            
            # Get match details
            match_id = match_ids[0]
            match_data = await self.api_client.get_match(match_id)
            
            if 'status' in match_data and 'status_code' in match_data['status']:
                logger.error(f"Failed to get match details. Status: {match_data['status']['status_code']}")
                return "Unable to determine match result.", None, queue_type
            
            # Get queue type if not provided
            if not queue_type and 'info' in match_data:
                queue_id = match_data['info'].get('queueId')
                queue_type = get_queue_type(queue_id)
                
            logger.info(f"Processing result with queue type: {queue_type}")
            
            # Find the player in the participants
            for participant in match_data['info']['participants']:
                if participant['puuid'] == self.config.riot.summoner_id:
                    deaths = None if queue_type == 'TOURNAMENT' else participant.get('deaths')
                    logger.info(f"Found player in match data - Deaths: {deaths}")
                    
                    if participant['win']:
                        return "won", deaths, queue_type
                    else:
                        return "lost", deaths, queue_type
            
            logger.error("Player not found in match participants")
            return "Unable to determine match result.", None, queue_type
            
        except Exception as e:
            logger.error(f"Error in check_match_result: {str(e)}")
            return f"Error: {str(e)}", None, queue_type

    async def track_rank_after_game(self, match_id: str) -> None:
        """
        Track rank changes after a game.
        
        Args:
            match_id: Match ID
        """
        try:
            # Get league entries
            league_entries = await self.api_client.get_league_entries(self.config.riot.summoner_id)
            
            if not league_entries or 'status' in league_entries:
                logger.error("Failed to get league entries.")
                return
            
            # Process both solo and flex queue data
            for entry in league_entries:
                try:
                    queue_type = entry.get('queueType')
                    tier = entry.get('tier')
                    rank = entry.get('rank')
                    lp = entry.get('leaguePoints')
                    
                    if all([queue_type, tier, rank, lp is not None]):
                        logger.info(f"Processing {queue_type} data - Tier: {tier}, Rank: {rank}, LP: {lp}")
                        await self.db_manager.store_rank_data(
                            match_id=match_id,
                            queue_type=queue_type,
                            tier=tier,
                            rank=rank,
                            lp=lp
                        )
                except KeyError as e:
                    logger.error(f"Missing required field in league entry: {e}")
                except Exception as e:
                    logger.error(f"Error processing league entry: {e}")
            
        except Exception as e:
            logger.error(f"Error in track_rank_after_game: {e}")

    async def check_spectator(self, channel) -> None:
        """
        Main spectator checking loop.
        
        Args:
            channel: Discord channel to send messages to
        """
        await self.api_client.initialize()
        
        try:
            while True:
                try:
                    async with self.game_check_lock:  # Use lock to prevent race conditions
                        # Validate summoner ID
                        if not self.config.riot.summoner_id or self.config.riot.summoner_id.strip() == '':
                            logger.info("Summoner ID is empty, attempting to fetch it")
                            success = await self.initialize_summoner_id()
                            if not success:
                                logger.error("Failed to initialize summoner ID. Waiting before retrying...")
                                await asyncio.sleep(60)
                                continue
                        
                        # Check for active game
                        logger.debug(f"Checking for active game with summoner ID: {self.config.riot.puuid}")
                        game_data = await self.api_client.get_current_game(
                                                                            summoner_id=self.config.riot.summoner_id,
                                                                            puuid=self.config.riot.puuid
                                                                        )
                        
                        if 'status' in game_data:
                            status_code = game_data['status'].get('status_code')
                            if status_code == 401:
                                logger.error("Authentication error (401) - Check if API key is valid")
                                # Wait longer before retrying on auth errors
                                await asyncio.sleep(60)
                                continue
                            elif status_code == 404:
                                # 404 means not in game - normal case
                                if self.game_in_progress:
                                    # Game has ended
                                    logger.info(f"Game ended - Processing results...")
                                    logger.info(f"Game ended with queue type: {self.current_queue_type}, pre-game queue type: {self.pre_game_queue_type}")
                                    
                                    # Mark game as not in progress
                                    self.game_in_progress = False
                                    
                                    # Wait for match data to be available
                                    await asyncio.sleep(30)
                                    
                                    try:
                                        # Check match result
                                        result, deaths, queue_type = await self.check_match_result(
                                            self.current_game_id, 
                                            self.current_queue_type
                                        )
                                        
                                        # Send result message
                                        display_name = self.get_display_name()
                                        emoji = self.emoji_map['win'] if result == "won" else self.emoji_map['loss']
                                        
                                        if result == "won":
                                            msg = self.config.messages.game_win.format(summoner_name=display_name)
                                        else:
                                            msg = self.config.messages.game_loss.format(summoner_name=display_name)
                                        
                                        await channel.send(f"{emoji} {msg}")
                                        
                                        # Send death count message for non-tournament games
                                        if queue_type == 'TOURNAMENT':
                                            await channel.send(f"{self.emoji_map['deaths']} Unable to display tournament death count... {self.emoji_map['copium']}")
                                        elif deaths is not None:
                                            death_msg = self.config.messages.death_count.format(
                                                summoner_name=display_name,
                                                deaths=deaths
                                            )
                                            if queue_type not in ['RANKED_SOLO_5x5', 'RANKED_FLEX_SR']:
                                                death_msg += f" in {self.format_queue_type(queue_type)}"
                                            await channel.send(f"{self.emoji_map['deaths']} {death_msg} {self.emoji_map['copium']}")
                                        
                                        # Process LP change for ranked games
                                        if self.pre_game_queue_type and self.pre_game_queue_type == queue_type and self.pre_game_lp is not None:
                                            logger.info(f"Processing LP change for {queue_type} - Pre-game LP: {self.pre_game_lp}")
                                            
                                            # Track rank changes
                                            await self.track_rank_after_game(self.current_game_id)
                                            await asyncio.sleep(5)  # Give time for DB update
                                            
                                            # Get post-game LP
                                            post_game_lp = await self.get_latest_lp(self.pre_game_queue_type)
                                            
                                            if post_game_lp is not None:
                                                lp_change = post_game_lp - self.pre_game_lp
                                                logger.info(f"LP change calculated: {lp_change} ({self.pre_game_lp} -> {post_game_lp})")
                                                
                                                if lp_change > 0:
                                                    msg = self.config.messages.lp_gain.format(
                                                        summoner_name=display_name,
                                                        lp_change=lp_change,
                                                        queue_type=self.format_queue_type(queue_type)
                                                    )
                                                    await channel.send(f"{self.emoji_map['lp_gain']} {msg}")
                                                else:
                                                    msg = self.config.messages.lp_loss.format(
                                                        summoner_name=display_name,
                                                        lp_change=abs(lp_change),
                                                        queue_type=self.format_queue_type(queue_type)
                                                    )
                                                    await channel.send(f"{self.emoji_map['lp_loss']} {msg}")
                                            else:
                                                logger.error(f"Could not get post-game LP for {queue_type}")
                                        else:
                                            logger.info(f"Skipping LP tracking - Queue type: {queue_type}, Pre-game LP: {self.pre_game_lp}")
                                        
                                    except Exception as e:
                                        logger.error(f"Error processing game results: {str(e)}")
                                    finally:
                                        # Reset state variables
                                        self.pre_game_lp = None
                                        self.current_queue_type = None
                                        self.pre_game_queue_type = None
                                        self.current_game_id = None
                            else:
                                logger.warning(f"Unexpected status code: {status_code}")
                                await asyncio.sleep(30)
                                continue
                        else:
                            # Game is in progress (no status means success)
                            if not self.game_in_progress:
                                logger.info("New game detected")
                                
                                # Get queue type
                                queue_id = game_data.get('gameQueueConfigId')
                                self.current_queue_type = get_queue_type(queue_id)
                                
                                # Store pre-game LP for ranked games
                                if self.current_queue_type in ['RANKED_SOLO_5x5', 'RANKED_FLEX_SR']:
                                    self.pre_game_lp = await self.get_latest_lp(self.current_queue_type)
                                    self.pre_game_queue_type = self.current_queue_type
                                    logger.info(f"Pre-game LP: {self.pre_game_lp}")
                                
                                # Mark game as in progress
                                self.game_in_progress = True
                                self.current_game_id = game_data['gameId']
                                
                                # Send game start message
                                display_name = self.get_display_name()
                                game_start_msg = self.config.messages.game_start.format(summoner_name=display_name)
                                await channel.send(f"{self.emoji_map['monitoring']} {game_start_msg}")
                
                except asyncio.CancelledError:
                    logger.info("Spectator checker task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in spectator check: {str(e)}")
                
                # Wait before next check
                await asyncio.sleep(self.config.database.check_interval)
                
        except asyncio.CancelledError:
            logger.info("Spectator checker exiting")
        finally:
            # Clean up resources
            await self.api_client.close()

async def initialize_spectator(channel, config_manager=None) -> asyncio.Task:
    """
    Initialize and run the spectator checker.
    
    Args:
        channel: Discord channel to send messages to
        config_manager: Optional configuration manager to reuse
        
    Returns:
        asyncio.Task: The running spectator checker task
    """
    if config_manager is None:
        config_path = "config/config.json"
        config_manager = ConfigManager(config_path)
    
    # Check if config file exists and has required fields
    config = config_manager.config
    if not all([
        config.riot.api_key,
        config.riot.summoner_name,
        config.riot.summoner_tag
    ]):
        logger.error("Required Riot API configuration is missing. Please configure the bot using the GUI.")
        
        # Launch GUI for configuration
        from pathlib import Path
        from gui import launch_gui
        
        config_file = Path("config/config.json")
        if not config_file.exists():
            config_file.parent.mkdir(parents=True, exist_ok=True)
        
        import threading
        gui_thread = threading.Thread(target=launch_gui, args=(config_manager,))
        gui_thread.daemon = True
        gui_thread.start()
        
        # Return an empty task that does nothing
        logger.info("Please complete the configuration using the GUI and restart the bot.")
        return asyncio.create_task(asyncio.sleep(0))
    
    checker = SpectatorChecker(config_manager)
    return asyncio.create_task(checker.check_spectator(channel))