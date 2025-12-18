import discord
from discord.ext import commands
import sys
import os
import aiosqlite
from database import (add_user_to_track, remove_user_track, 
                      get_all_tracked_users, set_server_config, 
                      update_user_field, update_history_field, 
                      set_server_prefix, get_server_prefix, DB_NAME)
from utils.roblox_api import RobloxAPI

class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = RobloxAPI()

    def build_embed(self, title, description, color=0x3498db):
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text="RBXStalker V2")
        return embed

    @commands.hybrid_command(description="Restarts the bot system.")
    @commands.has_permissions(administrator=True)
    async def restart(self, ctx):
        await ctx.send(embed=self.build_embed("System Restart", "🔄 Restarting...", 0xFFA500))
        os.execv(sys.executable, ['python'] + sys.argv)

    @commands.hybrid_command(description="Syncs slash commands.")
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx):
        msg = await ctx.send(embed=self.build_embed("Syncing", "Clearing and re-syncing commands..."))
        self.bot.tree.clear_commands(guild=ctx.guild)
        self.bot.tree.copy_global_to(guild=ctx.guild)
        await self.bot.tree.sync(guild=ctx.guild)
        await msg.edit(embed=self.build_embed("Sync Complete", f"✅ Synced to **{ctx.guild.name}**.", 0x00FF00))

    @commands.hybrid_command(name="setprefix", description="Change command prefix.")
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx, new_prefix: str):
        if len(new_prefix) > 5: return await ctx.send("Prefix too long.")
        await set_server_prefix(ctx.guild.id, new_prefix)
        await ctx.send(embed=self.build_embed("Configuration", f"✅ Prefix set to `{new_prefix}`", 0x00FF00))

    @commands.hybrid_command(name="setchannel", description="Set event/log channels.")
    @commands.has_permissions(administrator=True)
    @discord.app_commands.describe(channel_type="Type 'events' or 'logs'")
    async def setchannel(self, ctx, channel_type: str):
        channel_type = channel_type.lower()
        if channel_type == "events":
            await set_server_config(ctx.guild.id, "event_channel_id", ctx.channel.id)
            await ctx.send(embed=self.build_embed("Configuration", f"✅ **Events** -> {ctx.channel.mention}", 0x00FF00))
        elif channel_type == "logs":
            await set_server_config(ctx.guild.id, "log_channel_id", ctx.channel.id)
            await ctx.send(embed=self.build_embed("Configuration", f"✅ **Logs** -> {ctx.channel.mention}", 0x00FF00))
        else:
            await ctx.send(embed=self.build_embed("Error", "Use `events` or `logs`", 0xFF0000))

    @commands.hybrid_command(name="setwebhook", description="Set a raw webhook for events.")
    @commands.has_permissions(administrator=True)
    async def setwebhook(self, ctx, url: str):
        if not url.startswith("http"): return await ctx.send("Invalid URL.")
        await set_server_config(ctx.guild.id, "event_webhook_url", url)
        await ctx.send(embed=self.build_embed("Configuration", "✅ Webhook configured.", 0x00FF00))

    @commands.hybrid_command(name="priority", description="Toggle High Priority (10s checks) for a user.")
    @commands.has_permissions(administrator=True)
    async def priority(self, ctx, username: str):
        user_data = await self.api.get_user_info(username)
        if not user_data: return await ctx.send("User not found.")
        
        uid = user_data['id']
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("SELECT priority FROM tracked_users WHERE user_id = ?", (uid,))
            row = await cur.fetchone()
            if not row: return await ctx.send("User not being tracked.")
            
            new_prio = 1 if row[0] == 0 else 0
            await db.execute("UPDATE tracked_users SET priority = ? WHERE user_id = ?", (new_prio, uid))
            await db.commit()
        
        status = "HIGH (10s)" if new_prio else "NORMAL (30s)"
        await ctx.send(embed=self.build_embed("Priority Updated", f"⚡ **{user_data['name']}** is now **{status}** priority.", 0xFFFF00))

    @commands.hybrid_group(name="list", fallback="show")
    async def list_group(self, ctx):
        users = await get_all_tracked_users()
        if not users: return await ctx.send("No users tracked.")
        msg = ""
        for u in users:
            prio = "⚡" if u['priority'] else ""
            msg += f"• {prio} **{u['display_name']}** (@{u['username']}) - {u['ping_mode']}\n"
        await ctx.send(embed=self.build_embed("Tracked Users", msg))

    @list_group.command(name="add", description="Add user(s) to track.")
    @commands.has_permissions(administrator=True)
    async def add_user(self, ctx, identifier: str, mode: str = "ping"):
        identifiers = [x.strip() for x in identifier.split(',')]
        count = 0
        for ident in identifiers:
            if not ident: continue
            user_data = await self.api.get_user_info(ident)
            if user_data:
                await add_user_to_track(user_data['id'], user_data['name'], user_data['displayName'], mode)
                await update_user_field(user_data['id'], "last_avatar_url", await self.api.get_avatar(user_data['id']))
                count += 1
        await ctx.send(embed=self.build_embed("Success", f"✅ Added {count} users.", 0x00FF00))

    @list_group.command(name="remove", description="Remove a user.")
    @commands.has_permissions(administrator=True)
    async def remove_user(self, ctx, identifier: str):
        user_data = await self.api.get_user_info(identifier)
        if user_data:
            await remove_user_track(user_data['id'])
            await ctx.send(embed=self.build_embed("Success", f"🗑️ Removed {user_data['name']}.", 0x00FF00))
        else:
            await ctx.send(embed=self.build_embed("Error", "User not found.", 0xFF0000))

    @commands.hybrid_command(name="help", description="Show help menu.")
    async def help(self, ctx):
        p = await get_server_prefix(self.bot, ctx.message)
        embed = discord.Embed(title="RBXStalker V2 Help", color=0x3498db)
        embed.add_field(name="👥 Tracking", value=f"`{p}list add <user>`\n`{p}list remove <user>`\n`{p}priority <user>`", inline=False)
        embed.add_field(name="⚙️ Config", value=f"`{p}setchannel events/logs`\n`{p}setwebhook <url>`\n`{p}setprefix <char>`", inline=False)
        embed.add_field(name="🛠️ System", value=f"`{p}showlogs`\n`{p}clearlogs`\n`{p}restart`", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Management(bot))