import discord
from discord.ext import commands
import os
import io
from database import get_server_configs
import logging

LOG_FILE = "logs/rbxstalker.log"

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.console_logger = logging.getLogger("RBXStalker")
        
    def build_embed(self, title, description, color=0x3498db):
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text="RBXStalker V2 Logs")
        return embed

    @commands.Cog.listener()
    async def on_rbx_log(self, guild_id, content, color=None):
        configs = await get_server_configs()
        
        # Try to find the guild name for context
        guild_name = "Global System"
        if guild_id:
            guild = self.bot.get_guild(guild_id)
            if guild:
                guild_name = guild.name
            else:
                guild_name = f"Guild ID: {guild_id}"

        for conf in configs:
            if guild_id and conf['guild_id'] != guild_id:
                continue
            
            if conf['log_channel_id']:
                channel = self.bot.get_channel(conf['log_channel_id'])
                if channel:
                    try:
                        # Check length limit (Discord limit is 4096)
                        if len(content) > 4000:
                            # Too long for embed -> Send as file
                            file_data = io.BytesIO(content.encode('utf-8'))
                            file = discord.File(file_data, filename="log_details.txt")
                            
                            embed = discord.Embed(
                                description=f"\u26A0 **Log content too long for embed.** See attached file.\n\n**Source:** {guild_name}",
                                color=color or 0xFFA500
                            )
                            embed.set_footer(text=f"System Log • {discord.utils.utcnow().strftime('%H:%M:%S')}")
                            await channel.send(embed=embed, file=file)
                        else:
                            # Normal Embed
                            embed = discord.Embed(description=content, color=color or 0x2b2d31)
                            embed.set_footer(text=f"Source: {guild_name} • {discord.utils.utcnow().strftime('%H:%M:%S')}")
                            await channel.send(embed=embed)
                            
                    except discord.Forbidden:
                        self.console_logger.warning(f"Could not send log to channel {conf['log_channel_id']}")
                    except Exception as e:
                        self.console_logger.error(f"Error sending log embed: {e}")

    @commands.hybrid_group(name="showlogs", fallback="latest")
    @commands.has_permissions(administrator=True)
    async def showlogs(self, ctx):
        """Displays the last 15 lines of the log."""
        if not os.path.exists(LOG_FILE):
            return await ctx.send(embed=self.build_embed("Error", "No log file found.", 0xFF0000))
        
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                last_lines = lines[-15:]
                text = "".join(last_lines)
            
            if not text.strip():
                return await ctx.send(embed=self.build_embed("Logs", "Log file is empty.", 0xFFFF00))
            
            # Send as code block inside embed
            # Truncate if somehow the last 15 lines are massive
            if len(text) > 1900:
                text = text[-1900:] + "\n... (truncated)"
                
            await ctx.send(embed=self.build_embed("Recent Logs", f"```ini\n{text}\n```"))
        except Exception as e:
            await ctx.send(embed=self.build_embed("Error", f"Error reading logs: {e}", 0xFF0000))

    @showlogs.command(name="save", description="Uploads the full log file.")
    @commands.has_permissions(administrator=True)
    async def save_logs(self, ctx):
        if os.path.exists(LOG_FILE):
            await ctx.send(content="📄 **Full System Log:**", file=discord.File(LOG_FILE))
        else:
            await ctx.send(embed=self.build_embed("Error", "No log file to save.", 0xFF0000))

    @commands.hybrid_command(name="clearlogs", description="Wipes the local log file.")
    @commands.has_permissions(administrator=True)
    async def clearlogs(self, ctx):
        with open(LOG_FILE, "w") as f:
            f.write("")
        await ctx.send(embed=self.build_embed("Logs Cleared", "🧹 Local log file has been wiped.", 0x00FF00))
        self.bot.dispatch("rbx_log", ctx.guild.id, f"🧹 Log file cleared by {ctx.author.mention}", 0xFFA500)

async def setup(bot):
    await bot.add_cog(Logs(bot))