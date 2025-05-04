import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

@dataclass
class DiscordConfig:
    bot_token: str
    channel_id: str
    rate_limit: int = 10
    time_window: int = 120

@dataclass
class RiotConfig:
    api_key: str
    summoner_id: str
    summoner_name: str
    summoner_tag: str
    region: str = "NA1"
    platform: str = "americas"
    puuid: str = ""

@dataclass
class DatabaseConfig:
    path: str = "/app/rank_tracker.db"
    check_interval: int = 10

@dataclass
class MessageConfig:
    game_start: str = "{summoner_name} is in a game now! Monitoring..."
    game_win: str = "{summoner_name} got carried!"
    game_loss: str = "{summoner_name} threw the game!"
    death_count: str = "Amount of times {summoner_name} died: {deaths}"
    lp_gain: str = "{summoner_name} gained {lp_change} LP in {queue_type}!"
    lp_loss: str = "{summoner_name} lost {lp_change} LP in {queue_type}!"
    nickname: str = ""  # If empty, will use summoner_name from config

@dataclass
class Config:
    discord: DiscordConfig
    riot: RiotConfig
    database: DatabaseConfig
    messages: MessageConfig

    def __init__(self, discord: DiscordConfig, riot: RiotConfig, database: DatabaseConfig, messages: Optional[MessageConfig] = None):
        self.discord = discord
        self.riot = riot
        self.database = database
        self.messages = messages or MessageConfig()

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self._config: Optional[Config] = None

    def load_config(self) -> Config:
        """Load configuration from file"""
        try:
            if not os.path.exists(self.config_path):
                self.logger.warning(f"Config file not found at {self.config_path}")
                return self._create_default_config()

            with open(self.config_path, 'r') as f:
                data = json.load(f)

            discord_config = DiscordConfig(**data['discord'])
            riot_config = RiotConfig(**data['riot'])
            database_config = DatabaseConfig(**data['database'])

            self._config = Config(
                discord=discord_config,
                riot=riot_config,
                database=database_config
            )
            return self._config

        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            return self._create_default_config()

    def save_config_dict(self, config_dict: Dict[str, Any]) -> bool:
        """Save configuration from dictionary"""
        try:
            # Create directory if it doesn't exist
            config_dir = Path(self.config_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)

            # Save to file
            with open(self.config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)

            # Reload configuration
            self._config = self.load_config()
            return True

        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
            return False

    def _create_default_config(self) -> Config:
        """Create a default configuration"""
        return Config(
            discord=DiscordConfig(
                bot_token="",
                channel_id="",
                rate_limit=10,
                time_window=120
            ),
            riot=RiotConfig(
                api_key="",
                summoner_id="",
                summoner_name="",
                summoner_tag="",
                region="NA1",
                platform="americas",
                puuid=""  # Add empty PUUID
            ),
            database=DatabaseConfig(
                path="/app/rank_tracker.db",
                check_interval=10
            ),
            messages=MessageConfig() 
        )

    def validate_config(self, config: Config) -> tuple[bool, str]:
        """Validate configuration values"""
        if not config.discord.bot_token:
            return False, "Discord bot token is required"
        if not config.discord.channel_id:
            return False, "Discord channel ID is required"
        if not config.riot.api_key:
            return False, "Riot API key is required"
        if not config.riot.summoner_id:
            return False, "Summoner ID is required"
        
        # Validate database path
        try:
            db_path = Path(config.database.path)
            db_dir = db_path.parent
            if not db_dir.exists():
                return False, f"Database directory {db_dir} does not exist"
        except Exception as e:
            return False, f"Invalid database path: {str(e)}"

        return True, "Configuration is valid"
    
    async def initialize_summoner_id(self) -> bool:
        """Initialize summoner ID if not already set"""
        if self.config.riot.summoner_id and self.config.riot.summoner_id.strip():
            return True
            
        # Check if summoner name and tag are set
        if not self.config.riot.summoner_name or not self.config.riot.summoner_tag:
            logger.error("Summoner name or tag is not set in configuration")
            return False
                
        try:
            logger.info(f"Fetching summoner ID for {self.config.riot.summoner_name}#{self.config.riot.summoner_tag}")
            
            # First attempt to get the account info by Riot ID
            account_data = await self.api_client.request(
                f"/riot/account/v1/accounts/by-riot-id/{self.config.riot.summoner_name}/{self.config.riot.summoner_tag}",
                use_platform=True
            )

            if 'puuid' in account_data:
                # Get summoner data by PUUID
                summoner_data = await self.api_client.request(
                    f"/lol/summoner/v4/summoners/by-puuid/{account_data['puuid']}"
                )
                
                if 'id' in summoner_data:
                    self.config.riot.summoner_id = summoner_data['id']
                    
                    # Save to config file
                    config_dict = {
                        'discord': asdict(self.config.discord),
                        'riot': asdict(self.config.riot),
                        'database': asdict(self.config.database),
                        'messages': asdict(self.config.messages)
                    }
                    self.save_config_dict(config_dict)
                    
                    return True
            
            return False
        except Exception as e:
            logging.error(f"Failed to initialize summoner ID: {e}")
            return False
        
    # Add to config_manager.py
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            'discord': asdict(self.config.discord),
            'riot': asdict(self.config.riot),
            'database': asdict(self.config.database),
            'messages': asdict(self.config.messages)
        }

    @property
    def config(self) -> Config:
        """Get current configuration"""
        if self._config is None:
            self._config = self.load_config()
        return self._config