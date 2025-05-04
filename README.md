# SourceStalker Setup Guide for Windows

## Prerequisites

Before beginning the setup process, you'll need to install the following software:

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

## Step-by-Step Setup Guide

### 1. Install Docker Desktop

1. Download Docker Desktop from the official website
2. Run the installer
3. Follow the installation prompts
4. When prompted, enable WSL 2 installation
5. Restart your computer when installation is complete
6. Start Docker Desktop and ensure it's running properly (look for the Docker icon in your system tray)

### 2. Create a Discord Bot

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

### 3. Get a Riot Games API Key

1. Go to https://developer.riotgames.com/
2. Sign in with your Riot Developer account
3. Register a new application
4. Wait for application approval
5. Save the application API key for later use

### 4. Set Up the Project

1. Open Command Prompt as Administrator
2. Create a directory for the project:
```cmd
mkdir C:\SourceStalker
cd C:\SourceStalker
```

3. Clone the repository:
```cmd
git clone [repository-url] .
```

4. Create required directories:
```cmd
mkdir config
```

### 5. Configure the Bot

1. Start the container for the first time:
```cmd
docker-compose up
```

2. The configuration GUI will appear. Fill in:
   - Discord Bot Token (from step 2)
   - Discord Channel ID (Right-click the channel in Discord > Copy ID)
   - Riot API Key (from step 3)
   - Summoner Name and Tag
   - Select your region
   - Leave other settings at default unless you need to change them

3. Click "Save Configuration", then you can close the window. The bot is now running.

### 6. Running the Bot

After initial setup, you can:

- Start the bot:
```cmd
docker-compose up -d
```

- Stop the bot:
```cmd
docker-compose down
```

- View logs:
```cmd
docker-compose logs -f
```

## Available Commands

Once the bot is running, you can use these commands in your Discord server:

- `/stalkmatches` - View recent match history
- `/livegame` - Check current game information
- `/stalkrank` - View rank and progression

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

1. **Commands don't work**
   - Ensure bot has proper permissions
   - Try re-inviting the bot using the OAuth2 URL
   - Verify slash commands are registered (may take up to an hour)

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
