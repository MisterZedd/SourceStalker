"""
main.py
Main entry point for the SourceStalker Discord Bot with improved implementation.
"""
import discord
from discord import app_commands
import asyncio
import logging
import sys
import argparse
from pathlib import Path
from riot_api_client import RiotAPIClient

from config_manager import ConfigManager
from spectator_checker import SpectatorChecker, initialize_spectator
from commands import CommandHandler
from gui import launch_gui

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class SourceStalkerBot:
    """
    Main bot class for the SourceStalker Discord Bot.
    Improved with better error handling and resource management.
    """
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the bot.
        
        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager
        self.config = config_manager.config
        
        # Initialize Discord client with appropriate intents
        intents = discord.Intents.default()
        intents.message_content = True  # Needed to read message content
        
        self.client = discord.Client(intents=intents, reconnect=True)
        self.tree = app_commands.CommandTree(self.client)
        
        # Initialize command handler
        self.command_handler = CommandHandler(self.config_manager)
        
        # Register commands
        self.register_commands()
        
        # Background tasks
        self.bg_tasks = []
        self.spectator_task = None
        self.connected = asyncio.Event()

    def register_commands(self):
        """Register slash commands."""
        self.tree.add_command(self.command_handler.stalkmatches_command)
        self.tree.add_command(self.command_handler.livegame_command)
        self.tree.add_command(self.command_handler.stalkrank_command)

    async def setup(self):
        """Set up the bot and start background tasks."""
        @self.client.event
        async def on_ready():
            logger.info(f'\033[32mLogged in as {self.client.user}\033[0m')
            
            # Sync commands only if needed
            if not hasattr(self.client, 'synced') or not self.client.synced:
                await self.tree.sync()
                self.client.synced = True
                logger.info("\033[32mCommands synced.\033[0m")
            
            # Set the connected event
            self.connected.set()

            # Get the channel to send updates to
            channel = self.client.get_channel(int(self.config.discord.channel_id))
            if not channel:
                logger.error(f"Could not find channel with ID {self.config.discord.channel_id}")
                return

            # Start spectator checker if not already running
            if not self.spectator_task or self.spectator_task.done():
                self.spectator_task = await initialize_spectator(channel)
                self.bg_tasks.append(self.spectator_task)
                logger.info("\033[32mSpectator checker started.\033[0m")

        @self.client.event
        async def on_disconnect():
            logger.info("\033[91mBot disconnected, attempting to reconnect...\033[0m")
            self.connected.clear()
        
        @self.client.event
        async def on_error(event, *args, **kwargs):
            logger.error(f"Discord error in {event}: {sys.exc_info()[1]}")

    async def run(self):
        """Run the bot with improved error handling and reconnection logic."""
        await self.setup()

        # Initialize the API client for config setup
        api_client = RiotAPIClient(
            api_key=self.config.riot.api_key,
            region=self.config.riot.region,
            platform=self.config.riot.platform
        )
        await api_client.initialize()
        
        # Initialize summoner ID if needed
        if not self.config.riot.summoner_id:
            logger.info("Summoner ID not found in config, attempting to fetch...")
            success = await self.config_manager.initialize_summoner_id(api_client)
            if success:
                logger.info(f"Successfully initialized summoner ID: {self.config.riot.summoner_id}")
                # Update the local config reference
                self.config = self.config_manager.config
            else:
                logger.error("Failed to initialize summoner ID. Please check summoner name and tag.")
        
        await api_client.close()
        
        try:
            while True:
                try:
                    logger.info("Connecting to Discord...")
                    await self.client.start(self.config.discord.bot_token)
                except discord.errors.LoginFailure:
                    logger.error("\033[91mInvalid Discord token\033[0m")
                    return
                except discord.errors.ConnectionClosed as e:
                    logger.info(f"\033[91mConnection closed: {e}, reconnecting in 5 seconds...\033[0m")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"\033[91mUnexpected error: {str(e)}\033[0m")
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("Bot shutdown initiated")
        finally:
            # Clean up resources
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources and background tasks."""
        # Cancel background tasks
        for task in self.bg_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close Discord client gracefully
        if self.client and self.client.is_ready():
            await self.client.close()
        
        logger.info("Bot resources cleaned up")

def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SourceStalker Discord Bot')
    parser.add_argument('--gui', action='store_true', help='Launch configuration GUI only')
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to config file')
    args = parser.parse_args()

    # Initialize configuration
    config_path = Path(args.config)
    config_manager = ConfigManager(str(config_path))

    # If --gui flag is used, only launch the GUI
    if args.gui:
        launch_gui(config_manager)
        return

    # Show GUI for initial configuration if needed
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        launch_gui(config_manager)
    
    # Start the bot
    bot = SourceStalkerBot(config_manager)
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("\033[93mKeyboardInterrupt detected: Bot shutting down gracefully.\033[0m")

if __name__ == "__main__":
    main()