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

    def add_time_jitter(self, dates: List[datetime], ranks: List[float], max_jitter_hours: int = 12) -> List[datetime]:
        """Add horizontal jitter to dates while preserving chronological order"""
        date_nums = mdates.date2num(dates)
        jittered_dates = date_nums.copy()
        
        # Group by rank but maintain order within groups
        rank_groups = defaultdict(list)
        for i, rank in enumerate(ranks):
            rank_groups[rank].append((i, date_nums[i]))
        
        # Sort points within each rank group by original date
        for rank in rank_groups:
            group = rank_groups[rank]
            if len(group) > 1:
                group.sort(key=lambda x: x[1])
                indices = [x[0] for x in group]
                
                # Generate evenly spaced jitter values
                span = max_jitter_hours / 24
                if len(group) > 1:
                    jitters = np.linspace(-span/2, span/2, len(group))
                    
                    # Apply jitter while maintaining order
                    for idx, jitter in zip(indices, jitters):
                        jittered_dates[idx] = date_nums[idx] + jitter
        
        return mdates.num2date(jittered_dates)

    def calculate_rank_position(self, rank: str, lp: Optional[int]) -> float:
        """Calculate numeric position for a rank with LP"""
        base_position = self.rank_to_numeric.get(rank, -1)
        if base_position >= 0 and lp is not None:
            base_position += lp / 100.0
        return base_position

    def generate_graph(self, rank_history: List[Tuple]) -> io.BytesIO:
        """Generate rank progression graph"""
        try:
            if not rank_history:
                raise ValueError("No rank history data available")

            # Calculate date cutoff (30 days ago)
            latest_date = max(datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S") for row in rank_history)
            cutoff_date = latest_date - timedelta(days=30)

            # Filter for last 30 days and extract data
            recent_history = [row for row in rank_history 
                            if datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S") >= cutoff_date]

            all_dates = [datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S") for row in recent_history]
            all_ranks = [f"{row[0]} {row[1]}" for row in recent_history]
            all_lp = [row[2] for row in recent_history]

            # Filter significant points
            significant_indices = []
            prev_rank = None
            prev_lp = None
            
            for i, (rank, lp) in enumerate(zip(all_ranks, all_lp)):
                is_significant = False
                
                if i == 0 or i == len(all_ranks) - 1:
                    is_significant = True
                elif rank != prev_rank:
                    is_significant = True
                    if i > 0 and i-1 not in significant_indices:
                        significant_indices.append(i-1)
                elif prev_lp is not None and abs(lp - prev_lp) >= 30:
                    is_significant = True
                
                if is_significant:
                    significant_indices.append(i)
                
                prev_rank = rank
                prev_lp = lp

            # Filter data
            dates = [all_dates[i] for i in significant_indices]
            ranks = [all_ranks[i] for i in significant_indices]
            lps = [all_lp[i] for i in significant_indices]

            # Convert ranks to numeric values with LP interpolation
            numeric_ranks = [self.calculate_rank_position(rank, lp) 
                           for rank, lp in zip(ranks, lps)]

            # Add jitter to dates while preserving order
            jittered_dates = self.add_time_jitter(dates, numeric_ranks)

            # Calculate visible range
            if numeric_ranks:
                min_recent = min(min(int(r) for r in numeric_ranks if r >= 0), 
                               self.rank_to_numeric["EMERALD IV"])
                max_recent = max(int(r) for r in numeric_ranks if r >= 0)
                
                visible_start = min(min_recent, self.rank_to_numeric["EMERALD IV"])
                visible_end = min(len(self.full_rank_order) - 1, max_recent + 2)
                
                if visible_end - visible_start < 5:
                    visible_end = min(len(self.full_rank_order) - 1, visible_start + 5)
                
                visible_ranks = self.full_rank_order[visible_start:visible_end + 1]
            else:
                visible_ranks = self.full_rank_order[20:28]  # Default to Emerald-Diamond range
                visible_start = 20
                visible_end = 27

            # Set style and create figure
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 8), dpi=100)

            # Plot line connecting points
            plt.plot(jittered_dates, 
                    [r - visible_start for r in numeric_ranks],
                    color="cyan", label="Rank Progression", linewidth=2, zorder=2, alpha=0.3)

            # Plot points
            plt.scatter(jittered_dates, 
                       [r - visible_start for r in numeric_ranks],
                       color='cyan', s=50, edgecolor='white', linewidth=1, zorder=3)

            # Add LP markers for first and last points
            for i, (date, rank, lp) in [(0, (jittered_dates[0], numeric_ranks[0], lps[0])), 
                                       (-1, (jittered_dates[-1], numeric_ranks[-1], lps[-1]))]:
                plt.annotate(f"{lp} LP", 
                            (date, rank - visible_start),
                            xytext=(0, 10),
                            textcoords='offset points',
                            ha='center',
                            va='bottom',
                            fontsize=8,
                            color='white',
                            bbox=dict(facecolor='black', edgecolor='none', alpha=0.7))

            # Format axes
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
            plt.xticks(rotation=30, ha='right', fontsize=8, color="white")
            plt.yticks(range(len(visible_ranks)), visible_ranks, color="white", fontsize=8)

            # Add grid
            plt.grid(which='major', color="gray", linestyle="--", linewidth=0.5, alpha=0.3, zorder=1)

            # Labels and title
            plt.xlabel("Date", fontsize=10, color="white", labelpad=10)
            plt.ylabel("Rank", fontsize=10, color="white", labelpad=10)
            plt.title("Rank Progression (Past 30 Days)", 
                     fontsize=12, color="white", pad=20)

            # Legend
            legend = plt.legend(facecolor='black', 
                              edgecolor='white', 
                              fontsize=8, 
                              loc='upper right',
                              framealpha=0.8)
            for text in legend.get_texts():
                text.set_color('white')

            # Set axis limits
            plt.ylim(-0.5, len(visible_ranks) - 0.5)
            plt.xlim(cutoff_date, latest_date + timedelta(days=1))

            plt.tight_layout()

            # Save to BytesIO
            buf = io.BytesIO()
            plt.savefig(buf, 
                       format='png', 
                       facecolor='black', 
                       edgecolor='none', 
                       bbox_inches='tight',
                       dpi=100)
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