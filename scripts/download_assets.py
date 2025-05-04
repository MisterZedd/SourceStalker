import aiohttp
import asyncio
import os
from pathlib import Path
from PIL import Image
import io

async def process_and_save_image(response_data: bytes, filepath: str, trim: bool = False):
    """Process image data and save to file, with optional trimming of transparent edges"""
    # Load image from bytes
    img = Image.open(io.BytesIO(response_data))
    
    if trim and img.mode == 'RGBA':
        # Get the alpha channel
        alpha = img.getchannel('A')
        
        # Get boundaries of non-transparent pixels
        bbox = alpha.getbbox()
        if bbox:
            # Crop to content
            img = img.crop(bbox)
            
            # Add small padding (10px on each side)
            padding = 10
            new_size = (img.width + padding*2, img.height + padding*2)
            padded_img = Image.new('RGBA', new_size, (0, 0, 0, 0))
            padded_img.paste(img, (padding, padding))
            img = padded_img
    
    # Resize if needed (maximum 128x128 for Discord)
    if img.width > 128 or img.height > 128:
        img.thumbnail((128, 128), Image.Resampling.LANCZOS)
    
    # Save the processed image
    img.save(filepath, 'PNG', optimize=True)

async def download_file(session, url, filename, folder, trim=False):
    """Download and process a single file"""
    Path(folder).mkdir(parents=True, exist_ok=True)
    filepath = os.path.join(folder, filename)
    
    try:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                await process_and_save_image(image_data, filepath, trim=trim)
                print(f"Downloaded and processed: {filename}")
                return True
        print(f"Failed to download: {filename} (Status: {response.status})")
        print(f"URL: {url}")
        return False
    except Exception as e:
        print(f"Error processing {filename}: {str(e)}")
        return False

async def download_assets():
    """Download all required assets"""
    base_url = "https://raw.communitydragon.org/latest/plugins/"
    
    async with aiohttp.ClientSession() as session:
        # Download champion icons
        print("Downloading champion icons...")
        champion_url = f"{base_url}rcp-be-lol-game-data/global/default/v1/champion-summary.json"
        async with session.get(champion_url) as response:
            if response.status != 200:
                print(f"Failed to fetch champion data: {response.status}")
                return
            champions = await response.json()

        for champion in champions:
            champion_id = champion.get('id')
            if champion_id:
                await download_file(
                    session,
                    f"{base_url}rcp-be-lol-game-data/global/default/v1/champion-icons/{champion_id}.png",
                    f"{champion_id}.png",
                    "emoji_assets/champions"
                )
        
        # Download rank emblems
        print("\nDownloading rank emblems...")
        ranks = {
            'IRON': 'emblem-iron.png',
            'BRONZE': 'emblem-bronze.png',
            'SILVER': 'emblem-silver.png',
            'GOLD': 'emblem-gold.png',
            'PLATINUM': 'emblem-platinum.png',
            'EMERALD': 'emblem-emerald.png',
            'DIAMOND': 'emblem-diamond.png',
            'MASTER': 'emblem-master.png',
            'GRANDMASTER': 'emblem-grandmaster.png',
            'CHALLENGER': 'emblem-challenger.png'
        }

        for rank_name, rank_file in ranks.items():
            await download_file(
                session,
                f"{base_url}rcp-fe-lol-static-assets/global/default/images/ranked-emblem/{rank_file}",
                f"{rank_name}.png",
                "emoji_assets/ranks",
                trim=True  # Enable trimming for rank emblems
            )
        
        # Download summoner spells
        print("\nDownloading summoner spells...")
        spell_paths = {
            'BARRIER': 'summonerbarrier.png',
            'CLEANSE': 'summoner_boost.png',
            'EXHAUST': 'summoner_exhaust.png',
            'FLASH': 'summoner_flash.png',
            'GHOST': 'summoner_haste.png',
            'HEAL': 'summoner_heal.png',
            'IGNITE': 'summonerignite.png',
            'CLARITY': 'summonermana.png',
            'SMITE': 'summoner_smite.png',
            'TELEPORT': 'summoner_teleport_new.png',
            'MARK': 'summoner_mark.png',
            'totheking': 'benevolence_of_king_poro_icon.png',
            'flee': 'icon_summonerspell_flee.2v2_mode_fighters.png'
        }

        for spell_name, spell_file in spell_paths.items():
            await download_file(
                session,
                f"{base_url}rcp-be-lol-game-data/global/default/data/spells/icons2d/{spell_file}",
                f"{spell_name.lower()}.png",
                "emoji_assets/spells"
            )

if __name__ == "__main__":
    print("Starting asset download...")
    asyncio.run(download_assets())
    print("\nDownload complete!")