import aiohttp
import asyncio
import logging
import os

logger = logging.getLogger("RBXStalker")

class RobloxAPI:
    def __init__(self):
        self.session = None
        self.cookie = os.getenv("ROBLOSECURITY")

    async def get_session(self):
        if self.session is None:
            headers = {}
            if self.cookie:
                headers["Cookie"] = f".ROBLOSECURITY={self.cookie}"
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def request(self, method, url, **kwargs):
        session = await self.get_session()
        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status == 429:
                    logger.warning(f"Rate Limit (429) at {url}. Skipping.")
                    return None
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"API Error at {url}: {e}")
        return None

    # --- USER DATA ---
    async def get_user_info(self, user_input):
        if str(user_input).isdigit():
            return await self.request("GET", f"https://users.roblox.com/v1/users/{user_input}")
        else:
            data = await self.request("POST", "https://users.roblox.com/v1/usernames/users", 
                                    json={"usernames": [user_input], "excludeBannedUsers": True})
            return data["data"][0] if data and data.get("data") else None

    async def get_presences(self, user_ids):
        return await self.request("POST", "https://presence.roblox.com/v1/presence/users", json={"userIds": user_ids})

    async def get_friends(self, user_id):
        return await self.request("GET", f"https://friends.roblox.com/v1/users/{user_id}/friends")

    async def get_avatar(self, user_id):
        data = await self.request("GET", f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false")
        return data["data"][0].get("imageUrl") if data and data.get("data") else None

    # --- NEW METADATA ---
    async def get_socials(self, user_id):
        return await self.request("GET", f"https://users.roblox.com/v1/users/{user_id}/social-links")

    async def get_user_groups(self, user_id):
        return await self.request("GET", f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")

    # --- GAME INFO ---
    async def get_server_info(self, place_id, game_id):
        data = await self.request("GET", f"https://games.roblox.com/v1/games/{place_id}/servers/Public?serverId={game_id}")
        if data and "data" in data and len(data["data"]) > 0:
            s = data["data"][0]
            return {
                "playing": s.get("playing", "?"),
                "maxPlayers": s.get("maxPlayers", "?"),
                "ping": s.get("ping", "Unknown"),
                "fps": s.get("fps", "Unknown"),
                "id": s.get("id")
            }
        return None