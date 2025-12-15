import discord
from discord.ext import commands
import sys
import os
import uuid
from database import (add_user_to_track, remove_user_track, 
                      get_all_tracked_users, set_server_config, 
                      update_user_field, update_history_field, get_server_configs,
                      set_server_prefix, get_server_prefix)
from utils.roblox_api import RobloxAPI

FAKE_PERM_ROLE_ID = 1441573007205072927

class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = RobloxAPI()

    def build_embed(self, title, description, color=0x3498db):
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text="RBXStalker V2")
        return embed

    def has_fake_perms():
        async def predicate(ctx):
            if ctx.author.guild_permissions.administrator: return True
            role = discord.utils.get(ctx.author.roles, id=FAKE_PERM_ROLE_ID)
            return role is not None
        return commands.check(predicate)

    @commands.hybrid_command(description="Restarts the bot system (Admin Only).")
    @commands.has_permissions(administrator=True)
    async def restart(self, ctx):
        """Restarts the bot system (Admin Only)."""
        await ctx.send(embed=self.build_embed("System Restart", "🔄 Restarting system...", 0xFFA500))
        self.bot.dispatch("rbx_log", ctx.guild.id, f"System restarted by {ctx.author.mention}", 0xFFA500)
        os.execv(sys.executable, ['python'] + sys.argv)

    @commands.hybrid_command(description="Syncs slash commands to the CURRENT server instantly.")
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx):
        """Syncs slash commands to this server."""
        msg = await ctx.send(embed=self.build_embed("Syncing", "Clearing and re-syncing commands..."))
        
        # 1. Clear existing commands to prevent duplicates
        self.bot.tree.clear_commands(guild=ctx.guild)
        
        # 2. Copy global commands to guild
        self.bot.tree.copy_global_to(guild=ctx.guild)
        
        # 3. Sync
        await self.bot.tree.sync(guild=ctx.guild)
        
        await msg.edit(embed=self.build_embed("Sync Complete", f"✅ Slash commands synced to **{ctx.guild.name}**! Duplicates removed.", 0x00FF00))

    @commands.hybrid_command(name="setprefix", description="Change the bot prefix for this server.")
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx, new_prefix: str):
        if len(new_prefix) > 5: 
            return await ctx.send(embed=self.build_embed("Error", "Prefix too long (max 5 chars).", 0xFF0000))
        
        await set_server_prefix(ctx.guild.id, new_prefix)
        await ctx.send(embed=self.build_embed("Configuration", f"✅ Prefix updated to `{new_prefix}`. Run `/help` to see changes.", 0x00FF00))
        self.bot.dispatch("rbx_log", ctx.guild.id, f"Prefix changed to `{new_prefix}` by {ctx.author.mention}", 0x00FFFF)

    @commands.hybrid_command(name="setchannel", description="Set the channel for events or logs.")
    @commands.has_permissions(administrator=True)
    @discord.app_commands.describe(channel_type="Type 'events' or 'logs'")
    async def setchannel(self, ctx, channel_type: str):
        channel_type = channel_type.lower()
        if channel_type == "events":
            await set_server_config(ctx.guild.id, "event_channel_id", ctx.channel.id)
            await ctx.send(embed=self.build_embed("Configuration", f"✅ **Events** will be sent to {ctx.channel.mention}", 0x00FF00))
            self.bot.dispatch("rbx_log", ctx.guild.id, f"Event Channel set to {ctx.channel.mention}", 0x00FFFF)
        elif channel_type == "logs":
            await set_server_config(ctx.guild.id, "log_channel_id", ctx.channel.id)
            await ctx.send(embed=self.build_embed("Configuration", f"✅ **System Logs** will be sent to {ctx.channel.mention}", 0x00FF00))
            self.bot.dispatch("rbx_log", ctx.guild.id, f"Log Channel configured by {ctx.author.mention}", 0x00FF00)
        else:
            await ctx.send(embed=self.build_embed("Error", "Usage: `setchannel events` or `setchannel logs`", 0xFF0000))

    @commands.hybrid_group(name="list", fallback="show")
    async def list_group(self, ctx):
        """Manage the tracking list."""
        users = await get_all_tracked_users()
        if not users: 
            return await ctx.send(embed=self.build_embed("Tracked Users", "No users currently tracked.", 0xFFFF00))
        
        msg = ""
        for u in users:
            msg += f"• {u['display_name']} (@{u['username']}) [ID: {u['user_id']}] - {u['ping_mode']}\n"
        
        if len(msg) > 3800: msg = msg[:3800] + "... (list truncated)"
        await ctx.send(embed=self.build_embed("Tracked Users", msg))

    @list_group.command(name="add", description="Add a user to the tracking list.")
    @commands.has_permissions(administrator=True)
    @discord.app_commands.describe(identifier="Username or ID (comma separated)", mode="ping or noping")
    async def add_user(self, ctx, identifier: str, mode: str = "ping"):
        mode = mode.lower()
        if mode not in ['ping', 'noping']: 
            return await ctx.send(embed=self.build_embed("Error", "Mode must be 'ping' or 'noping'.", 0xFF0000))
        
        identifiers = [x.strip() for x in identifier.split(',')]
        status_msg = await ctx.send(embed=self.build_embed("Processing", f"Processing {len(identifiers)} users..."))
        
        success_count = 0
        for ident in identifiers:
            if not ident: continue
            user_data = await self.api.get_user_info(ident)
            if not user_data:
                continue

            uid = user_data['id']
            username = user_data.get('name')
            display = user_data.get('displayName', username)

            await add_user_to_track(uid, username, display, mode)
            
            avatar = await self.api.get_avatar(uid)
            if avatar: await update_user_field(uid, "last_avatar_url", avatar)
            
            friends = await self.api.get_friends(uid)
            if friends and 'data' in friends:
                fids = [f['id'] for f in friends['data']]
                await update_history_field(uid, "friend_ids", fids)
            
            success_count += 1
            self.bot.dispatch("rbx_log", ctx.guild.id, f"User **{display}** added by {ctx.author.mention}", 0x00FF00)

        await status_msg.edit(embed=self.build_embed("Success", f"✅ Added {success_count} users to tracking ({mode}).", 0x00FF00))

    @list_group.command(name="remove", description="Remove a user from tracking.")
    @commands.has_permissions(administrator=True)
    async def remove_user(self, ctx, identifier: str):
        user_data = await self.api.get_user_info(identifier)
        if user_data:
            await remove_user_track(user_data['id'])
            await ctx.send(embed=self.build_embed("Success", f"🗑️ Removed **{user_data.get('name')}**.", 0x00FF00))
            self.bot.dispatch("rbx_log", ctx.guild.id, f"User **{user_data.get('name')}** removed by {ctx.author.mention}", 0xFF0000)
        elif identifier.isdigit():
            await remove_user_track(int(identifier))
            await ctx.send(embed=self.build_embed("Success", f"🗑️ Removed ID {identifier}.", 0x00FF00))
        else:
            await ctx.send(embed=self.build_embed("Error", "❌ User not found.", 0xFF0000))

    @commands.hybrid_group(name="fake", fallback="help")
    @has_fake_perms()
    async def fake(self, ctx):
        """Admin/Restricted testing commands."""
        await ctx.send(embed=self.build_embed("Fake Events", f"Usage:\n`fake online <user>`\n`fake offline <user>`\n`fake game <user>`"))

    @fake.command(name="online", description="Simulate online event")
    @has_fake_perms()
    async def fake_online(self, ctx, username: str):
        track = self.bot.get_cog("Tracking")
        if not track: return
        udata = await self.api.get_user_info(username)
        if not udata: return await ctx.send(embed=self.build_embed("Error", "User not found.", 0xFF0000))
        avatar = await self.api.get_avatar(udata['id'])
        prof = f"https://www.roblox.com/users/{udata['id']}/profile"
        await track.dispatch_event(f"{udata['displayName']} is Online", f"Is now **Online**.", 0x4287f5, udata['name'], udata['displayName'], avatar, True, "ping", profile_url=prof)
        await ctx.send(embed=self.build_embed("Success", "✅ Fake Online event sent.", 0x00FF00), ephemeral=True)

    @fake.command(name="offline", description="Simulate offline event")
    @has_fake_perms()
    async def fake_offline(self, ctx, username: str):
        track = self.bot.get_cog("Tracking")
        if not track: return
        udata = await self.api.get_user_info(username)
        if not udata: return await ctx.send(embed=self.build_embed("Error", "User not found.", 0xFF0000))
        avatar = await self.api.get_avatar(udata['id'])
        prof = f"https://www.roblox.com/users/{udata['id']}/profile"
        await track.dispatch_event(f"{udata['displayName']} went Offline", f"Went **Offline**.", 0x808080, udata['name'], udata['displayName'], avatar, False, "ping", profile_url=prof)
        await ctx.send(embed=self.build_embed("Success", "✅ Fake Offline event sent.", 0x00FF00), ephemeral=True)

    @fake.command(name="game", description="Simulate game event")
    @has_fake_perms()
    async def fake_game(self, ctx, username: str):
        track = self.bot.get_cog("Tracking")
        if not track: return
        udata = await self.api.get_user_info(username)
        if not udata: return await ctx.send(embed=self.build_embed("Error", "User not found.", 0xFF0000))
        avatar = await self.api.get_avatar(udata['id'])
        prof = f"https://www.roblox.com/users/{udata['id']}/profile"
        
        fake_server_id = str(uuid.uuid4())
        fake_place_id = 4924922222 
        
        await track.dispatch_event(
            f"{udata['displayName']} started Playing", 
            f"Playing: [**Brookhaven RP**](https://www.roblox.com/games/{fake_place_id})\n\n**Server Stats:**\n👥 **Players:** 12/20\n📶 **Ping:** 90ms\n🖥️ **FPS:** 60\n🆔 **Server ID:** `{fake_server_id}`", 
            0x37B06D, udata['name'], udata['displayName'], avatar, True, "ping", 
            profile_url=prof,
            game_url=f"https://www.roblox.com/games/start?placeId={fake_place_id}&launchData={fake_server_id}",
            server_id=fake_server_id
        )
        await ctx.send(embed=self.build_embed("Success", "✅ Fake Game event sent.", 0x00FF00), ephemeral=True)

    @commands.hybrid_command(name="mancheck", description="Manually check status of a user.")
    @commands.has_permissions(administrator=True)
    async def mancheck(self, ctx, username: str):
        """Manually trigger a check for a user."""
        track = self.bot.get_cog("Tracking")
        if not track: return await ctx.send(embed=self.build_embed("Error", "Tracking module not loaded.", 0xFF0000))

        user_data = await self.api.get_user_info(username)
        if not user_data: return await ctx.send(embed=self.build_embed("Error", "User not found.", 0xFF0000))
        
        uid = user_data['id']
        
        # Check current status
        presences = await self.api.get_presences([uid])
        if not presences or "userPresences" not in presences:
             return await ctx.send(embed=self.build_embed("Error", "Could not fetch presence.", 0xFF0000))
        
        p_data = presences['userPresences'][0]
        status_type = p_data['userPresenceType']
        
        status_map = {0: "Offline", 1: "Online", 2: "In Game", 3: "Studio"}
        status_text = status_map.get(status_type, "Unknown")
        
        desc = f"**Current Status:** {status_text} (Type: {status_type})"
        
        if status_type == 2:
            game_name = p_data.get("lastLocation", "Unknown Game")
            place_id = p_data.get("placeId")
            game_id = p_data.get("gameId")
            
            desc += f"\n**Game:** {game_name}"
            desc += f"\n**Place ID:** {place_id}"
            desc += f"\n**Game ID (Server):** {game_id if game_id else 'Hidden/None'}"
            
        await ctx.send(embed=self.build_embed(f"Manual Check: {user_data['displayName']}", desc, 0x00FF00))

    # --- DYNAMIC HELP MENU ---
    @commands.hybrid_command(name="help", description="Show the help menu.")
    async def help(self, ctx):
        real_prefix = await get_server_prefix(self.bot, ctx.message)
        p = real_prefix
        
        embed = discord.Embed(title="RBXStalker V2 Help", color=0x3498db)
        embed.set_footer(text=f"Current Prefix: {p}")

        embed.add_field(name="👥 Tracking", value=(f"`{p}list` - List tracked users\n`{p}list add` - Add user(s)\n`{p}list remove` - Remove user"), inline=False)
        embed.add_field(name="🛠️ System", value=(f"`{p}health` - Bot status\n`{p}features` - **Full Guide**\n`{p}showlogs` - View logs\n`{p}mancheck` - Manual User Check"), inline=False)

        if ctx.author.guild_permissions.administrator:
            embed.add_field(name="🛡️ Admin / Config", value=(f"`{p}setprefix` - Change prefix\n`{p}setchannel` - Set channels\n`{p}clearlogs` - Wipe logs\n`{p}sync` - Fix slash commands\n`{p}restart` - Reboot bot"), inline=False)
        
        is_admin = ctx.author.guild_permissions.administrator
        has_role = discord.utils.get(ctx.author.roles, id=FAKE_PERM_ROLE_ID) is not None
        
        if is_admin or has_role:
            embed.add_field(name="🧪 Testing", value=(f"`{p}fake online`\n`{p}fake offline`\n`{p}fake game`"), inline=False)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="features", description="Detailed overview of all features.")
    async def features(self, ctx):
        embed = discord.Embed(title="RBXStalker V2 Features", description="A comprehensive guide to what this bot can do.", color=0x9B59B6)
        embed.add_field(name="🕵️ Live Tracking", value=("• **Real-time Presence:** Detects Online, Offline, Studio, or Game status.\n• **Server Detection:** Fetches Exact Server via Profile Join Button logic.\n• **Joins Off Detection:** Distinctly warns if a user has joins disabled.\n• **Direct Join Link:** Generates one-click launch links."), inline=False)
        embed.add_field(name="📋 Metadata", value=("• **Avatar Updates:** Notifies on avatar changes.\n• **Friend List:** Tracks friend adds/removes."), inline=False)
        embed.add_field(name="⚙️ Config", value=("• **Hybrid Commands:** Use `/` or Prefix.\n• **Custom Prefix:** Change via `setprefix`.\n• **Logging:** Dedicated log channels."), inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(description="View bot health status.")
    async def health(self, ctx):
        await ctx.send(embed=self.build_embed("System Health", f"🟢 **System Online**\n📡 Ping: `{round(self.bot.latency * 1000)}ms`", 0x00FF00))

async def setup(bot):
    await bot.add_cog(Management(bot))