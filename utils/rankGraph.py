import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import io
import logging
from typing import List, Tuple, Optional
from config_manager import ConfigManager

logger = logging.getLogger(__name__)

class GameSession:
    """Represents a gaming session - a cluster of games played within a time window."""
    
    def __init__(self, first_game_data: Tuple):
        """Initialize session with the first game."""
        self.start_time = datetime.strptime(first_game_data[3], "%Y-%m-%d %H:%M:%S")
        self.end_time = self.start_time
        self.games = [first_game_data]
        self.start_rank = f"{first_game_data[0]} {first_game_data[1]}"
        self.start_lp = first_game_data[2]
        self.end_rank = self.start_rank
        self.end_lp = self.start_lp
        self.has_rank_change = False
        
    def add_game(self, game_data: Tuple) -> None:
        """Add a game to this session."""
        game_time = datetime.strptime(game_data[3], "%Y-%m-%d %H:%M:%S")
        self.end_time = game_time
        self.games.append(game_data)
        
        # Update end state
        new_rank = f"{game_data[0]} {game_data[1]}"
        if new_rank != self.end_rank:
            self.has_rank_change = True
        self.end_rank = new_rank
        self.end_lp = game_data[2]
    
    def can_add_game(self, game_data: Tuple, max_gap_minutes: int = 45) -> bool:
        """Check if a game can be added to this session based on time gap."""
        game_time = datetime.strptime(game_data[3], "%Y-%m-%d %H:%M:%S")
        gap = (game_time - self.end_time).total_seconds() / 60
        return gap <= max_gap_minutes
    
    @property
    def game_count(self) -> int:
        """Number of games in this session."""
        return len(self.games)
    
    @property
    def net_lp_change(self) -> int:
        """Net LP change during this session."""
        return self.end_lp - self.start_lp
    
    @property
    def duration_minutes(self) -> int:
        """Duration of the session in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)
    
    @property
    def session_type(self) -> str:
        """Classify the session type for visualization."""
        if self.game_count == 1:
            return "single"
        elif self.has_rank_change:
            return "rank_change"
        elif self.net_lp_change > 0:
            return "winning"
        else:
            return "losing"
    
    def get_summary_text(self) -> str:
        """Get a text summary of the session for annotations."""
        if self.game_count == 1:
            return f"{self.end_lp} LP"
        else:
            if self.has_rank_change:
                return f"{self.game_count} games\n{self.start_rank}→{self.end_rank}\n{self.net_lp_change:+d} LP"
            else:
                return f"{self.game_count} games\n{self.net_lp_change:+d} LP"

class RankGraphGenerator:
    def __init__(self):
        self.full_rank_order = [
            "IRON IV", "IRON III", "IRON II", "IRON I",
            "BRONZE IV", "BRONZE III", "BRONZE II", "BRONZE I",
            "SILVER IV", "SILVER III", "SILVER II", "SILVER I",
            "GOLD IV", "GOLD III", "GOLD II", "GOLD I",
            "PLATINUM IV", "PLATINUM III", "PLATINUM II", "PLATINUM I",
            "EMERALD IV", "EMERALD III", "EMERALD II", "EMERALD I",
            "DIAMOND IV", "DIAMOND III", "DIAMOND II", "DIAMOND I",
            "MASTER", "GRANDMASTER", "CHALLENGER"
        ]
        self.rank_to_numeric = {rank: i for i, rank in enumerate(self.full_rank_order)}
        
        # Tier-based color scheme
        self.tier_colors = {
            "IRON": "#6B4423",
            "BRONZE": "#B87333", 
            "SILVER": "#C0C0C0",
            "GOLD": "#FFD700",
            "PLATINUM": "#00CED1",
            "EMERALD": "#50C878",
            "DIAMOND": "#B9F2FF",
            "MASTER": "#9966CC",
            "GRANDMASTER": "#FF6B6B",
            "CHALLENGER": "#FFE66D"
        }
        
        # Shorter rank labels for better display
        self.rank_labels = {
            "IRON IV": "I4", "IRON III": "I3", "IRON II": "I2", "IRON I": "I1",
            "BRONZE IV": "B4", "BRONZE III": "B3", "BRONZE II": "B2", "BRONZE I": "B1",
            "SILVER IV": "S4", "SILVER III": "S3", "SILVER II": "S2", "SILVER I": "S1",
            "GOLD IV": "G4", "GOLD III": "G3", "GOLD II": "G2", "GOLD I": "G1",
            "PLATINUM IV": "P4", "PLATINUM III": "P3", "PLATINUM II": "P2", "PLATINUM I": "P1",
            "EMERALD IV": "E4", "EMERALD III": "E3", "EMERALD II": "E2", "EMERALD I": "E1",
            "DIAMOND IV": "D4", "DIAMOND III": "D3", "DIAMOND II": "D2", "DIAMOND I": "D1",
            "MASTER": "M", "GRANDMASTER": "GM", "CHALLENGER": "C"
        }

    def get_tier_from_rank(self, rank: str) -> str:
        """Extract tier from rank string (e.g., 'GOLD II' -> 'GOLD')"""
        return rank.split()[0] if ' ' in rank else rank
    
    def get_rank_color(self, rank: str) -> str:
        """Get color for a specific rank based on its tier"""
        tier = self.get_tier_from_rank(rank)
        return self.tier_colors.get(tier, "#FFFFFF")

    def calculate_rank_position(self, rank: str, lp: Optional[int]) -> float:
        """Calculate numeric position for a rank with LP"""
        base_position = self.rank_to_numeric.get(rank, -1)
        if base_position >= 0 and lp is not None:
            base_position += lp / 100.0
        return base_position

    def filter_significant_points(self, dates: List[datetime], ranks: List[str], lps: List[int]) -> Tuple[List[datetime], List[str], List[int]]:
        """Intelligently filter points to show meaningful progression"""
        if len(dates) <= 2:
            return dates, ranks, lps
        
        significant_indices = [0]  # Always include first point
        
        for i in range(1, len(ranks) - 1):
            is_significant = False
            
            # Always include rank changes
            if ranks[i] != ranks[i-1]:
                is_significant = True
                # Also include the point before rank change for context
                if i-1 not in significant_indices:
                    significant_indices.append(i-1)
            
            # Include significant LP changes (20+ LP, not 30+)
            elif abs(lps[i] - lps[i-1]) >= 20:
                is_significant = True
            
            # Include LP milestones (0, 25, 50, 75, 100)
            elif lps[i] in [0, 25, 50, 75, 100] and lps[i-1] not in [0, 25, 50, 75, 100]:
                is_significant = True
            
            if is_significant:
                significant_indices.append(i)
        
        significant_indices.append(len(ranks) - 1)  # Always include last point
        
        # Remove duplicates and sort
        significant_indices = sorted(list(set(significant_indices)))
        
        return ([dates[i] for i in significant_indices], 
                [ranks[i] for i in significant_indices], 
                [lps[i] for i in significant_indices])

    def calculate_dynamic_range(self, numeric_ranks: List[float]) -> Tuple[int, int, List[str]]:
        """Calculate optimal visible range based on actual data"""
        if not numeric_ranks:
            # Default to Gold-Plat range if no data
            start_idx = self.rank_to_numeric["GOLD IV"]
            end_idx = self.rank_to_numeric["PLATINUM I"]
            return start_idx, end_idx, self.full_rank_order[start_idx:end_idx + 1]
        
        min_rank = min(int(r) for r in numeric_ranks if r >= 0)
        max_rank = max(int(r) for r in numeric_ranks if r >= 0)
        
        # Add padding above and below
        visible_start = max(0, min_rank - 2)
        visible_end = min(len(self.full_rank_order) - 1, max_rank + 2)
        
        # Ensure minimum range of 6 ranks
        if visible_end - visible_start < 5:
            center = (visible_start + visible_end) // 2
            visible_start = max(0, center - 3)
            visible_end = min(len(self.full_rank_order) - 1, center + 3)
        
        visible_ranks = self.full_rank_order[visible_start:visible_end + 1]
        return visible_start, visible_end, visible_ranks

    def cluster_games_into_sessions(self, rank_history: List[Tuple], max_gap_minutes: int = 45) -> List[GameSession]:
        """
        Cluster games into sessions based on time gaps.
        
        Args:
            rank_history: List of rank data tuples (tier, rank, lp, timestamp, match_id)
            max_gap_minutes: Maximum gap between games in the same session
            
        Returns:
            List[GameSession]: Gaming sessions
        """
        if not rank_history:
            return []
            
        # Sort by timestamp to ensure chronological order
        sorted_history = sorted(rank_history, key=lambda x: datetime.strptime(x[3], "%Y-%m-%d %H:%M:%S"))
        
        sessions = []
        current_session = None
        
        for game_data in sorted_history:
            if current_session is None:
                # Start first session
                current_session = GameSession(game_data)
            elif current_session.can_add_game(game_data, max_gap_minutes):
                # Add to current session
                current_session.add_game(game_data)
            else:
                # Gap too large, finish current session and start new one
                sessions.append(current_session)
                current_session = GameSession(game_data)
        
        # Don't forget the last session
        if current_session is not None:
            sessions.append(current_session)
            
        return sessions

    def should_use_session_clustering(self, rank_history: List[Tuple]) -> bool:
        """
        Determine if session clustering would be beneficial for this data.
        
        Args:
            rank_history: List of rank data tuples
            
        Returns:
            bool: True if clustering should be used
        """
        if len(rank_history) < 5:
            return False
            
        # Check for dense gaming patterns (multiple games within short time periods)
        dates = [datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S") for row in rank_history]
        
        # Count games within 2-hour windows
        dense_periods = 0
        for i, date in enumerate(dates):
            games_in_window = sum(1 for other_date in dates[i:i+10] 
                                if (other_date - date).total_seconds() <= 7200)  # 2 hours
            if games_in_window >= 3:
                dense_periods += 1
                
        # Use clustering if we have multiple dense periods
        return dense_periods >= 2

    def generate_graph(self, rank_history: List[Tuple]) -> io.BytesIO:
        """Generate an enhanced rank progression graph"""
        try:
            if not rank_history:
                raise ValueError("No rank history data available")

            # Calculate date cutoff (30 days ago)
            latest_date = max(datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S") for row in rank_history)
            cutoff_date = latest_date - timedelta(days=30)

            # Filter for last 30 days and extract data
            recent_history = [row for row in rank_history 
                            if datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S") >= cutoff_date]

            # Decide whether to use session clustering or individual games
            use_clustering = self.should_use_session_clustering(recent_history)
            
            if use_clustering:
                # Use session clustering for dense data
                sessions = self.cluster_games_into_sessions(recent_history)
                
                # Extract session data for plotting
                dates = [session.end_time for session in sessions]  # Use end time as plot point
                ranks = [session.end_rank for session in sessions]
                lps = [session.end_lp for session in sessions]
                session_data = sessions  # Keep session objects for enhanced visualization
                
            else:
                # Use traditional approach for sparse data
                all_dates = [datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S") for row in recent_history]
                all_ranks = [f"{row[0]} {row[1]}" for row in recent_history]
                all_lp = [row[2] for row in recent_history]
                
                # Intelligent filtering of significant points
                dates, ranks, lps = self.filter_significant_points(all_dates, all_ranks, all_lp)
                session_data = None

            # Convert ranks to numeric values with LP interpolation
            numeric_ranks = [self.calculate_rank_position(rank, lp) for rank, lp in zip(ranks, lps)]

            # Calculate dynamic visible range
            visible_start, visible_end, visible_ranks = self.calculate_dynamic_range(numeric_ranks)

            # Set up the plot with dark theme
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(14, 8), dpi=120)
            fig.patch.set_facecolor('#0F1419')
            ax.set_facecolor('#0F1419')

            # Create segments with tier-based colors
            for i in range(len(dates) - 1):
                start_rank = ranks[i]
                end_rank = ranks[i + 1]
                start_color = self.get_rank_color(start_rank)
                
                # Plot line segment
                plt.plot([dates[i], dates[i + 1]], 
                        [numeric_ranks[i] - visible_start, numeric_ranks[i + 1] - visible_start],
                        color=start_color, linewidth=3, alpha=0.8, zorder=2)

            # Plot points - different logic for sessions vs individual games
            if use_clustering and session_data:
                # Session-based visualization
                for i, (session, date, rank, lp, numeric_rank) in enumerate(zip(session_data, dates, ranks, lps, numeric_ranks)):
                    color = self.get_rank_color(rank)
                    
                    # Session-specific styling
                    if session.session_type == "single":
                        marker = 'o'
                        base_size = 60
                        edge_color = 'white'
                    elif session.session_type == "rank_change":
                        marker = '^' if session.net_lp_change > 0 else 'v'
                        base_size = 80
                        edge_color = '#00FF00' if session.net_lp_change > 0 else '#FF4444'
                    elif session.session_type == "winning":
                        marker = 's'  # Square for winning sessions
                        base_size = 70
                        edge_color = '#00AA00'
                    else:  # losing session
                        marker = 's'  # Square for losing sessions
                        base_size = 70
                        edge_color = '#AA0000'
                    
                    # Scale size by game count (but not too dramatically)
                    size = base_size + min(session.game_count * 8, 40)
                    
                    plt.scatter(date, numeric_rank - visible_start, 
                              color=color, s=size, marker=marker,
                              edgecolor=edge_color, linewidth=2, zorder=3)
                    
                    # Session annotations
                    annotation_text = session.get_summary_text()
                    
                    # Position annotations to avoid overlap
                    y_offset = 20 if i % 2 == 0 else -25
                    va = 'bottom' if y_offset > 0 else 'top'
                    
                    plt.annotate(annotation_text,
                                (date, numeric_rank - visible_start),
                                xytext=(0, y_offset),
                                textcoords='offset points',
                                ha='center', va=va,
                                fontsize=8, color='white', weight='bold',
                                bbox=dict(boxstyle='round,pad=0.4', 
                                         facecolor='black', alpha=0.9, edgecolor='none'))
                                         
            else:
                # Traditional individual game visualization
                for i, (date, rank, lp, numeric_rank) in enumerate(zip(dates, ranks, lps, numeric_ranks)):
                    color = self.get_rank_color(rank)
                    
                    # Check if this is a promotion/demotion
                    is_promotion = i > 0 and numeric_rank > numeric_ranks[i-1] and ranks[i] != ranks[i-1]
                    is_demotion = i > 0 and numeric_rank < numeric_ranks[i-1] and ranks[i] != ranks[i-1]
                    
                    # Different markers for different events
                    if is_promotion:
                        marker = '^'  # Triangle up for promotion
                        size = 80
                        edge_color = '#00FF00'
                    elif is_demotion:
                        marker = 'v'  # Triangle down for demotion
                        size = 80
                        edge_color = '#FF4444'
                    else:
                        marker = 'o'  # Circle for normal points
                        size = 60
                        edge_color = 'white'
                    
                    plt.scatter(date, numeric_rank - visible_start, 
                              color=color, s=size, marker=marker,
                              edgecolor=edge_color, linewidth=2, zorder=3)
                    
                    # Add LP annotations for significant points
                    if i == 0 or i == len(dates) - 1 or is_promotion or is_demotion:
                        plt.annotate(f"{lp} LP", 
                                    (date, numeric_rank - visible_start),
                                    xytext=(0, 15),
                                    textcoords='offset points',
                                    ha='center', va='bottom',
                                    fontsize=9, color='white', weight='bold',
                                    bbox=dict(boxstyle='round,pad=0.3', 
                                             facecolor='black', alpha=0.8, edgecolor='none'))

            # Format axes with shorter labels
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 8)))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            plt.xticks(rotation=45, ha='right', fontsize=10, color="#E0E0E0")
            
            # Use shorter rank labels
            short_labels = [self.rank_labels.get(rank, rank) for rank in visible_ranks]
            plt.yticks(range(len(visible_ranks)), short_labels, color="#E0E0E0", fontsize=10)

            # Enhanced grid
            plt.grid(which='major', color="#333333", linestyle="-", linewidth=0.5, alpha=0.6, zorder=1)
            plt.grid(which='minor', color="#222222", linestyle=":", linewidth=0.3, alpha=0.4, zorder=1)

            # Styling and labels
            plt.xlabel("Date", fontsize=12, color="#E0E0E0", labelpad=15)
            plt.ylabel("Rank", fontsize=12, color="#E0E0E0", labelpad=15)
            
            # Dynamic title with current rank
            current_rank = ranks[-1]
            current_lp = lps[-1]
            plt.title(f"Rank Progression: {current_rank} ({current_lp} LP)", 
                     fontsize=14, color="#E0E0E0", pad=25, weight='bold')

            # Dynamic legend based on visualization mode
            from matplotlib.lines import Line2D
            
            if use_clustering and session_data:
                # Session-based legend
                legend_elements = [
                    Line2D([0], [0], marker='s', color='w', markerfacecolor='#00AA00', 
                           markersize=8, label='Winning Sessions', linestyle='None'),
                    Line2D([0], [0], marker='s', color='w', markerfacecolor='#AA0000', 
                           markersize=8, label='Losing Sessions', linestyle='None'),
                    Line2D([0], [0], marker='^', color='w', markerfacecolor='#00FF00', 
                           markersize=8, label='Rank Up Sessions', linestyle='None'),
                    Line2D([0], [0], marker='o', color='w', markerfacecolor='#888888', 
                           markersize=6, label='Single Games', linestyle='None')
                ]
                legend_title = "Gaming Sessions (size = game count)"
            else:
                # Traditional legend
                legend_elements = [
                    Line2D([0], [0], marker='^', color='w', markerfacecolor='#00FF00', 
                           markersize=8, label='Promotion', linestyle='None'),
                    Line2D([0], [0], marker='v', color='w', markerfacecolor='#FF4444', 
                           markersize=8, label='Demotion', linestyle='None'),
                    Line2D([0], [0], marker='o', color='w', markerfacecolor='#888888', 
                           markersize=8, label='LP Change', linestyle='None')
                ]
                legend_title = "Individual Games"
                
            legend = plt.legend(handles=legend_elements, loc='upper left', 
                              facecolor='#1a1a1a', edgecolor='#444444', 
                              fontsize=9, framealpha=0.9, title=legend_title)
            legend.get_title().set_color('#E0E0E0')
            legend.get_title().set_fontsize(9)
            for text in legend.get_texts():
                text.set_color('#E0E0E0')

            # Set axis limits with padding
            plt.ylim(-0.8, len(visible_ranks) - 0.2)
            date_range = latest_date - cutoff_date
            plt.xlim(cutoff_date - date_range * 0.02, latest_date + date_range * 0.02)

            # Remove spines for cleaner look
            for spine in ax.spines.values():
                spine.set_color('#444444')
                spine.set_linewidth(1)

            plt.tight_layout()

            # Save with high quality
            buf = io.BytesIO()
            plt.savefig(buf, format='png', facecolor='#0F1419', edgecolor='none', 
                       bbox_inches='tight', dpi=120, pad_inches=0.2)
            plt.close()
            buf.seek(0)
            return buf

        except Exception as e:
            logger.error(f"Error generating rank graph: {e}")
            raise

def generate_rank_graph(rank_history: List[Tuple], match_ids: List[str]) -> io.BytesIO:
    """Wrapper function for backward compatibility"""
    generator = RankGraphGenerator()
    return generator.generate_graph(rank_history)