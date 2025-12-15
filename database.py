import aiosqlite
import json

DB_NAME = "stalker_data.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Tracked Users Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tracked_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                ping_mode TEXT DEFAULT 'ping',
                last_presence_type INTEGER DEFAULT 0,
                last_game_name TEXT,
                last_avatar_url TEXT,
                enabled INTEGER DEFAULT 1
            )
        """)
        
        # 2. User Data History
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_history (
                user_id INTEGER PRIMARY KEY,
                friend_ids TEXT DEFAULT '[]',
                group_ids TEXT DEFAULT '[]',
                badge_ids TEXT DEFAULT '[]',
                FOREIGN KEY(user_id) REFERENCES tracked_users(user_id) ON DELETE CASCADE
            )
        """)

        # 3. Server Configuration
        await db.execute("""
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id INTEGER PRIMARY KEY,
                event_channel_id INTEGER,
                log_channel_id INTEGER,
                admin_role_id INTEGER,
                prefix TEXT DEFAULT '!'
            )
        """)
        
        # 4. Schema Migrations
        try:
            await db.execute("ALTER TABLE server_config ADD COLUMN prefix TEXT DEFAULT '!'")
        except Exception:
            pass 

        try:
            # Add columns for detailed game tracking (Server hopping support)
            await db.execute("ALTER TABLE tracked_users ADD COLUMN last_place_id INTEGER")
            await db.execute("ALTER TABLE tracked_users ADD COLUMN last_game_id TEXT")
        except Exception:
            pass

        await db.commit()

async def get_db():
    return await aiosqlite.connect(DB_NAME)

# --- HELPERS ---

async def get_prefix_by_guild_id(guild_id):
    """Fetches prefix directly by ID (Used for main.py startup message)."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT prefix FROM server_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        return row[0] if row else "!"

async def get_server_prefix(bot, message):
    if not message.guild:
        return "!"
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT prefix FROM server_config WHERE guild_id = ?", (message.guild.id,))
        row = await cursor.fetchone()
        return row[0] if row else "!"

async def set_server_prefix(guild_id, new_prefix):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO server_config (guild_id, prefix) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET prefix = ?
        """, (guild_id, new_prefix, new_prefix))
        await db.commit()

async def add_user_to_track(user_id, username, display_name, ping_mode='ping'):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR REPLACE INTO tracked_users 
            (user_id, username, display_name, ping_mode) 
            VALUES (?, ?, ?, ?)
        """, (user_id, username, display_name, ping_mode))
        await db.execute("INSERT OR IGNORE INTO user_history (user_id) VALUES (?)", (user_id,))
        await db.commit()

async def remove_user_track(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM tracked_users WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM user_history WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_all_tracked_users():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tracked_users WHERE enabled = 1")
        return await cursor.fetchall()

async def update_user_field(user_id, field, value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE tracked_users SET {field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

# New function to update presence state atomically
async def update_presence_state(user_id, presence_type, place_id, game_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE tracked_users 
            SET last_presence_type = ?, last_place_id = ?, last_game_id = ?
            WHERE user_id = ?
        """, (presence_type, place_id, game_id, user_id))
        await db.commit()

async def get_user_history(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM user_history WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row if row else None

async def update_history_field(user_id, field, value_list):
    json_val = json.dumps(value_list)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE user_history SET {field} = ? WHERE user_id = ?", (json_val, user_id))
        await db.commit()

async def set_server_config(guild_id, channel_type, channel_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"""
            INSERT INTO server_config (guild_id, {channel_type}) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {channel_type} = ?
        """, (guild_id, channel_id, channel_id))
        await db.commit()
        
async def get_server_configs():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM server_config")
        return await cursor.fetchall()