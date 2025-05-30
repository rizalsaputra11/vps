import discord
from discord import app_commands
from discord.ext import commands
import json
import aiohttp
import random
import asyncio

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=".", intents=intents)
TOKEN = ""
GUILD_ID = 1349346320325935167  # Replace with your server ID
PANEL_URL = "http://panel.dragoncloud.ggff.net"
PANEL_API_KEY = "ptla_9M4qmqeDpJSioG4L2ZyX5hXfi5QCFq3fOSvslNzPaZR"

USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.tree.command(name="ping", description="Check the bot's ping", guild=discord.Object(id=GUILD_ID))
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! 🏓 Latency: {round(bot.latency * 1000)}ms", ephemeral=True)

@bot.tree.command(name="register", description="Register a new account", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    first_name="Your first name",
    last_name="Your last name",
    username="Your desired username",
    email="Your email",
    password="Your password"
)
async def register(interaction: discord.Interaction, first_name: str, last_name: str, username: str, email: str, password: str):
    users = load_users()
    if str(interaction.user.id) in users:
        await interaction.response.send_message("You are already registered.", ephemeral=True)
        return

    users[str(interaction.user.id)] = {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "email": email,
        "password": password
    }
    save_users(users)

    await interaction.user.send(f"✅ Registered successfully!\n**Username:** {username}\n**Email:** {email}\n**Password:** {password}")
    await interaction.response.send_message("Registration complete. Check your DMs!", ephemeral=True)

@bot.tree.command(name="list", description="List all registered users", guild=discord.Object(id=GUILD_ID))
async def list_users(interaction: discord.Interaction):
    users = load_users()
    if not users:
        await interaction.response.send_message("No users found.", ephemeral=True)
        return

    user_list = "\n".join([
        f"🆔 {uid} - **{data['email']}** / `{data['password']}`"
        for uid, data in users.items()
    ])
    await interaction.response.send_message(f"📄 Registered Users:\n{user_list}", ephemeral=True)

@bot.tree.command(name="createserver", description="Create a Pterodactyl server", guild=discord.Object(id=GUILD_ID))
async def createserver(interaction: discord.Interaction):
    users = load_users()
    user_data = users.get(str(interaction.user.id))
    if not user_data:
        await interaction.response.send_message("❌ You must register first using /register", ephemeral=True)
        return

    # Get available nodes (allowing in1 now)
    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {PANEL_API_KEY}", "Content-Type": "application/json"}) as session:
        async with session.get(f"{PANEL_URL}/api/application/nodes") as resp:
            data = await resp.json()
            nodes = [node for node in data["data"] if "in1" in node["attributes"]["name"] or "Paris" in node["attributes"]["name"] or True]
            node = random.choice(nodes)
            node_id = node["attributes"]["id"]

    server_data = {
        "name": f"{user_data['username']}-server",
        "user": 1,
        "egg": 1,
        "docker_image": "ghcr.io/pterodactyl/yolks:java_17",
        "startup": "java -Xms128M -Xmx4096M -jar server.jar",
        "limits": {"memory": 4096, "swap": 0, "disk": 10240, "io": 500, "cpu": 200},
        "feature_limits": {"databases": 1, "allocations": 1},
        "allocation": {"default": node_id},
        "environment": {
            "DL_VERSION": "latest",
            "SERVER_JARFILE": "server.jar",
            "MINECRAFT_VERSION": "latest",
            "BUILD_NUMBER": "latest"
        }
    }

    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {PANEL_API_KEY}", "Content-Type": "application/json"}) as session:
        async with session.post(f"{PANEL_URL}/api/application/servers", json=server_data) as resp:
            if resp.status == 201:
                await interaction.response.send_message("✅ Server created successfully!", ephemeral=True)
            else:
                error = await resp.text()
                await interaction.response.send_message(f"❌ Failed to create server: {error}", ephemeral=True)

bot.run(TOKEN)
