# ==============================
# VRTEX BOT - LAYER 1 (CORE)
# ==============================

# -------- IMPORTS --------
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import os
import motor.motor_asyncio
from datetime import datetime


# -------- CONFIG --------
TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

BOT_NAME = "VRTEX"
BOT_VERSION = "1.0"


# -------- PREFIX MANAGEMENT --------
async def get_prefix(bot, message):

    if not message.guild:
        return ["v"]

    server = cached_servers.get(message.guild.id)

    # default prefix always works
    prefixes = ["v"]

    if server:
        # if server has VRTEX+ and custom prefix
        if server.get("vrt_ex_plus") and server.get("prefix") != "v":
            prefixes.append(server.get("prefix"))

    return prefixes

# -------- BOT INITIALIZATION --------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents
)


# -------- DATABASE --------
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client.vrtex

users_collection = db.users
servers_collection = db.servers


# -------- USER SETUP --------
async def setup_user(user_id: int):
    user = await users_collection.find_one({"user_id": user_id})

    if not user:
        await users_collection.insert_one({
            "user_id": user_id,
            "balance": 0,
            "bank": 0,
            "job": None,
            "job_level": 1,
            "work_streak": 0,
            "last_work": None,
            "inventory": [],
            "created_at": datetime.utcnow()
        })


# -------- SERVER SETUP --------
async def setup_server(guild_id: int):
    server = await servers_collection.find_one({"guild_id": guild_id})

    if not server:
        await servers_collection.insert_one({
            "guild_id": guild_id,
            "prefix": "v",
            "vrt_ex_plus": False,
            "created_at": datetime.utcnow()
        })

# ==============================
# VRTEX BOT – LAYER 2 (DATA FETCHING & CACHE)
# ==============================
# -------- IN-MEMORY CACHE --------
cached_users = {}
cached_servers = {}


# -------- FETCH ALL USERS --------
async def fetch_all_users():
    """
    Fetch all users from MongoDB and store them in memory.
    This ensures user data is restored after every redeploy.
    """
    cached_users.clear()

    cursor = users_collection.find({})
    async for user in cursor:
        cached_users[user["user_id"]] = user

    print(f"[CACHE] Loaded {len(cached_users)} users")


# -------- FETCH ALL SERVERS --------
async def fetch_all_servers():
    """
    Fetch all servers from MongoDB and store them in memory.
    """
    cached_servers.clear()

    cursor = servers_collection.find({})
    async for server in cursor:
        cached_servers[server["guild_id"]] = server

    print(f"[CACHE] Loaded {len(cached_servers)} servers")


# -------- FETCH EVERYTHING --------
async def fetch_all_data():
    """
    Fetch all bot-related data into memory.
    Called once when the bot starts.
    """
    await fetch_all_users()
    await fetch_all_servers()
    print("[CACHE] All data successfully loaded")


# -------- GET USER (FROM CACHE) --------
async def get_user(user_id: int):
    """
    Return user data from cache.
    If user doesn't exist, create and cache them.
    """
    if user_id not in cached_users:
        new_user = {
            "user_id": user_id,
            "balance": 0,
            "bank": 0,
            "job": None,
            "job_level": 1,
            "work_streak": 0,
            "last_work": None,
            "inventory": [],
            "created_at": datetime.utcnow()
        }

        await users_collection.insert_one(new_user)
        cached_users[user_id] = new_user

    return cached_users[user_id]


# -------- GET SERVER (FROM CACHE) --------
async def get_server(guild_id: int):
    """
    Return server data from cache.
    If server doesn't exist, create and cache it.
    """
    if guild_id not in cached_servers:
        new_server = {
            "guild_id": guild_id,
            "prefix": "v",
            "vrt_ex_plus": False,
            "setup_completed": False,
            "created_at": datetime.utcnow()
        }

        await servers_collection.insert_one(new_server)
        cached_servers[guild_id] = new_server

    return cached_servers[guild_id]

# ==============================
# VRTEX BOT - LAYER 3 (ONBOARDING)
# ==============================

from discord.ui import View, Button, Select
from discord import PermissionOverwrite
from discord.ext import commands
from datetime import datetime, timedelta

# -------- CONSTANTS --------

FUN_GAME_CHANNELS = {
    "🧠 memory-games": [
        "remember-words",
        "remember-emojis",
        "remember-colors",
        "remember-numbers",
        "remember-sentences"
    ],
    "❓ quiz-games": [
        "general-quiz",
        "anime-quiz",
        "gaming-quiz",
        "math-quiz",
        "science-quiz",
        "history-quiz",
        "geography-quiz"
    ],
    "🎭 emoji-games": [
        "emoji-match",
        "guess-emotion",
        "emoji-riddle",
        "emoji-translate",
        "odd-emoji"
    ],
    "🔢 logic-games": [
        "number-sequence",
        "pattern-guess",
        "word-scramble",
        "sentence-unscramble",
        "missing-number",
        "riddles"
    ],
    "🕹️ classic-games": [
        "tic-tac-toe",
        "rock-paper-scissors",
        "connect-4",
        "coin-flip",
        "dice-roll"
    ],
    "⚡ speed-games": [
        "fast-click",
        "type-first",
        "reaction-test",
        "first-press",
        "color-reflex"
    ],
    "🎲 luck-games": [
        "slots",
        "spin-wheel",
        "mystery-box",
        "daily-spin",
        "risk-reward"
    ],
    "🗺️ adventure-games": [
        "choose-path",
        "survival",
        "dungeon-escape",
        "treasure-hunt",
        "story-choices"
    ],
    "🤖 ai-games": [
        "would-you-rather",
        "truth-or-dare",
        "guess-character",
        "guess-movie",
        "guess-anime",
        "number-hunt-1-1000"
    ],
    "💰 economy": [
        "economy"
    ]
}

TERMS_AND_CONDITIONS = """
**VRTEX BOT — TERMS & CONDITIONS**

1. VRTEX is a Discord entertainment and utility bot.
2. In-game currency has **NO real-world value**.
3. Selling, trading, or exchanging in-game currency for real money, crypto, or items is **strictly prohibited**.
4. VRTEX is **not responsible** for losses, misuse, or damages caused by user actions.
5. Exploiting bugs, abusing commands, or bypassing systems may result in permanent blacklisting.
6. Premium (VRTEX+) activation keys are server-locked and time-based.
7. Removing the bot does NOT reset subscription time.
8. We may update these terms at any time.

By clicking **Accept**, you agree to all terms above.
"""

# -------- HELPERS --------

async def is_onboarding_complete(guild_id: int):
    server = cached_servers.get(guild_id)
    return server and server.get("onboarding_complete", False)


async def block_if_not_onboarded(interaction: Interaction):
    if not await is_onboarding_complete(interaction.guild_id):
        await interaction.response.send_message(
            "❌ This server has not completed VRTEX onboarding yet.",
            ephemeral=True
        )
        return False
    return True


# -------- CHANNEL CREATION --------

async def create_fun_categories(guild: discord.Guild, staff_role: discord.Role):
    overwrites = {
        guild.default_role: PermissionOverwrite(send_messages=True),
        staff_role: PermissionOverwrite(manage_messages=True)
    }

    for category_name, channels in FUN_GAME_CHANNELS.items():
        category = await guild.create_category(category_name, overwrites=overwrites)

        for ch in channels:
            await guild.create_text_channel(
                ch,
                category=category,
                slowmode_delay=3
            )


# -------- UI VIEWS --------

class VRTEXPlusView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @Button(label="Yes, I have VRTEX+", style=discord.ButtonStyle.success)
    async def yes(self, interaction: Interaction, button: Button):
        await interaction.response.send_message(
            "💎 Please enter your activation key using `/activate <key>`",
            ephemeral=True
        )
        cached_servers[interaction.guild_id]["vrt_ex_plus"] = True

    @Button(label="No, continue without VRTEX+", style=discord.ButtonStyle.secondary)
    async def no(self, interaction: Interaction, button: Button):
        cached_servers[interaction.guild_id]["vrt_ex_plus"] = False
        await send_staff_role_setup(interaction)


class StaffRoleSelect(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)

        options = [
            discord.SelectOption(label="I don't have one, make one"),
            discord.SelectOption(label="I don't want one")
        ]

        for role in guild.roles:
            if not role.is_default():
                options.append(
                    discord.SelectOption(
                        label=role.name,
                        value=str(role.id)
                    )
                )

        self.select = Select(
            placeholder="Select staff role",
            options=options[:25]
        )
        self.select.callback = self.callback
        self.add_item(self.select)

    async def callback(self, interaction: Interaction):
        value = self.select.values[0]

        if value == "I don't have one, make one":
            role = await interaction.guild.create_role(
                name="VRTEX Staff",
                permissions=discord.Permissions(manage_messages=True)
            )
        elif value == "I don't want one":
            role = interaction.guild.default_role
        else:
            role = interaction.guild.get_role(int(value))

        cached_servers[interaction.guild_id]["staff_role_id"] = role.id
        await send_terms(interaction, role)


# -------- ONBOARDING FLOW --------

async def send_staff_role_setup(interaction: Interaction):
    await interaction.response.send_message(
        "🧑‍⚖️ Select your staff/moderator role:",
        view=StaffRoleSelect(interaction.guild),
        ephemeral=True
    )


async def send_terms(interaction: Interaction, staff_role: discord.Role):
    view = View()

    async def accept(interaction: Interaction):
        await create_fun_categories(interaction.guild, staff_role)

        await servers_collection.update_one(
            {"guild_id": interaction.guild_id},
            {"$set": {
                "onboarding_complete": True,
                "onboarded_at": datetime.utcnow()
            }}
        )

        cached_servers[interaction.guild_id]["onboarding_complete"] = True

        await interaction.response.send_message(
            "✅ VRTEX setup complete! The bot is now fully operational.",
            ephemeral=True
        )

    btn = Button(label="Accept Terms", style=discord.ButtonStyle.success)
    btn.callback = accept
    view.add_item(btn)

    await interaction.response.send_message(
        TERMS_AND_CONDITIONS,
        view=view,
        ephemeral=True
    )


# -------- START ONBOARDING COMMAND --------

@bot.tree.command(name="setup", description="Start VRTEX onboarding")
async def setup(interaction: Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Only administrators can run setup.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "💎 Do you have VRTEX+ for this server?",
        view=VRTEXPlusView(),
        ephemeral=True
    )
