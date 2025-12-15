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
        retries = 0
        max_retries = 3

        while retries < max_retries:
            try:
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 429:
                        wait_time = 2 ** retries 
                        logger.warning(f"Rate Limit (429) at {url}. Waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        retries += 1
                        continue
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
            except Exception as e:
                logger.error(f"Request Exception: {e}")
                return None
        return None

    # --- USER DATA ---
    async def get_user_info(self, user_input):
        if str(user_input).isdigit():
            url = f"https://users.roblox.com/v1/users/{user_input}"
            data = await self.request("GET", url)
            return data 
        else:
            url = "https://users.roblox.com/v1/usernames/users"
            payload = {"usernames": [user_input], "excludeBannedUsers": True}
            data = await self.request("POST", url, json=payload)
            if data and data.get("data"):
                return data["data"][0] 
        return None

    async def get_presences(self, user_ids):
        url = "https://presence.roblox.com/v1/presence/users"
        payload = {"userIds": user_ids}
        return await self.request("POST", url, json=payload)

    async def get_friends(self, user_id):
        url = f"https://friends.roblox.com/v1/users/{user_id}/friends"
        return await self.request("GET", url)

    async def get_avatar(self, user_id):
        url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
        data = await self.request("GET", url)
        if data and data.get("data"):
            return data["data"][0].get("imageUrl")
        return None
    
    async def get_groups(self, user_id):
        url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
        return await self.request("GET", url)

    # --- GAME & SERVER INFO ---
    
    async def can_join_game(self, user_id):
        """Checks if the user's privacy settings allow joining."""
        url = f"https://friends.roblox.com/v1/users/{user_id}/canjoin"
        data = await self.request("GET", url)
        if data:
            return data.get("canJoin", True)
        return True 

    async def get_server_info(self, place_id, game_id):
        """
        Fetches info for a SPECIFIC server ID using direct query.
        Matches code.py logic: GetSpecificServerInfo
        """
        url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?serverId={game_id}"
        data = await self.request("GET", url)
        
        # If data exists in the array, it means the server is Public and we found it.
        if data and "data" in data and len(data["data"]) > 0:
            server = data["data"][0]
            return {
                "playing": server.get("playing", "?"),
                "maxPlayers": server.get("maxPlayers", "?"),
                "ping": server.get("ping", "Unknown"),
                "fps": server.get("fps", "Unknown"),
                "id": server.get("id")
            }
        # If array is empty, server exists (we have game_id) but is Private/Restricted.
        return None