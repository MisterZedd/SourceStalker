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
from dataclasses import asdict
import time


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
        
        # Initialize client without application_id - we'll get it after login
        self.client = discord.Client(
            intents=intents, 
            reconnect=True
        )
        self.tree = app_commands.CommandTree(self.client)
        
        # Initialize command handler
        self.command_handler = CommandHandler(self.config_manager)
        
        # Background tasks
        self.bg_tasks = []
        self.spectator_task = None
        self.connected = asyncio.Event()
        
        # Add a sync lock to prevent multiple syncs
        self._sync_lock = asyncio.Lock()
        self._last_sync_time = 0
        self._initial_sync_done = False
        self._commands_registered = False
        
        # Development mode from config
        self.dev_mode = getattr(self.config.discord, 'development_mode', False)
        
        # Development guild for testing (if in dev mode)
        self.dev_guild = None
        if self.dev_mode and hasattr(self.config.discord, 'dev_guild_id') and self.config.discord.dev_guild_id:
            self.dev_guild = discord.Object(id=int(self.config.discord.dev_guild_id))

    def register_commands(self):
        """Register slash commands with proper formatting."""
        if self._commands_registered:
            logger.info("Commands already registered, skipping registration")
            return
            
        # Add a sync command (owner only)
        @self.tree.command(name="sync", description="Sync commands (owner only)")
        async def sync_cmd(interaction: discord.Interaction, global_sync: bool = False):
            """
            Sync slash commands
            
            Parameters:
                global_sync: Whether to sync commands globally (default: False)
            """
            # Only allow owners to use this command
            if not await self._is_owner(interaction):
                await interaction.response.send_message("You must be the owner to use this command!", ephemeral=True)
                return
                
            await interaction.response.defer(ephemeral=True)
            await self._sync_commands(interaction=interaction, global_sync=global_sync)
        
        # Register commands from the command handler using the tree decorator pattern
        @self.tree.command(name="stalkmatches", description="Check recent match history")
        async def stalkmatches_cmd(interaction: discord.Interaction):
            await self.command_handler.stalkmatches(interaction)
        
        @self.tree.command(name="livegame", description="Get live game information")
        async def livegame_cmd(interaction: discord.Interaction):
            await self.command_handler.livegame(interaction)
            
        @self.tree.command(name="stalkrank", description="Check current rank and rank history")
        async def stalkrank_cmd(interaction: discord.Interaction):
            await self.command_handler.stalkrank(interaction)
            
        self._commands_registered = True
        logger.info(f"Registered 4 commands successfully!")  # sync + 3 game commands

    async def _is_owner(self, interaction: discord.Interaction) -> bool:
        """Check if the user is the bot owner."""
        # Use application owner as the definitive check
        app_info = await self.client.application_info()
        owner_id = app_info.owner.id
        
        # Store in config for future reference
        if not hasattr(self.config.discord, 'owner_id') or str(self.config.discord.owner_id) != str(owner_id):
            # Update config
            self.config.discord.owner_id = str(owner_id)
            config_dict = self.config_manager.get_config_dict()
            self.config_manager.save_config_dict(config_dict)
            
        return interaction.user.id == owner_id
    
    async def _sync_commands(self, interaction=None, global_sync=False, force_guild=None):
        """
        Improved sync command implementation
        
        Parameters:
            interaction: Discord interaction for response (optional)
            global_sync: Whether to sync globally
            force_guild: Force sync to a specific guild (for initial setup)
        """
        async with self._sync_lock:
            # Check if we've synced recently (avoid rate limits)
            current_time = time.time()
            if current_time - self._last_sync_time < 60 and not force_guild:
                if interaction:
                    await interaction.followup.send("Command sync requested too soon. Please wait before trying again.")
                logger.warning("Command sync requested too soon after previous sync")
                return 0
            
            # Determine target for sync
            if force_guild:
                guild = force_guild
            elif global_sync:
                guild = None
            else:
                guild = self.dev_guild
            
            try:
                # Log what we're doing
                if guild:
                    logger.info(f"Syncing commands to guild: {guild.id}")
                else:
                    logger.info("Syncing commands globally")
                
                # Ensure commands are registered before syncing
                if not self._commands_registered:
                    self.register_commands()
                
                # Copy global commands to guild if needed (for guild-specific sync)
                if guild and not global_sync:
                    self.tree.copy_global_to(guild=guild)
                
                # Sync commands with the Discord API
                synced = await self.tree.sync(guild=guild)
                
                # Update last sync time
                self._last_sync_time = current_time
                
                # Log results
                if guild:
                    logger.info(f"Synced {len(synced)} commands to guild {guild.id}")
                else:
                    logger.info(f"Synced {len(synced)} commands globally")
                
                # Send response if interaction is provided
                if interaction:
                    target = f"guild {guild.id}" if guild else "all servers (globally)"
                    await interaction.followup.send(f"Successfully synced {len(synced)} commands to {target}!")
                
                return len(synced)
                
            except discord.HTTPException as e:
                error_msg = f"Error syncing commands: {e}"
                logger.error(error_msg)
                
                # If it's a 403 error, it might be a permissions issue
                if e.status == 403:
                    error_msg += "\n\nMake sure the bot has the 'applications.commands' scope in the OAuth2 URL."
                
                if interaction:
                    await interaction.followup.send(f"Failed to sync commands: {error_msg}")
                
                return 0
            except Exception as e:
                logger.error(f"Unexpected error syncing commands: {str(e)}", exc_info=True)
                
                if interaction:
                    await interaction.followup.send(f"An unexpected error occurred: {str(e)}")
                
                return 0

    async def setup(self):
        """Set up the bot and start background tasks."""
        @self.client.event
        async def on_ready():
            logger.info(f'\033[32mLogged in as {self.client.user}\033[0m')
            
            # Display bot invite link with proper permissions on first ready
            if not self._initial_sync_done:
                try:
                    app_info = await self.client.application_info()
                    permissions = discord.Permissions(
                        send_messages=True,
                        embed_links=True,
                        attach_files=True,
                        read_message_history=True,
                        use_application_commands=True
                    )
                    invite_link = discord.utils.oauth_url(
                        app_info.id,
                        permissions=permissions,
                        scopes=['bot', 'applications.commands']
                    )
                    logger.info(f"\033[36mBot invite link: {invite_link}\033[0m")
                    logger.info("\033[33mMake sure the bot was added with the 'applications.commands' scope!\033[0m")
                except Exception as e:
                    logger.error(f"Could not generate invite link: {e}")
            
            # Set the connected event
            self.connected.set()
            
            # Get and save application ID automatically on first ready
            if not self._initial_sync_done:
                logger.info("First ready event - initializing bot")
                try:
                    # Get application info to retrieve ID
                    app_info = await self.client.application_info()
                    app_id = str(app_info.id)
                    
                    # Save application ID to config if different
                    if not hasattr(self.config.discord, 'application_id') or self.config.discord.application_id != app_id:
                        logger.info(f"Saving application ID: {app_id}")
                        self.config.discord.application_id = app_id
                        config_dict = self.config_manager.get_config_dict()
                        self.config_manager.save_config_dict(config_dict)
                    
                    # Register commands
                    logger.info("Registering commands")
                    self.register_commands()
                    self._initial_sync_done = True
                    
                    # Small delay to ensure connection is stable
                    await asyncio.sleep(2)
                    
                    # Sync commands based on mode
                    if self.dev_mode and self.dev_guild:
                        logger.info(f"Development mode - syncing commands to dev guild {self.dev_guild.id}")
                        await self._sync_commands(global_sync=False)
                    else:
                        # In production, sync to the channel's guild
                        channel_guild_id = None
                        try:
                            channel = self.client.get_channel(int(self.config.discord.channel_id))
                            if channel and hasattr(channel, 'guild'):
                                channel_guild_id = channel.guild.id
                                logger.info(f"Production mode - syncing commands to guild {channel_guild_id}")
                                guild_obj = discord.Object(id=channel_guild_id)
                                await self._sync_commands(force_guild=guild_obj)
                            else:
                                logger.warning("Could not determine guild from channel, syncing globally")
                                await self._sync_commands(global_sync=True)
                        except Exception as e:
                            logger.error(f"Error determining guild for sync: {e}")
                            logger.info("Falling back to global sync")
                            await self._sync_commands(global_sync=True)
                            
                except Exception as e:
                    logger.error(f"Error during initialization: {e}", exc_info=True)

            # Get the channel to send updates to
            channel = self.client.get_channel(int(self.config.discord.channel_id))
            if not channel:
                logger.error(f"Could not find channel with ID {self.config.discord.channel_id}")
                return
            
            # Start spectator checker if not already running
            if not self.spectator_task or self.spectator_task.done():
                self.spectator_task = await initialize_spectator(channel, self.config_manager)
                self.bg_tasks.append(self.spectator_task)
                logger.info("\033[32mSpectator checker started.\033[0m")

        @self.client.event
        async def on_disconnect():
            logger.info("\033[91mBot disconnected, attempting to reconnect...\033[0m")
            self.connected.clear()
        
        @self.client.event
        async def on_error(event, *args, **kwargs):
            logger.error(f"Discord error in {event}: {sys.exc_info()[1]}")
            
        @self.client.event
        async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            logger.error(f"Command error in {interaction.command.name if interaction.command else 'unknown'}: {type(error).__name__}: {error}")
            
            if isinstance(error, app_commands.errors.CommandSignatureMismatch):
                logger.error(f"Command signature mismatch detected for command: {interaction.command.name}")
                await interaction.response.send_message(
                    "This command is out of sync with Discord. Please ask the bot owner to run `/sync` or wait for automatic re-sync.",
                    ephemeral=True
                )
            elif isinstance(error, app_commands.errors.CommandNotFound):
                await interaction.response.send_message(
                    "This command is not available. The bot may need to sync its commands. Please try again in a few moments.",
                    ephemeral=True
                )
            elif isinstance(error, app_commands.errors.CommandOnCooldown):
                await interaction.response.send_message(
                    f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                    ephemeral=True
                )
            elif isinstance(error, app_commands.errors.MissingPermissions):
                await interaction.response.send_message(
                    "You don't have permission to use this command.",
                    ephemeral=True
                )
            else:
                # Log the full error for debugging
                logger.error(f"Unhandled app command error: {error}", exc_info=error)
                
                # Send generic error message
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"An error occurred while executing this command. Please try again later.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"An error occurred while executing this command. Please try again later.",
                        ephemeral=True
                    )

    async def run(self):
        """Run the bot with improved error handling and reconnection logic."""
        await self.setup()
        
        # Initialize the API client for config setup
        from riot_api_client import RiotAPIClient
        api_client = RiotAPIClient(
            api_key=self.config.riot.api_key,
            region=self.config.riot.region,
            platform=self.config.riot.platform
        )
        await api_client.initialize()
        
        # Initialize summoner ID if needed
        if not self.config.riot.summoner_id and self.config.riot.summoner_name:
            logger.info("Summoner ID not found in config, attempting to fetch...")
            try:
                # Get summoner info by name
                summoner_data = await api_client.request(
                    f"/lol/summoner/v4/summoners/by-name/{self.config.riot.summoner_name}",
                    region_override=self.config.riot.region
                )
                
                if 'id' in summoner_data and 'puuid' in summoner_data:
                    self.config.riot.summoner_id = summoner_data['id']
                    self.config.riot.puuid = summoner_data['puuid']
                    
                    # Save to config
                    config_dict = {
                        'discord': asdict(self.config.discord),
                        'riot': asdict(self.config.riot),
                        'database': asdict(self.config.database),
                        'messages': asdict(self.config.messages)
                    }
                    self.config_manager.save_config_dict(config_dict)
                    
                    logger.info(f"Initialized summoner ID: {summoner_data['id']}")
                    logger.info(f"Initialized PUUID: {summoner_data['puuid']}")
                else:
                    logger.error(f"Failed to get summoner data: {summoner_data}")
            except Exception as e:
                logger.error(f"Error initializing summoner information: {e}")
        
        await api_client.close()
        
        try:
            await self.client.start(self.config.discord.bot_token)
        except discord.errors.LoginFailure:
            logger.error("\033[91mInvalid Discord token\033[0m")
        except Exception as e:
            logger.error(f"\033[91mUnexpected error: {str(e)}\033[0m")
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
    parser.add_argument('--sync', action='store_true', help='Force sync commands on startup')
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