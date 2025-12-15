import discord
from discord.ext import tasks, commands
from discord.ui import View, Button
import json
import asyncio
from utils.roblox_api import RobloxAPI
from database import (get_all_tracked_users, update_user_field, 
                      get_server_configs, get_user_history, update_history_field,
                      update_presence_state)

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
        self.presence_loop.start()
        self.metadata_loop.start()

    def cog_unload(self):
        self.presence_loop.cancel()
        self.metadata_loop.cancel()

    async def dispatch_event(self, title, description, color, username, display_name, thumbnail=None, ping=False, user_ping_mode="ping", 
                             profile_url=None, game_url=None, server_id=None):
        configs = await get_server_configs()
        
        embed = discord.Embed(description=description, color=color)
        embed.set_author(name=f"{display_name} (@{username})", icon_url=thumbnail, url=profile_url)
        if thumbnail: embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text="RBXStalker V2 • Real-Time Tracking")
        
        view = TrackingView(profile_url, game_url, server_id)

        for conf in configs:
            channel_id = conf['event_channel_id']
            if not channel_id: continue
            
            channel = self.bot.get_channel(channel_id)
            if channel:
                content = "@everyone" if (ping and user_ping_mode == "ping") else ""
                try:
                    await channel.send(content=content, embed=embed, view=view)
                except discord.Forbidden: pass
        
        self.bot.dispatch("rbx_log", None, f"📨 Event Sent: **{title}**", color)

    async def verify_change(self, user_id, new_status_type):
        await asyncio.sleep(6)
        resp = await self.api.get_presences([user_id])
        if resp and "userPresences" in resp:
            latest = resp['userPresences'][0]
            if latest['userPresenceType'] == new_status_type:
                return latest
        return None

    @tasks.loop(seconds=30)
    async def presence_loop(self):
        try:
            users = await get_all_tracked_users()
            if not users: return

            user_ids = [u['user_id'] for u in users]
            chunks = [user_ids[i:i + 50] for i in range(0, len(user_ids), 50)]

            for chunk in chunks:
                resp = await self.api.get_presences(chunk)
                if not resp or "userPresences" not in resp: continue

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
                        verified = await self.verify_change(uid, new_type)
                        if not verified: continue
                        
                        p_data = verified
                        new_type = p_data['userPresenceType']
                        new_place_id = p_data.get("placeId")
                        new_game_id = p_data.get("gameId")

                        is_swapped = (new_type == 2 and last_type == 2 and (new_place_id != last_place_id or new_game_id != last_game_id))
                        if new_type == last_type and not is_swapped: continue 

                        username = local_user['username']
                        display = local_user['display_name']
                        thumb = local_user['last_avatar_url']
                        prof_url = f"https://www.roblox.com/users/{uid}/profile"
                        
                        if new_type == 1:
                            await self.dispatch_event(f"{display} is Online", f"Is now **Online**.", 0x4287f5, username, display, thumb, True, local_user['ping_mode'], profile_url=prof_url)
                        
                        elif new_type == 2:
                            game_name = p_data.get("lastLocation", "a Game") or "a Game"
                            desc_lines = []
                            join_url = None
                            server_id_display = None

                            # CASE 1: Valid Game ID (Joinable)
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
                            
                            # CASE 2: Missing Game ID (Joins Off / Private / Mobile)
                            else:
                                desc_lines.append(f"🚫 **{display} does not have joins on.**")
                                desc_lines.append(f"*(Server ID is hidden by privacy settings or platform)*")

                            await self.dispatch_event(f"{display} started Playing", "\n".join(desc_lines), 0x37B06D, username, display, thumb, True, local_user['ping_mode'], profile_url=prof_url, game_url=join_url, server_id=server_id_display)
                        
                        elif new_type == 3:
                            await self.dispatch_event(f"{display} is in Studio", f"Is building in **Roblox Studio**.", 0xEE8700, username, display, thumb, True, local_user['ping_mode'], profile_url=prof_url)
                        
                        elif new_type == 0:
                            await self.dispatch_event(f"{display} went Offline", f"Went **Offline**.", 0x808080, username, display, thumb, False, local_user['ping_mode'], profile_url=prof_url)

                        await update_presence_state(uid, new_type, new_place_id, new_game_id)

        except Exception as e:
            self.bot.logger.error(f"Presence loop error: {e}")

    @tasks.loop(minutes=5)
    async def metadata_loop(self):
        try:
            users = await get_all_tracked_users()
            for user in users:
                uid = user['user_id']
                history = await get_user_history(uid)
                if not history: continue
                
                prof_url = f"https://www.roblox.com/users/{uid}/profile"
                username = user['username']
                display = user['display_name']
                thumb = user['last_avatar_url']

                new_avatar = await self.api.get_avatar(uid)
                if new_avatar and new_avatar != user['last_avatar_url']:
                    if user['last_avatar_url']:
                        await self.dispatch_event(f"Avatar Changed", f"Updated their avatar.", 0xFFFF00, username, display, new_avatar, profile_url=prof_url)
                    await update_user_field(uid, "last_avatar_url", new_avatar)
                    await asyncio.sleep(1)

                friends_resp = await self.api.get_friends(uid)
                if friends_resp and 'data' in friends_resp:
                    current = [f['id'] for f in friends_resp['data']]
                    old = json.loads(history['friend_ids'])
                    if not old and current:
                        await update_history_field(uid, "friend_ids", current)
                        continue
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
                await asyncio.sleep(2)
        except Exception as e:
            self.bot.logger.error(f"Meta loop error: {e}")

    @presence_loop.before_loop
    async def before_tracking(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Tracking(bot))