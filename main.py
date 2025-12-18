import sys
import os
import asyncio
import traceback
from dotenv import load_dotenv
from colorama import Fore, Style, init

# 1. SETUP
load_dotenv()

# We check for token inside the function now, to allow GUI to create .env first
import discord
from discord.ext import commands
from database import init_db, get_server_prefix, get_server_configs
from utils.logger import setup_logger

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
            except Exception as e:
                self.logger.error(f"Failed {ext}: {e}")

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user}")
        print(f"Bot Connected: {self.user}")

# --- THREADING ENTRY POINT ---
def run_bot():
    # Reload environment to ensure we get the token if it was just saved
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    
    if not TOKEN:
        print("Waiting for Token...")
        return

    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        bot = RBXStalkerBot()
        asyncio.run(bot.start(TOKEN))
    except Exception as e:
        traceback.print_exc()

def start_bot_thread():
    """Called by GUI to start bot in background"""
    run_bot()

if __name__ == "__main__":
    run_bot()