import discord
from discord import app_commands
import asyncio
import logging
import sys
import argparse
from pathlib import Path
from config_manager import ConfigManager
from spectator_checker import SpectatorChecker
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
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.config
        
        # Initialize Discord client
        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents, reconnect=True)
        self.tree = app_commands.CommandTree(self.client)
        
        # Initialize command handler
        self.command_handler = CommandHandler(self.config_manager)
        
        # Register commands
        self.register_commands()

    def register_commands(self):
        """Register slash commands"""
        self.tree.add_command(self.command_handler.stalkmatches_command)
        self.tree.add_command(self.command_handler.livegame_command)
        self.tree.add_command(self.command_handler.stalkrank_command)

    async def setup(self):
        """Set up the bot and start background tasks"""
        @self.client.event
        async def on_ready():
            logger.info(f'\033[32mLogged in as {self.client.user}\033[0m')
            if not hasattr(self.client, 'synced'):
                await self.tree.sync()
                self.client.synced = True
                logger.info("\033[32mCommands synced.\033[0m")

            # Get the channel to send updates to
            channel = self.client.get_channel(int(self.config.discord.channel_id))
            if not channel:
                logger.error(f"Could not find channel with ID {self.config.discord.channel_id}")
                return

            # Initialize and start spectator checker
            self.spectator_checker = SpectatorChecker(self.config_manager)
            self.client.loop.create_task(self.spectator_checker.check_spectator(channel))

        @self.client.event
        async def on_disconnect():
            logger.info("\033[91mBot disconnected, attempting to reconnect...\033[0m")

    async def run(self):
        """Run the bot"""
        await self.setup()
        while True:
            try:
                await self.client.start(self.config.discord.bot_token)
            except discord.errors.LoginFailure:
                logger.error("Invalid Discord token")
                return
            except discord.errors.ConnectionClosed:
                logger.info("\033[91mConnection lost, trying to reconnect in 5 seconds...\033[0m")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                await asyncio.sleep(5)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SourceStalker Discord Bot')
    parser.add_argument('--gui', action='store_true', help='Launch configuration GUI only')
    args = parser.parse_args()

    # Initialize configuration
    config_manager = ConfigManager()

    # If --gui flag is used, only launch the GUI
    if args.gui:
        launch_gui(config_manager)
        return

    # Show GUI for initial configuration if needed
    if not Path('config/config.json').exists():
        launch_gui(config_manager)
    
    # Start the bot
    bot = SourceStalkerBot(config_manager)
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("\033[93mKeyboardInterrupt detected: Bot shutting down gracefully.\033[0m")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    main()