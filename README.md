# SourceStalker V3 Setup Guide

SourceStalker is a Discord bot that tracks League of Legends players with live game monitoring, match history, and rank progression visualization.

## Setup Options

Choose one of two setup methods:

### Option A: Docker Setup (Recommended for Windows)
### Option B: Native Python Setup (Recommended for Linux/macOS)

---

## Option A: Docker Setup (Windows)

### Prerequisites

1. **Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop
   - System Requirements:
     - Windows 10/11
     - WSL 2 (Windows Subsystem for Linux)
     - Virtualization enabled in BIOS

2. **Git for Windows**
   - Download from: https://git-scm.com/download/win
   - Used to clone the repository

3. **Required Accounts/API Keys**
   - Discord Developer Account
   - Discord Bot Token
   - Riot Games API Key

---

## Option B: Native Python Setup (Linux/macOS)

### Prerequisites

1. **Python 3.9+**
   - Linux: `sudo apt install python3 python3-pip python3-venv` (Ubuntu/Debian)
   - macOS: Install via Homebrew `brew install python` or download from python.org

2. **Git**
   - Linux: `sudo apt install git` (Ubuntu/Debian)
   - macOS: `brew install git` or use Xcode Command Line Tools

3. **Required Accounts/API Keys**
   - Discord Developer Account  
   - Discord Bot Token
   - Riot Games API Key

---

## Common Setup Steps

### 1. Create a Discord Bot

1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Give your application a name (e.g., "SourceStalker")
4. Go to the "Bot" section
5. Click "Add Bot"
6. Under "Token", click "Copy" to copy your bot token (save this for later)
7. Under "Privileged Gateway Intents", enable:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
8. Go to "OAuth2" > "URL Generator"
9. Select the following scopes:
   - bot
   - applications.commands
10. Select the following bot permissions:
    - Send Messages
    - Embed Links
    - Attach Files
    - Read Message History
    - Use Slash Commands
11. Copy the generated URL and use it to invite the bot to your server

### 2. Get a Riot Games API Key

1. Go to https://developer.riotgames.com/
2. Sign in with your Riot Developer account
3. Register a new application
4. Wait for application approval
5. Save the application API key for later use

---

## Setup Instructions

### Docker Setup (Windows)

1. **Install Docker Desktop** (if not already installed)
   - Download and install Docker Desktop
   - Enable WSL 2 when prompted
   - Restart your computer
   - Ensure Docker is running (system tray icon)

2. **Set Up the Project**
```cmd
mkdir C:\SourceStalker
cd C:\SourceStalker
git clone [repository-url] .
mkdir config
```

3. **Download Emoji Assets**
```cmd
python scripts/download_assets.py
```

4. **Configure and Run**
```cmd
docker-compose up
```

### Native Python Setup (Linux/macOS)

1. **Set Up the Project**
```bash
git clone [repository-url] SourceStalker
cd SourceStalker
```

2. **Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Download Emoji Assets**
```bash
python scripts/download_assets.py
```

5. **Create Config Directory**
```bash
mkdir config
```

6. **Run the Bot**
```bash
python main.py
```

---

## Initial Configuration

When you first run the bot, a configuration GUI will appear. Fill in:

- **Discord Bot Token** (from Discord Developer Portal)
- **Discord Channel ID** (Right-click channel in Discord > Copy ID)  
- **Riot API Key** (from Riot Developer Portal)
- **Summoner Name and Tag** (e.g., "PlayerName#NA1")
- **Select your region** (NA1, EUW1, etc.)
- Leave other settings at default unless you need to change them

Click "Save Configuration", then you can close the window. The bot is now running.

## Running the Bot

### Docker Commands
- Start: `docker-compose up -d`
- Stop: `docker-compose down`
- View logs: `docker-compose logs -f`

### Native Python Commands  
- Start: `python main.py` (with virtual environment activated)
- Stop: Ctrl+C in terminal

## Available Commands

Once the bot is running, you can use these commands in your Discord server:

- `/stalkmatches` - View recent match history with detailed stats and KDA
- `/livegame` - Check if the player is in a game and see team compositions
- `/stalkrank` - View current rank and 30-day rank progression graph
- `/sync` - (Owner only) Manually sync slash commands if they're not working
  - Use `/sync global_sync:True` to sync commands to all servers

The bot will also automatically:
- Monitor when the tracked player enters a game
- Send notifications for game results (win/loss)
- Track death count and LP changes after ranked games

## Emoji Assets

SourceStalker uses emoji assets for champions, ranks, and summoner spells. These are **not included in the repository** to keep it lightweight.

### Download Assets
Run this command after cloning the repository:
```bash
python scripts/download_assets.py
```

This will download:
- Champion icons (emoji_assets/champions/)  
- Rank icons (emoji_assets/ranks/)
- Summoner spell icons (emoji_assets/spells/)

**Note:** You'll need these assets for the bot to display champion emojis properly in Discord. The download script will automatically fetch the latest assets from Riot's CDN.

## Troubleshooting

### Docker Issues

1. **Docker won't start**
   - Ensure virtualization is enabled in BIOS
   - Verify WSL 2 is installed and updated
   - Try running: `wsl --update`

2. **Container won't build**
   - Clear Docker cache: `docker system prune -a`
   - Ensure all files are in the correct locations
   - Check Docker logs for specific errors

3. **Container starts but bot doesn't respond**
   - Verify bot token is correct
   - Check if bot has proper permissions in Discord
   - Review logs for error messages

### Bot Issues

1. **Commands don't work or show as "not synced"**
   - Ensure bot has proper permissions and was invited with 'applications.commands' scope
   - Bot owner can run `/sync` command to manually sync slash commands
   - Commands sync automatically to the bot's guild on startup
   - For global sync across all servers, use `/sync global_sync:True`
   - Check bot logs for any sync errors during startup

2. **Riot API errors**
   - Verify API key is valid and not expired
   - Check rate limits
   - Ensure summoner name/tag are correct

3. **Database errors**
   - Check if data directory has proper permissions
   - Try stopping the container and starting it again
   - Verify database file exists in data directory

## Maintenance

1. **Updating the Bot**
```cmd
docker-compose down
git pull
docker-compose build --no-cache
docker-compose up -d
```

3. **Changing Configuration**
- Edit `config/config.json` directly
- Or stop the bot and delete config to trigger GUI on next start

## Support

If you encounter issues not covered in this guide:

1. Check the logs: `docker-compose logs -f`
2. Verify all prerequisites are properly installed
3. Ensure all tokens and API keys are valid
4. Try restarting Docker Desktop
5. Check Discord Developer Portal for bot status

## Security Notes

- Keep your bot token and API key secure
- Don't share your config.json file
- Use a dedicated Discord server for testing
- Keep Docker Desktop and WSL updated
- Monitor your Riot API usage

## Updates and Maintenance

The bot will need occasional updates:

1. Discord bot token rarely needs updating unless compromised

2. Keep Docker Desktop updated for security and performance

Remember to regularly check logs for any issues.
