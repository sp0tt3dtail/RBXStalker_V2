import discord
from discord.ext import tasks, commands
from discord.ui import View, Button
import json
import asyncio
import aiohttp
from utils.roblox_api import RobloxAPI
from database import *

class TrackingView(View):
    def __init__(self, profile_url, game_url=None, server_id=None):
        super().__init__(timeout=None)
        self.add_item(Button(label="👤 Profile", url=profile_url, style=discord.ButtonStyle.link))
        if game_url:
            self.add_item(Button(label="🚀 Join Game", url=game_url, style=discord.ButtonStyle.link))
        if server_id:
            self.add_item(CopyIDButton(server_id))

class CopyIDButton(Button):
    def __init__(self, server_id):
        self.server_id = str(server_id)
        super().__init__(label="🆔 Copy Server ID", style=discord.ButtonStyle.gray, custom_id=f"copy_{server_id}")
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"**Server ID:**\n```\n{self.server_id}\n```", ephemeral=True)

class Tracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = RobloxAPI()
        self.priority_loop.start()
        self.standard_loop.start()
        self.metadata_loop.start()

    def cog_unload(self):
        self.priority_loop.cancel()
        self.standard_loop.cancel()
        self.metadata_loop.cancel()

    async def send_webhook(self, url, embed):
        if not url: return
        async with aiohttp.ClientSession() as session:
            try:
                webhook_data = {
                    "embeds": [embed.to_dict()],
                    "username": "RBXStalker Event",
                    "avatar_url": self.bot.user.avatar.url if self.bot.user.avatar else None
                }
                await session.post(url, json=webhook_data)
            except:
                pass

    async def dispatch_event(self, title, description, color, username, display, thumb=None, ping=False, ping_mode="ping", 
                             profile_url=None, game_url=None, server_id=None):
        configs = await get_server_configs()
        embed = discord.Embed(description=description, color=color)
        embed.set_author(name=f"{display} (@{username})", icon_url=thumb, url=profile_url)
        if thumb: embed.set_thumbnail(url=thumb)
        embed.set_footer(text="RBXStalker V2 • Real-Time Tracking")
        
        view = TrackingView(profile_url, game_url, server_id)

        for conf in configs:
            # 1. Discord Channel
            if conf['event_channel_id']:
                channel = self.bot.get_channel(conf['event_channel_id'])
                if channel:
                    content = "@everyone" if (ping and ping_mode == "ping") else ""
                    try:
                        await channel.send(content=content, embed=embed, view=view)
                    except discord.Forbidden: pass
            
            # 2. Webhook
            if conf['event_webhook_url']:
                await self.send_webhook(conf['event_webhook_url'], embed)
        
        self.bot.dispatch("rbx_log", None, f"📨 Event Sent: **{title}** ({display})", color)

    # --- MAIN TRACKING LOGIC ---
    async def process_presences(self, users):
        if not users: return
        user_ids = [u['user_id'] for u in users]
        resp = await self.api.get_presences(user_ids)
        if not resp or "userPresences" not in resp: return

        for p_data in resp['userPresences']:
            uid = p_data['userId']
            new_type = p_data['userPresenceType']
            local_user = next((u for u in users if u['user_id'] == uid), None)
            if not local_user: continue

            last_type = local_user['last_presence_type']
            new_place_id = p_data.get("placeId")
            new_game_id = p_data.get("gameId")
            last_place_id = local_user['last_place_id'] 
            last_game_id = local_user['last_game_id']

            game_swapped = (new_type == 2 and last_type == 2 and (new_place_id != last_place_id or new_game_id != last_game_id))

            if new_type != last_type or game_swapped:
                # Basic debouncing (sleep and check again)
                await asyncio.sleep(2)
                verify = await self.api.get_presences([uid])
                if not verify or "userPresences" not in verify: continue
                p_data = verify['userPresences'][0]
                if p_data['userPresenceType'] != new_type: continue

                username = local_user['username']
                display = local_user['display_name']
                thumb = local_user['last_avatar_url']
                prof_url = f"https://www.roblox.com/users/{uid}/profile"
                
                # ONLINE
                if new_type == 1:
                    await self.dispatch_event(f"{display} is Online", f"Is now **Online**.", 0x4287f5, username, display, thumb, True, local_user['ping_mode'], profile_url=prof_url)
                
                # IN GAME
                elif new_type == 2:
                    game_name = p_data.get("lastLocation", "a Game") or "a Game"
                    desc_lines = []
                    join_url = None
                    server_id_display = None

                    if new_place_id and new_game_id:
                        desc_lines.append(f"Playing: [**{game_name}**](https://www.roblox.com/games/{new_place_id})")
                        join_url = f"https://www.roblox.com/games/start?placeId={new_place_id}&launchData={new_game_id}"
                        server_id_display = new_game_id
                        
                        s_info = await self.api.get_server_info(new_place_id, new_game_id)
                        if s_info:
                            desc_lines.append(f"\n**Server Stats:**")
                            desc_lines.append(f"👥 **Players:** {s_info['playing']}/{s_info['maxPlayers']}")
                            desc_lines.append(f"📶 **Ping:** {s_info['ping']}ms")
                            desc_lines.append(f"🖥️ **FPS:** {s_info['fps']}")
                            desc_lines.append(f"🆔 **Server ID:** `{s_info['id']}`")
                        else:
                            desc_lines.append("\n⚠️ *Could not fetch server stats (Private?)*")
                            desc_lines.append(f"🆔 **Server ID:** `{new_game_id}`")
                    else:
                        desc_lines.append(f"🚫 **{display} does not have joins on.**")
                        desc_lines.append(f"*(Server ID is hidden by privacy settings)*")

                    await self.dispatch_event(f"{display} started Playing", "\n".join(desc_lines), 0x37B06D, username, display, thumb, True, local_user['ping_mode'], profile_url=prof_url, game_url=join_url, server_id=server_id_display)
                
                # STUDIO
                elif new_type == 3:
                    await self.dispatch_event(f"{display} is in Studio", f"Is building in **Roblox Studio**.", 0xEE8700, username, display, thumb, True, local_user['ping_mode'], profile_url=prof_url)
                
                # OFFLINE
                elif new_type == 0:
                    await self.dispatch_event(f"{display} went Offline", f"Went **Offline**.", 0x808080, username, display, thumb, False, local_user['ping_mode'], profile_url=prof_url)

                await update_presence_state(uid, new_type, new_place_id, new_game_id)

    # --- LOOPS ---
    @tasks.loop(seconds=10)
    async def priority_loop(self):
        """Checks Priority Users (Priority=1)."""
        all_users = await get_all_tracked_users()
        prio_users = [u for u in all_users if u['priority'] == 1]
        await self.process_presences(prio_users)

    @tasks.loop(seconds=35)
    async def standard_loop(self):
        """Checks Standard Users (Priority=0)."""
        all_users = await get_all_tracked_users()
        norm_users = [u for u in all_users if u['priority'] == 0]
        chunks = [norm_users[i:i + 50] for i in range(0, len(norm_users), 50)]
        for chunk in chunks:
            await self.process_presences(chunk)
            await asyncio.sleep(1)

    @tasks.loop(minutes=10)
    async def metadata_loop(self):
        """Checks Friends, Groups, and Avatar."""
        users = await get_all_tracked_users()
        for user in users:
            uid = user['user_id']
            history = await get_user_history(uid)
            if not history: continue
            
            prof_url = f"https://www.roblox.com/users/{uid}/profile"
            username = user['username']
            display = user['display_name']
            
            # 1. Avatar
            new_avatar = await self.api.get_avatar(uid)
            if new_avatar and new_avatar != user['last_avatar_url']:
                if user['last_avatar_url']:
                    await self.dispatch_event(f"Avatar Changed", f"Updated their avatar.", 0xFFFF00, username, display, new_avatar, profile_url=prof_url)
                await update_user_field(uid, "last_avatar_url", new_avatar)

            # 2. Friends
            friends_resp = await self.api.get_friends(uid)
            if friends_resp and 'data' in friends_resp:
                current = [f['id'] for f in friends_resp['data']]
                old = json.loads(history['friend_ids'])
                if not old and current:
                    await update_history_field(uid, "friend_ids", current)
                else:
                    new = set(current) - set(old)
                    removed = set(old) - set(current)
                    if new or removed:
                        desc = ""
                        for fid in new:
                            fname = next((f['name'] for f in friends_resp['data'] if f['id'] == fid), str(fid))
                            desc += f"➕ Added: **{fname}**\n"
                        for fid in removed:
                            desc += f"➖ Removed ID: **{fid}**\n"
                        await self.dispatch_event(f"Friend List Updated", desc, 0x9B59B6, username, display, user['last_avatar_url'], profile_url=prof_url)
                        await update_history_field(uid, "friend_ids", current)
            
            # 3. Groups (New)
            groups = await self.api.get_user_groups(uid)
            if groups and 'data' in groups:
                current_groups = {str(g['group']['id']): g['role']['rank'] for g in groups['data']}
                old_groups = json.loads(history['group_data']) if history['group_data'] else {}
                
                # Check for rank changes or joins
                if old_groups:
                    for gid, rank in current_groups.items():
                        if gid in old_groups and old_groups[gid] != rank:
                            gname = next((g['group']['name'] for g in groups['data'] if str(g['group']['id']) == gid), "Group")
                            rname = next((g['role']['name'] for g in groups['data'] if str(g['group']['id']) == gid), "Rank")
                            await self.dispatch_event(f"Rank Change", f"Rank in **{gname}** changed to **{rname}**.", 0xFFA500, username, display, user['last_avatar_url'], profile_url=prof_url)
                
                await update_history_field(uid, "group_data", current_groups)

            await asyncio.sleep(2)

    @priority_loop.before_loop
    async def before_tracking(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Tracking(bot))