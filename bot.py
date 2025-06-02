import discord
from discord import app_commands
from discord.ext import commands
import json
import requests

TOKEN = "BOT_TOKEN"
PANEL_URL = "http://panel.dragoncloud.ggff.net"
API_KEY = "ptla_9M4qmqeDpJSioG4L2ZyX5hXfi5QCFq3fOSvslNzPaZR"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "Application/vnd.pterodactyl.v1+json"
}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

def get_user_data(user_id):
    users = load_users()
    return users.get(str(user_id))

@tree.command(name="register")
@app_commands.describe(first_name="Your first name", last_name="Your last name", username="Panel username", email="Email for panel", password="Password")
async def register(interaction: discord.Interaction, first_name: str, last_name: str, username: str, email: str, password: str):
    await interaction.response.defer()
    data = {
        "username": username,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "password": password
    }
    response = requests.post(f"{PANEL_URL}/api/application/users", headers=HEADERS, json=data)
    if response.status_code == 201:
        user_data = response.json()
        users = load_users()
        users[str(interaction.user.id)] = {
            "id": user_data["attributes"]["id"],
            "email": email,
            "password": password
        }
        save_users(users)
        await interaction.followup.send("✅ Registered successfully. Check your DMs.")
        await interaction.user.send(f"🎉 Registered on panel!\nEmail: {email}\nPassword: {password}")
    else:
        await interaction.followup.send(f"❌ Failed to register: {response.text}")

@tree.command(name="list")
async def list_user(interaction: discord.Interaction):
    await interaction.response.defer()
    user_data = get_user_data(interaction.user.id)
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use /register first.")
        return
    await interaction.followup.send(f"📄 Your Details:\nEmail: {user_data['email']}\nPassword: {user_data['password']}\nID: {user_data['id']}")

@tree.command(name="createserver")
@app_commands.describe(name="Server name", node="Select node")
@app_commands.choices(
    node=[
        app_commands.Choice(name="in2 - India", value="3"),
        app_commands.Choice(name="in3 - India", value="5"),
        app_commands.Choice(name="au2 - Australia", value="7")
    ]
)
async def createserver(interaction: discord.Interaction, name: str, node: app_commands.Choice[str]):
    await interaction.response.defer()
    user_data = get_user_data(interaction.user.id)
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use /register first.")
        return

    data = {
        "name": name,
        "user": user_data["id"],
        "egg": 16,
        "docker_image": "ghcr.io/pterodactyl/yolks:java_17",
        "startup": "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar server.jar",
        "environment": {
            "SERVER_JARFILE": "server.jar",
            "MINECRAFT_VERSION": "latest",
            "PAPER_VERSION": "latest"
        },
        "limits": {
            "memory": 4096,
            "swap": 0,
            "disk": 10240,
            "io": 500,
            "cpu": 100
        },
        "feature_limits": {
            "databases": 0,
            "allocations": 1
        },
        "deploy": {
            "locations": [int(node.value)],
            "dedicated_ip": False,
            "port_range": []
        }
    }

    response = requests.post(f"{PANEL_URL}/api/application/servers", headers=HEADERS, json=data)
    if response.status_code == 201:
        await interaction.followup.send("✅ Server created successfully!")
    else:
        await interaction.followup.send(f"❌ Failed to create server: {response.text}")

@tree.command(name="myserver")
async def myserver(interaction: discord.Interaction):
    user_data = get_user_data(interaction.user.id)
    if not user_data:
        await interaction.response.send_message("❌ You are not registered.")
        return

    servers = requests.get(f"{PANEL_URL}/api/application/users/{user_data['id']}/servers", headers=HEADERS).json()
    if not servers["data"]:
        await interaction.response.send_message("🔍 No servers found for your account.")
        return

    srv = servers["data"][0]["attributes"]
    await interaction.response.send_message(f"📡 Your Server:\nName: {srv['name']}\nID: {srv['identifier']}\nIP: {srv['allocations'][0]['ip']}:{srv['allocations'][0]['port']}\nLimits: {srv['limits']['memory']}MB RAM, {srv['limits']['cpu']}% CPU")

@tree.command(name="upgraderam")
async def upgraderam(interaction: discord.Interaction):
    await interaction.response.send_message("💸 To upgrade RAM by 2GB, please send: `owo pay @gamerhacker 200k` and then use `/confirmupgrade`.")

@tree.command(name="confirmupgrade")
async def confirmupgrade(interaction: discord.Interaction):
    await interaction.response.defer()
    user_data = get_user_data(interaction.user.id)
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use /register first.")
        return
    await interaction.followup.send("✅ Upgrade request received. Admin will verify and upgrade RAM.")

@tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency is {round(bot.latency * 1000)}ms")

@tree.command(name="botinfo")
async def botinfo(interaction: discord.Interaction):
    await interaction.response.send_message("🤖 Bot developed by GamerHacker#0001")

@tree.command(name="freeservers")
async def freeservers(interaction: discord.Interaction):
    await interaction.response.send_message("🆓 Use `/register` and then `/createserver` to get your free server!")

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot is ready. Logged in as {bot.user}.")

bot.run(TOKEN)
