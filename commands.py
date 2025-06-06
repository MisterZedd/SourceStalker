"""
commands.py
Improved implementation of the CommandHandler class with better error handling and concurrency.
"""
import discord
from discord import app_commands
import datetime
import asyncio
import time
from collections import deque
import io
import logging
import sys
from typing import Optional, List, Dict, Tuple, Union
from datetime import datetime, timedelta

from config_manager import ConfigManager
from riot_api_client import RiotAPIClient
from db_manager import DBManager
from utils.getChampionNameByID import get_champion_name
from utils.gamemodes import get_queue_type
from utils.summonerSpells import get_summoner_spell_name
from utils.rankEmojis import get_rank_emoji
from utils.rankGraph import generate_rank_graph

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for Discord commands."""
    def __init__(self, rate_limit: int, time_window: int):
        """
        Initialize the rate limiter.
        
        Args:
            rate_limit: Maximum number of requests in the time window
            time_window: Time window in seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.requests = deque(maxlen=rate_limit)
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Try to acquire permission to execute a command.
        
        Returns:
            bool: True if allowed, False if rate limited
        """
        async with self.lock:
            current_time = time.time()
            
            # Remove expired timestamps
            while self.requests and current_time - self.requests[0] > self.time_window:
                self.requests.popleft()
            
            # Check if limit is reached
            if len(self.requests) >= self.rate_limit:
                return False
            
            # Add current request
            self.requests.append(current_time)
            return True
    
    async def get_remaining_time(self) -> int:
        """
        Get time until the rate limit resets.
        
        Returns:
            int: Time in seconds until a request slot becomes available
        """
        async with self.lock:
            if not self.requests or len(self.requests) < self.rate_limit:
                return 0
            
            current_time = time.time()
            oldest_request = self.requests[0]
            return max(0, int(self.time_window - (current_time - oldest_request)))

class CommandHandler:
    """Discord command handler with improved error handling and rate limiting."""
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the command handler.
        
        Args:
            config_manager: Configuration manager
        """
        self.config = config_manager.config
        
        # Initialize API client
        self.api_client = RiotAPIClient(
            api_key=self.config.riot.api_key,
            region=self.config.riot.region,
            platform=self.config.riot.platform
        )
        
        # Initialize database manager
        self.db_manager = DBManager(self.config.database.path)
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            rate_limit=self.config.discord.rate_limit,
            time_window=self.config.discord.time_window
        )

    def get_day_with_suffix(self, day: int) -> str:
        """
        Return day with appropriate suffix (1st, 2nd, 3rd, etc.)
        
        Args:
            day: Day of the month
            
        Returns:
            str: Day with suffix
        """
        if 11 <= day <= 13:
            return f"{day}th"
        suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
        return f"{day}{suffixes.get(day % 10, 'th')}"

    async def get_relative_time(self, timestamp: int) -> str:
        """
        Calculate relative time from timestamp to now.
        
        Args:
            timestamp: Unix timestamp in milliseconds
            
        Returns:
            str: Human-readable relative time
        """
        game_time = datetime.fromtimestamp(timestamp / 1000)
        now = datetime.now()
        diff = now - game_time

        if diff.days > 0:
            return f"{diff.days} day(s) ago"
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours} hour(s) ago"
        minutes = (diff.seconds % 3600) // 60
        return f"{minutes} minute(s) ago"

    async def get_summoner_info(self, force_refresh: bool = False) -> Optional[Dict]:
        """
        Get summoner information, preferably from cache or config.
        
        Args:
            force_refresh: Force a refresh from API
            
        Returns:
            Optional[Dict]: Summoner information or None
        """
        # If we have the data in config, use that
        if self.config.riot.summoner_id and self.config.riot.puuid and not force_refresh:
            return {
                'id': self.config.riot.summoner_id,
                'puuid': self.config.riot.puuid,
                'name': self.config.riot.summoner_name,
                'summonerName': self.config.riot.summoner_name
            }
        
        # Try to get from cache
        if not force_refresh:
            cached_data = await self.db_manager.get_summoner_by_name(self.config.riot.summoner_name)
            if cached_data:
                return cached_data
        
        # Get from API using PUUID if available
        if self.config.riot.puuid:
            endpoint = f"/lol/summoner/v4/summoners/by-puuid/{self.config.riot.puuid}"
            summoner_data = await self.api_client.request(endpoint, region_override=self.config.riot.region)
        else:
            # Fallback to by-name (deprecated but might work for some regions)
            summoner_data = await self.api_client.get_summoner_by_name(self.config.riot.summoner_name)
        
        if 'status' in summoner_data and 'status_code' in summoner_data['status']:
            logger.error(f"Failed to get summoner info: {summoner_data['status']['message']}")
            return None
        
        # Cache the data for future use
        await self.db_manager.store_summoner_data(
            puuid=summoner_data['puuid'],
            summoner_id=summoner_data['id'],
            account_id=summoner_data['accountId'],
            name=summoner_data.get('name', self.config.riot.summoner_name),
            data=summoner_data
        )
        
        return summoner_data
    async def stalkmatches(self, interaction: discord.Interaction) -> None:
        """
        Handle the stalkmatches command.
        
        Args:
            interaction: Discord interaction
        """
        # Check rate limiting
        allowed = await self.rate_limiter.acquire()
        if not allowed:
            remaining_time = await self.rate_limiter.get_remaining_time()
            await interaction.response.send_message(
                f"Rate limit reached. Try again in {remaining_time} seconds.",
                ephemeral=True
            )
            return

        try:
            # Defer response due to potentially long API calls
            await interaction.response.defer()
            
            # Get summoner info
            summoner = await self.get_summoner_info()
            if not summoner:
                await interaction.followup.send(
                    f"Could not find summoner information for {self.config.riot.summoner_name}",
                    ephemeral=True
                )
                return
            
            # Get match history
            match_ids = await self.api_client.get_match_list(
                puuid=summoner['puuid'],
                count=3
            )
            
            logger.info(f"Match IDs response: {match_ids}")
            
            if not match_ids or (isinstance(match_ids, dict) and 'status' in match_ids):
                await interaction.followup.send(
                    f"No recent matches found for {self.config.riot.summoner_name}",
                    ephemeral=True
                )
                return
            
            # Fetch match details concurrently
            match_details = []
            tasks = []
            for match_id in match_ids:
                tasks.append(self.api_client.get_match(match_id))
            
            match_results = await asyncio.gather(*tasks)
            for i, result in enumerate(match_results):
                logger.info(f"Match {i} result: {type(result)} - has status: {'status' in result if isinstance(result, dict) else 'not dict'}")
                if isinstance(result, dict) and 'status' not in result:
                    match_details.append(result)
                elif isinstance(result, dict) and 'status' in result:
                    logger.warning(f"Match {i} has error status: {result['status']}")
                else:
                    logger.warning(f"Match {i} unexpected result type: {type(result)}")
            
            if not match_details:
                await interaction.followup.send(
                    "Failed to fetch match details.",
                    ephemeral=True
                )
                return
            
            # Create embeds for each match
            embeds = []
            for match in match_details:
                embed = await self.create_match_embed(match, interaction.user)
                if embed:
                    embeds.append(embed)
            
            if embeds:
                await interaction.followup.send(embeds=embeds)
            else:
                await interaction.followup.send(
                    "Error creating match summary.",
                    ephemeral=True
                )
        
        except Exception as e:
            logger.error(f"Error in stalkmatches command: {e}")
            await interaction.followup.send(
                "An error occurred while processing the command.",
                ephemeral=True
            )

    async def create_match_embed(self, match_data: Dict, user: discord.User) -> Optional[discord.Embed]:
        """
        Create an embed for a match.
        
        Args:
            match_data: Match data
            user: Discord user who requested the embed
            
        Returns:
            Optional[discord.Embed]: Match embed or None
        """
        try:
            # Find the player in the match using PUUID (more reliable than name)
            participant = None
            for p in match_data['info']['participants']:
                if p['puuid'] == self.config.riot.puuid:
                    participant = p
                    break
            
            # Fallback to name matching if PUUID doesn't work
            if not participant:
                participant = next(
                    (p for p in match_data['info']['participants'] 
                     if p['summonerName'].lower() == self.config.riot.summoner_name.lower()),
                    None
                )
            
            if not participant:
                return None
            
            # Get basic match info
            queue_type = get_queue_type(match_data['info']['queueId'])
            game_duration = match_data['info']['gameDuration']
            minutes, seconds = divmod(game_duration, 60)
            relative_time = await self.get_relative_time(match_data['info']['gameCreation'])
            
            # Get player stats
            kills = participant['kills']
            deaths = participant['deaths']
            assists = participant['assists']
            cs = participant['totalMinionsKilled'] + participant.get('neutralMinionsKilled', 0)
            cs_per_min = cs / (game_duration / 60)

            # Get additional stats
            vision_score = participant.get('visionScore', 0)
            damage_dealt = participant.get('totalDamageDealtToChampions', 0)
            gold_earned = participant.get('goldEarned', 0)
            
            # Calculate comparative stats (with negative spin)
            def get_negative_spin_stats():
                all_participants = match_data['info']['participants']
                player_team_id = participant['teamId']
                player_position = participant.get('individualPosition', '')
                
                # Get team members
                team_members = [p for p in all_participants if p['teamId'] == player_team_id]
                
                # Helper function to add ordinal suffix
                def add_ordinal_suffix(num):
                    if 11 <= num <= 13:
                        return f"{num}th"
                    suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
                    return f"{num}{suffixes.get(num % 10, 'th')}"
                
                # Team damage ranking (worst to best)
                team_damage_sorted = sorted(team_members, key=lambda x: x.get('totalDamageDealtToChampions', 0))
                damage_rank = len(team_damage_sorted) - team_damage_sorted.index(participant)
                damage_spin = f"{add_ordinal_suffix(damage_rank)} lowest damage on team"
                
                # Team gold ranking (worst to best)  
                team_gold_sorted = sorted(team_members, key=lambda x: x.get('goldEarned', 0))
                gold_rank = len(team_gold_sorted) - team_gold_sorted.index(participant)
                gold_spin = f"{add_ordinal_suffix(gold_rank)} lowest gold on team"
                
                # Team vision ranking (worst to best)
                team_vision_sorted = sorted(team_members, key=lambda x: x.get('visionScore', 0))
                vision_rank = len(team_vision_sorted) - team_vision_sorted.index(participant)
                vision_spin = f"{add_ordinal_suffix(vision_rank)} lowest vision on team"
                
                # Lane opponent comparison (if available)
                lane_opponent = None
                if player_position:
                    opponents = [p for p in all_participants 
                               if p['teamId'] != player_team_id and 
                                  p.get('individualPosition') == player_position]
                    if opponents:
                        lane_opponent = opponents[0]
                
                return damage_spin, gold_spin, vision_spin, lane_opponent
            
            damage_spin, gold_spin, vision_spin, lane_opponent = get_negative_spin_stats()

            # Create the embed
            embed_color = discord.Color.green() if participant['win'] else discord.Color.red()
            embed = discord.Embed(
                title="Match Details",
                color=embed_color,
                description=f"View full match details on [OP.GG]"
                           f"(https://op.gg/summoners/{self.config.riot.region.lower()}/"
                           f"{self.config.riot.summoner_name}-{self.config.riot.summoner_tag})"
            )

            # Add champion icon
            champion_id = participant['championId']
            embed.set_thumbnail(
                url=f"https://cdn.communitydragon.org/latest/champion/{champion_id}/square"
            )

            # Add fields
            embed.add_field(name="Queue Type", value=queue_type, inline=True)
            embed.add_field(
                name="Result", 
                value="Victory" if participant['win'] else "Defeat",
                inline=True
            )
            embed.add_field(
                name="Duration",
                value=f"{minutes}m {seconds}s",
                inline=True
            )
            embed.add_field(
                name="KDA",
                value=f"{kills}/{deaths}/{assists} ({((kills + assists) / max(1, deaths)):.1f})",
                inline=True
            )
            embed.add_field(
                name="CS",
                value=f"{cs} ({cs_per_min:.1f}/min)",
                inline=True
            )
            embed.add_field(
                name="Time Ago",
                value=relative_time,
                inline=True
            )
            # Add new fields with negative spin
            embed.add_field(
                name="Vision Score",
                value=f"{vision_score} ({vision_spin})",
                inline=True
            )
            embed.add_field(
                name="Damage",
                value=f"{damage_dealt:,} ({damage_spin})",
                inline=True
            )
            embed.add_field(
                name="Gold",
                value=f"{gold_earned:,} ({gold_spin})",
                inline=True
            )

            # Add footer
            now = datetime.now()
            formatted_time = f"{now.strftime('%B')} {self.get_day_with_suffix(now.day)}, {now.strftime('at %I:%M %p')}"
            embed.set_footer(
                text=f"Requested by {user.name} • {formatted_time}",
                icon_url=user.avatar.url if user.avatar else None
            )

            return embed

        except Exception as e:
            logger.error(f"Error creating match embed: {e}")
            return None

    async def livegame(self, interaction: discord.Interaction) -> None:
        """
        Handle the livegame command.
        
        Args:
            interaction: Discord interaction
        """
        # Check rate limiting
        allowed = await self.rate_limiter.acquire()
        if not allowed:
            remaining_time = await self.rate_limiter.get_remaining_time()
            await interaction.response.send_message(
                f"Rate limit reached. Try again in {remaining_time} seconds.",
                ephemeral=True
            )
            return

        try:
            await interaction.response.defer()

            # Get summoner info
            summoner = await self.get_summoner_info()
            if not summoner:
                await interaction.followup.send(
                    f"Could not find summoner information for {self.config.riot.summoner_name}",
                    ephemeral=True
                )
                return

            # Get live game data using PUUID
            game_data = await self.api_client.get_current_game(
                summoner_id=summoner['id'],
                puuid=summoner['puuid']
            )
            
            if 'status' in game_data:
                if game_data['status'].get('status_code') == 404:
                    await interaction.followup.send(
                        f"{self.config.riot.summoner_name} is not currently in a game.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"Error fetching live game: {game_data['status'].get('message', 'Unknown error')}",
                        ephemeral=True
                    )
                return

            embed = await self.create_live_game_embed(game_data, interaction.user)
            if embed:
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "Error creating live game summary.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in livegame command: {e}")
            await interaction.followup.send(
                "An error occurred while processing the command.",
                ephemeral=True
            )

    async def create_live_game_embed(self, game_data: Dict, user: discord.User) -> Optional[discord.Embed]:
        """
        Create an embed for a live game.
        
        Args:
            game_data: Game data
            user: Discord user who requested the embed
            
        Returns:
            Optional[discord.Embed]: Live game embed or None
        """
        try:
            # Find the player in the game using PUUID (more reliable than name)
            participant = None
            for p in game_data['participants']:
                if p['puuid'] == self.config.riot.puuid:
                    participant = p
                    break
            
            # Fallback to name matching if PUUID doesn't work
            if not participant:
                participant = next(
                    (p for p in game_data['participants'] 
                     if p['summonerName'].lower() == self.config.riot.summoner_name.lower()),
                    None
                )
            
            if not participant:
                return None

            # Get game info
            queue_type = get_queue_type(game_data['gameQueueConfigId'])
            game_duration = game_data['gameLength'] // 60

            # Create embed
            embed = discord.Embed(
                title=f"Live Game - {self.config.riot.summoner_name}",
                description=f"Queue Type: {queue_type}",
                color=discord.Color.blue()
            )

            # Add champion info
            champion_id = participant['championId']
            embed.set_thumbnail(
                url=f"https://cdn.communitydragon.org/latest/champion/{champion_id}/square"
            )

            # Add summoner spells
            spell1_name = get_summoner_spell_name(participant['spell1Id'])
            spell2_name = get_summoner_spell_name(participant['spell2Id'])
            embed.add_field(
                name="Summoner Spells",
                value=f"{spell1_name[0]} {spell1_name[1]} | {spell2_name[0]} {spell2_name[1]}",
                inline=False
            )

            # Add game duration
            embed.add_field(
                name="Game Duration",
                value=f"{game_duration} minutes",
                inline=False
            )

            # Add teams
            allies = []
            enemies = []
            player_team = participant['teamId']

            for p in game_data['participants']:
                champ = get_champion_name(p['championId'])
                if p['teamId'] == player_team:
                    if p['summonerName'] == self.config.riot.summoner_name:
                        champ = f"__**{champ}**__"
                    allies.append(champ)
                else:
                    enemies.append(champ)

            embed.add_field(
                name="Ally Team",
                value=", ".join(allies) if allies else "No allies found",
                inline=False
            )
            embed.add_field(
                name="Enemy Team",
                value=", ".join(enemies) if enemies else "No enemies found",
                inline=False
            )

            # Add banned champions if any
            if 'bannedChampions' in game_data and game_data['bannedChampions']:
                bans = []
                for ban in game_data['bannedChampions']:
                    if ban['championId'] > 0:  # Ignore "no ban" (-1)
                        champ = get_champion_name(ban['championId'])
                        bans.append(champ.split(' ')[0])  # Get just the emoji
                
                if bans:
                    embed.add_field(
                        name="Banned Champions",
                        value=" | ".join(bans),
                        inline=False
                    )

            # Add footer
            now = datetime.now()
            formatted_time = f"{now.strftime('%B')} {self.get_day_with_suffix(now.day)}, {now.strftime('at %I:%M %p')}"
            embed.set_footer(
                text=f"Requested by {user.name} • {formatted_time}",
                icon_url=user.avatar.url if user.avatar else None
            )

            return embed

        except Exception as e:
            logger.error(f"Error creating live game embed: {e}")
            return None

    async def stalkrank(self, interaction: discord.Interaction) -> None:
        """
        Handle the stalkrank command.
        
        Args:
            interaction: Discord interaction
        """
        # Check rate limiting
        allowed = await self.rate_limiter.acquire()
        if not allowed:
            remaining_time = await self.rate_limiter.get_remaining_time()
            await interaction.response.send_message(
                f"Rate limit reached. Try again in {remaining_time} seconds.",
                ephemeral=True
            )
            return

        try:
            await interaction.response.defer()

            # Fetch current rank data
            rank_history = await self.db_manager.get_rank_history('RANKED_SOLO_5x5', days=30)
            if not rank_history:
                await interaction.followup.send(
                    f"No rank history found for {self.config.riot.summoner_name}",
                    ephemeral=True
                )
                return

            # Get current rank and calculate recent changes
            current_rank = rank_history[-1]  # Most recent entry
            tier = current_rank[0]
            division = current_rank[1]
            lp = current_rank[2]
            
            # Calculate LP changes and streak
            recent_games = rank_history[-5:] if len(rank_history) >= 5 else rank_history
            lp_changes = []
            for i in range(1, len(recent_games)):
                lp_diff = recent_games[i][2] - recent_games[i-1][2]
                lp_changes.append(lp_diff)
            
            # Calculate win/loss streak (simplified based on LP changes)
            streak = 0
            streak_type = "wins" if lp_changes and lp_changes[-1] > 0 else "losses"
            for lp_change in reversed(lp_changes):
                if (lp_change > 0 and streak_type == "wins") or (lp_change < 0 and streak_type == "losses"):
                    streak += 1
                else:
                    break

            # Create enhanced rank embed
            embed = discord.Embed(
                title=f"{self.config.riot.summoner_name}'s Solo Queue Progress",
                color=discord.Color.gold() if tier == "GOLD" else 
                      discord.Color.teal() if tier == "PLATINUM" else
                      discord.Color.green() if tier == "EMERALD" else
                      discord.Color.blue()
            )

            # Add rank emoji and formatted rank string
            rank_emoji = get_rank_emoji(tier)
            rank_str = f"{rank_emoji} **{tier} {division} - {lp} LP**"
            embed.description = rank_str
            
            # Add streak information if significant
            if streak >= 2:
                embed.add_field(
                    name="Current Streak",
                    value=f"{streak} {streak_type} in a row",
                    inline=True
                )
            
            # Add recent LP changes
            if lp_changes:
                total_lp_change = sum(lp_changes)
                embed.add_field(
                    name="Recent LP Change",
                    value=f"{total_lp_change:+d} LP (last {len(lp_changes)} games)",
                    inline=True
                )

            # Generate enhanced rank graph
            try:
                graph_buffer = generate_rank_graph(rank_history, [r[4] for r in rank_history])  # r[4] is match_id
                if isinstance(graph_buffer, str):
                    # Error occurred
                    await interaction.followup.send(
                        f"Error generating rank graph: {graph_buffer}",
                        ephemeral=True
                    )
                    return

                # Add graph as image
                file = discord.File(graph_buffer, "rank_progression.png")
                embed.set_image(url="attachment://rank_progression.png")
                
                # Add graph description
                embed.add_field(
                    name="Graph Legend",
                    value="🔺 Promotions • 🔻 Demotions • Colors = Rank Tiers",
                    inline=False
                )
                
            except Exception as e:
                logger.error(f"Error generating rank graph: {e}")
                # Enhanced fallback information
                embed.add_field(
                    name="Rank History",
                    value=f"Showing {len(rank_history)} rank changes over 30 days",
                    inline=False
                )
                embed.add_field(
                    name="Note",
                    value="Rank visualization temporarily unavailable",
                    inline=False
                )
                file = None

            # Add footer
            now = datetime.now()
            formatted_time = f"{now.strftime('%B')} {self.get_day_with_suffix(now.day)}, {now.strftime('at %I:%M %p')}"
            embed.set_footer(
                text=f"Requested by {interaction.user.name} • {formatted_time}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )

            if file:
                await interaction.followup.send(embed=embed, file=file)
            else:
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in stalkrank command: {e}")
            await interaction.followup.send(
                "An error occurred while processing the command.",
                ephemeral=True
            )