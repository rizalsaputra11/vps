import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
import asyncio

TOKEN = 'MTM3NzUyMDQxMDc0NDMyNDIwNg.GDat25._7r3593EmbW5L4J4FJvHWlgAB7UcX15PylyUlM'
GUILD_ID =   # Replace with your Discord server ID
PANEL_URL = "http://panel.dragoncloud.ggff.net"
ADMIN_API_KEY = "ptlc_OmXsasCHtMYaeSkv2n3KEJq92qw0yJ0s1OOtS9g8DMh"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

users_file = "users.json"

def load_users():
    try:
        with open(users_file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(users_file, "w") as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Logged in as {bot.user}")

@tree.command(name="register", description="Register an account", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(email="Your email", password="Your password")
async def register(interaction: discord.Interaction, email: str, password: str):
    await interaction.response.defer()
    users = load_users()
    if str(interaction.user.id) in users:
        await interaction.followup.send("You are already registered.")
        return

    headers = {
        "Authorization": f"Bearer {ADMIN_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "Application/vnd.pterodactyl.v1+json"
    }

    data = {
        "username": interaction.user.name.lower(),
        "email": email,
        "first_name": interaction.user.name,
        "last_name": "User",
        "password": password
    }

    response = requests.post(f"{PANEL_URL}/api/application/users", headers=headers, json=data)
    if response.status_code == 201:
        user_info = response.json()["attributes"]
        users[str(interaction.user.id)] = {
            "id": user_info["id"],
            "email": email,
            "password": password
        }
        save_users(users)
        await interaction.followup.send("✅ Registered successfully.")
    else:
        await interaction.followup.send(f"❌ Error: {response.text}")

@tree.command(name="createserver", description="Create a Minecraft server", guild=discord.Object(id=GUILD_ID))
async def createserver(interaction: discord.Interaction):
    await interaction.response.defer()
    users = load_users()
    if str(interaction.user.id) not in users:
        await interaction.followup.send("❌ Please register first using `/register`.")
        return

    user_id = users[str(interaction.user.id)]["id"]

    headers = {
        "Authorization": f"Bearer {ADMIN_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "Application/vnd.pterodactyl.v1+json"
    }

    data = {
        "name": interaction.user.name,
        "user": user_id,
        "egg": 1,
        "docker_image": "ghcr.io/pterodactyl/yolks:java_21",
        "startup": "java -Xms128M -XX:MaxRAMPercentage=95.0 -Dterminal.jline=false -Dterminal.ansi=true -jar {{SERVER_JARFILE}}",
        "limits": {
            "memory": 4096,
            "swap": 0,
            "disk": 10240,
            "io": 500,
            "cpu": 200
        },
        "feature_limits": {
            "databases": 0,
            "backups": 0,
            "allocations": 1
        },
        "environment": {
            "SERVER_JARFILE": "server.jar",
            "BUILD_NUMBER": "latest",
            "MINECRAFT_VERSION": "latest",
            "DL_PATH": ""
        },
        "deploy": {
            "locations": [1],
            "dedicated_ip": False,
            "port_range": []
        },
        "start_on_completion": True
    }

    response = requests.post(f"{PANEL_URL}/api/application/servers", headers=headers, json=data)
    if response.status_code == 201:
        await interaction.followup.send("✅ Server created successfully!")
    else:
        await interaction.followup.send(f"❌ Failed to create server: {response.text}")

@tree.command(name="ping", description="Check bot latency", guild=discord.Object(id=GUILD_ID))
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")

@tree.command(name="botinfo", description="Show bot developer info", guild=discord.Object(id=GUILD_ID))
async def botinfo(interaction: discord.Interaction):
    await interaction.response.send_message("🤖 PteroDash7\n👨‍💻 Developer: `YourName`\n🌐 Panel: http://panel.dragoncloud.ggff.net")

bot.run(TOKEN)
