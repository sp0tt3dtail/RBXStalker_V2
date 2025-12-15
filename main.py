import sys
import subprocess
import os
import asyncio
import traceback
from colorama import Fore, Style, init

init(autoreset=True)

# 1. AUTO-INSTALLER
def install_dependencies():
    required = {
        "discord": "discord.py",
        "dotenv": "python-dotenv",
        "aiohttp": "aiohttp",
        "aiosqlite": "aiosqlite",
        "colorama": "colorama"
    }
    missing = []
    for import_name, install_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(install_name)
    
    if missing:
        print(f"Installing missing: {', '.join(missing)}...")
        for pkg in missing:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            except Exception as e:
                print(f"Failed to install {pkg}: {e}")
                sys.exit(1)

if __name__ == "__main__":
    install_dependencies()

# 2. IMPORTS
try:
    import discord
    from discord.ext import commands
    from dotenv import load_dotenv
    from database import init_db, get_server_prefix, get_server_configs, get_prefix_by_guild_id
    from utils.logger import setup_logger
except ImportError as e:
    print(f"Critical Import Error: {e}")
    sys.exit(1)

# 3. SETUP
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
COOKIE = os.getenv("ROBLOSECURITY")

intents = discord.Intents.default()
intents.message_content = True

class RBXStalkerBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=get_server_prefix, intents=intents, help_command=None)
        self.logger = setup_logger()

    async def setup_hook(self):
        await init_db()
        extensions = ['cogs.management', 'cogs.tracking', 'cogs.logs']
        for ext in extensions:
            try:
                await self.load_extension(ext)
                self.logger.info(f"Loaded {ext}")
            except Exception as e:
                self.logger.error(f"Failed {ext}: {e}")
                print(f"{Fore.RED}Failed to load {ext}{Style.RESET_ALL}")

    async def on_ready(self):
        print(f"\n{Fore.GREEN}>>> Logged in as {self.user} (ID: {self.user.id}){Style.RESET_ALL}")
        self.logger.info(f"Logged in as {self.user}")
        
        if not COOKIE:
            msg = f"\n{Fore.YELLOW}⚠️ WARNING: No ROBLOSECURITY cookie found in .env!{Style.RESET_ALL}\nRate limits will be strict and some game info may be hidden."
            print(msg)
            self.logger.warning("No ROBLOSECURITY cookie found.")

        # Send Startup Message to Log Channels (AS EMBED)
        configs = await get_server_configs()
        for conf in configs:
            if conf['log_channel_id']:
                try:
                    chan = self.get_channel(conf['log_channel_id'])
                    if chan:
                        # Fetch real prefix for this guild
                        prefix = await get_prefix_by_guild_id(conf['guild_id'])
                        
                        embed = discord.Embed(
                            title="System Online", 
                            description=f"🟢 **RBXStalker V2 has restarted.**\nType `{prefix}help` or `/help` for commands.", 
                            color=0x00FF00
                        )
                        embed.set_footer(text="System Ready")
                        await chan.send(embed=embed)
                except:
                    pass

        print(f"{Fore.CYAN}>>> System Ready. Type !help in Discord to begin.{Style.RESET_ALL}")

async def main():
    if not TOKEN:
        print(f"{Fore.RED}ERROR: DISCORD_TOKEN missing in .env{Style.RESET_ALL}")
        return

    bot = RBXStalkerBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal Error: {e}")
        traceback.print_exc()