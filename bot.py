import discord
from discord.ext import commands
from discord import app_commands
import json
import requests

TOKEN = 'YOUR_BOT_TOKEN'
PANEL_URL = 'http://panel.dragoncloud.ggff.net'
API_KEY = 'ptla_9M4qmqeDpJSioG4L2ZyX5hXfi5QCFq3fOSvslNzPaZR'
GUILD_ID = 1349346320325935167 # Replace with int, not string

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

USERS_FILE = 'users.json'

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def get_available_nodes():
    headers = {'Authorization': f'Bearer {API_KEY}', 'Accept': 'application/json'}
    response = requests.get(f'{PANEL_URL}/api/application/nodes', headers=headers)
    data = response.json()['data']
    return [
        (node['attributes']['name'], node['attributes']['id'])
        for node in data
        if node['attributes']['name'] not in ['in1', 'Paris']
    ]

@tree.command(name="register", description="Register an account", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    first_name="Your first name",
    last_name="Your last name",
    username="Choose a username",
    email="Your email address",
    password="Choose a password"
)
async def register(interaction: discord.Interaction, first_name: str, last_name: str, username: str, email: str, password: str):
    users = load_users()
    user_id = str(interaction.user.id)

    if user_id in users:
        await interaction.response.send_message("You are already registered.", ephemeral=True)
        return

    users[user_id] = {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "email": email,
        "password": password
    }
    save_users(users)

    try:
        await interaction.user.send(f"✅ Registration Complete!\n**First Name:** {first_name}\n**Last Name:** {last_name}\n**Username:** {username}\n**Email:** {email}\n**Password:** {password}")
    except discord.Forbidden:
        await interaction.response.send_message("✅ Registered! But I couldn't DM you.", ephemeral=True)
    else:
        await interaction.response.send_message("✅ Registered! Details sent to your DM.", ephemeral=True)

@tree.command(name="createserver", description="Create a Minecraft server", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(node="Select a node")
async def createserver(interaction: discord.Interaction, node: str):
    users = load_users()
    user_id = str(interaction.user.id)

    if user_id not in users:
        await interaction.response.send_message("❌ You must register first using `/register`.", ephemeral=True)
        return

    user_data = users[user_id]
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    data = {
        "name": f"{interaction.user.name}-server",
        "user": 1,
        "egg": 1,
        "docker_image": "ghcr.io/pterodactyl/yolks:java_17",
        "startup": "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar server.jar nogui",
        "limits": {"memory": 4096, "swap": 0, "disk": 10240, "io": 500, "cpu": 200},
        "feature_limits": {"databases": 1, "allocations": 1, "backups": 1},
        "environment": {
            "DL_VERSION": "latest",
            "SERVER_JARFILE": "server.jar",
            "BUILD_NUMBER": "latest"
        },
        "deploy": {
            "locations": [int(node)],
            "dedicated_ip": False,
            "port_range": []
        },
        "start_on_completion": True
    }

    response = requests.post(f"{PANEL_URL}/api/application/servers", headers=headers, json=data)

    if response.status_code == 201:
        await interaction.response.send_message("✅ Server created successfully!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Server creation failed: {response.text}", ephemeral=True)

@tree.command(name="list", description="List all registered users", guild=discord.Object(id=GUILD_ID))
async def list_users(interaction: discord.Interaction):
    # Only bot owner can use
    if interaction.user.id != YOUR_DISCORD_ID:  # Replace with your actual Discord ID
        await interaction.response.send_message("❌ You do not have permission to use this.", ephemeral=True)
        return

    users = load_users()
    if not users:
        await interaction.response.send_message("No registered users found.", ephemeral=True)
        return

    msg = ""
    for uid, info in users.items():
        msg += f"📧 Email: {info['email']}\n🔑 Password: {info['password']}\n🆔 ID: {uid}\n\n"

    await interaction.response.send_message(msg, ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Bot is ready as {bot.user}")

bot.run(TOKEN)
