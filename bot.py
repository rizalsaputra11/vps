import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json
import random
import asyncio

TOKEN = "BOT_TOKEN"
PTERO_PANEL = "http://panel.dragoncloud.ggff.net"
PTERO_API_KEY = "ptlc_OmXsasCHtMYaeSkv2n3KEJq92qw0yJ0s1OOtS9g8DMh"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

# Load users.json
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

# Save users.json
def save_users(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

# /ping
@tree.command(name="ping", description="Check bot latency")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! 🏓 {round(bot.latency * 1000)}ms")

# /botinfo
@tree.command(name="botinfo", description="Show info about this bot")
async def botinfo(interaction: discord.Interaction):
    embed = discord.Embed(title="PteroDash Bot", description="Free server bot powered by Pterodactyl!", color=0x00ff00)
    embed.add_field(name="Developer", value="Gamerzhacker", inline=True)
    embed.add_field(name="GitHub", value="Coming soon...", inline=True)
    await interaction.response.send_message(embed=embed)

# /freeservers
@tree.command(name="freeservers", description="How to get a free server")
async def freeservers(interaction: discord.Interaction):
    await interaction.response.send_message("Use `/register` to create an account and `/createserver` to get a free Minecraft server!")

# /register
@tree.command(name="register", description="Register a new account on the panel")
@app_commands.describe(
    first_name="Your first name",
    last_name="Your last name",
    username="Username for the panel",
    email="Your email",
    password="Password for panel login"
)
async def register(interaction: discord.Interaction, first_name: str, last_name: str, username: str, email: str, password: str):
    await interaction.response.defer(ephemeral=True)
    users = load_users()

    if str(interaction.user.id) in users:
        await interaction.followup.send("❌ You're already registered.")
        return

    headers = {
        "Authorization": f"Bearer {PTERO_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "Application/vnd.pterodactyl.v1+json"
    }

    payload = {
        "username": username,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "password": password
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{PTERO_PANEL}/api/application/users", headers=headers, json=payload) as resp:
            data = await resp.json()
            if resp.status == 201:
                user_id = data['attributes']['id']
                users[str(interaction.user.id)] = {
                    "email": email,
                    "password": password,
                    "panel_id": user_id
                }
                save_users(users)
                await interaction.user.send(f"✅ Account created!\nEmail: `{email}`\nPassword: `{password}`\nPanel: {PTERO_PANEL}")
                await interaction.followup.send("✅ Registered and details sent in DM!")
            else:
                error = data.get("errors", [{"detail": "Unknown error"}])[0]["detail"]
                await interaction.followup.send(f"❌ Failed to register: {error}")

# /createserver
@tree.command(name="createserver", description="Create a Minecraft server")
async def createserver(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    users = load_users()

    if str(interaction.user.id) not in users:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return

    user_data = users[str(interaction.user.id)]
    user_id = user_data["panel_id"]

    headers = {
        "Authorization": f"Bearer {PTERO_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "Application/vnd.pterodactyl.v1+json"
    }

    # Get all nodes
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PTERO_PANEL}/api/application/nodes", headers=headers) as resp:
            nodes_data = await resp.json()

    # Pick a random node (you can exclude "in1" and "paris" if needed)
    available_nodes = [node["attributes"]["id"] for node in nodes_data["data"]
                       if node["attributes"]["name"].lower() not in ["in1", "paris"]]

    if not available_nodes:
        await interaction.followup.send("❌ No valid nodes found.")
        return

    node_id = random.choice(available_nodes)

    server_name = f"{interaction.user.name}-server"
    payload = {
        "name": server_name,
        "user": user_id,
        "egg": 1,
        "docker_image": "ghcr.io/pterodactyl/yolks:java_17",
        "startup": "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar server.jar nogui",
        "environment": {
            "DL_VERSION": "latest",
            "SERVER_JARFILE": "server.jar",
            "BUILD_NUMBER": "latest"
        },
        "limits": {
            "memory": 4096,
            "swap": 0,
            "disk": 10240,
            "io": 500,
            "cpu": 200
        },
        "feature_limits": {
            "databases": 0,
            "allocations": 1,
            "backups": 1
        },
        "allocation": {
            "default": 1
        },
        "deploy": {
            "locations": [node_id],
            "dedicated_ip": False,
            "port_range": []
        },
        "start_on_completion": True
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{PTERO_PANEL}/api/application/servers", headers=headers, json=payload) as resp:
            if resp.status == 201:
                await interaction.followup.send("✅ Server created! Check your panel.")
            else:
                error = await resp.text()
                await interaction.followup.send(f"❌ Failed to create server: {error}")

bot.run(TOKEN)
