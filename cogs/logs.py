import discord
from discord.ext import commands
import os
import io
from database import get_server_configs, set_server_config
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
        
        guild_name = "System"
        if guild_id:
            g = self.bot.get_guild(guild_id)
            if g: guild_name = g.name

        for conf in configs:
            if guild_id and conf['guild_id'] != guild_id: continue
            if not conf['log_channel_id']: continue

            channel = self.bot.get_channel(conf['log_channel_id'])
            if channel:
                try:
                    # FIX: If log is massive, send as file instead of embed
                    if len(content) > 3800:
                        file_data = io.BytesIO(content.encode('utf-8'))
                        file = discord.File(file_data, filename="log_entry.txt")
                        
                        warning_embed = discord.Embed(
                            description=f"\u26A0 **Log too long for embed.** See attached file.\n**Source:** {guild_name}",
                            color=color or 0xFFA500
                        )
                        await channel.send(embed=warning_embed, file=file)
                    else:
                        embed = discord.Embed(description=content, color=color or 0x2b2d31)
                        embed.set_footer(text=f"Source: {guild_name} • {discord.utils.utcnow().strftime('%H:%M:%S')}")
                        await channel.send(embed=embed)
                        
                except Exception as e:
                    self.console_logger.error(f"Error sending log to Discord: {e}")

    @commands.hybrid_group(name="showlogs", fallback="latest")
    @commands.has_permissions(administrator=True)
    async def showlogs(self, ctx):
        """Displays the last 20 lines of the log."""
        if not os.path.exists(LOG_FILE):
            return await ctx.send(embed=self.build_embed("Error", "No log file found.", 0xFF0000))
        
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                text = "".join(lines[-20:])
            
            # Use file if even the last 20 lines are huge
            if len(text) > 1900:
                file_data = io.BytesIO(text.encode('utf-8'))
                file = discord.File(file_data, filename="recent_logs.txt")
                await ctx.send(content="**Recent Logs (Too long for embed):**", file=file)
            else:
                await ctx.send(embed=self.build_embed("Recent Logs", f"```ini\n{text}\n```"))
        except Exception as e:
            await ctx.send(embed=self.build_embed("Error", f"Read error: {e}", 0xFF0000))

    @showlogs.command(name="save", description="Uploads the full log file.")
    async def save_logs(self, ctx):
        if os.path.exists(LOG_FILE):
            await ctx.send(content="📄 **Full System Log:**", file=discord.File(LOG_FILE))
        else:
            await ctx.send(embed=self.build_embed("Error", "No log file.", 0xFF0000))

    @showlogs.command(name="stop", description="Disables startup log messages.")
    async def stop_logs(self, ctx):
        await set_server_config(ctx.guild.id, "show_logs_on_startup", 0)
        await ctx.send(embed=self.build_embed("Config", "🚫 Startup logs **Disabled** for this server.", 0xFFA500))

    @showlogs.command(name="start", description="Enables startup log messages.")
    async def start_logs(self, ctx):
        await set_server_config(ctx.guild.id, "show_logs_on_startup", 1)
        await ctx.send(embed=self.build_embed("Config", "✅ Startup logs **Enabled**.", 0x00FF00))

    @commands.hybrid_command(name="clearlogs", description="Wipes the local log file.")
    @commands.has_permissions(administrator=True)
    async def clearlogs(self, ctx):
        with open(LOG_FILE, "w") as f:
            f.write("")
        await ctx.send(embed=self.build_embed("Logs Cleared", "🧹 Local log file has been wiped.", 0x00FF00))
        self.bot.dispatch("rbx_log", ctx.guild.id, f"🧹 Log file cleared by {ctx.author.mention}", 0xFFA500)

async def setup(bot):
    await bot.add_cog(Logs(bot))