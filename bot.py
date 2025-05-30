import discord
from discord import app_commands
from discord.ext import commands
import json
import requests

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

# CONFIG
TOKEN = "YOUR_BOT_TOKEN"
PANEL_URL = "http://panel.dragoncloud.ggff.net"
API_KEY = "ptla_9M4qmqeDpJSioG4L2ZyX5hXfi5QCFq3fOSvslNzPaZR"
GUILD_ID = 1349346320325935167 # Replace with integer guild ID

# JSON storage
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

# Register command
@tree.command(name="register", description="Register for PteroDash", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    firstname="Your first name",
    lastname="Your last name",
    username="Choose a username",
    email="Enter your email",
    password="Choose a password"
)
async def register(interaction: discord.Interaction, firstname: str, lastname: str, username: str, email: str, password: str):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    data = {
        "email": email,
        "username": username,
        "first_name": firstname,
        "last_name": lastname,
        "password": password
    }

    r = requests.post(f"{PANEL_URL}/api/application/users", headers=headers, json=data)
    if r.status_code == 201:
        user_data = r.json()
        users = load_users()
        users[str(interaction.user.id)] = {
            "email": email,
            "password": password,
            "ptero_id": user_data["id"]
        }
        save_users(users)
        try:
            await interaction.user.send(f"✅ Registered successfully!\nEmail: {email}\nPassword: {password}\nID: {user_data['id']}")
            await interaction.response.send_message("✅ Registered! Check your DMs.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("✅ Registered, but I couldn’t DM you!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Registration failed: {r.text}", ephemeral=True)

# List user info
@tree.command(name="list", description="Show your Ptero account details", guild=discord.Object(id=GUILD_ID))
async def list(interaction: discord.Interaction):
    users = load_users()
    user = users.get(str(interaction.user.id))
    if user:
        await interaction.response.send_message(
            f"📧 Email: {user['email']}\n🔑 Password: {user['password']}\n🆔 ID: {user['ptero_id']}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message("❌ You are not registered yet.", ephemeral=True)

# Fetch nodes
def get_nodes():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }
    r = requests.get(f"{PANEL_URL}/api/application/nodes", headers=headers)
    nodes = []
    if r.status_code == 200:
        for node in r.json()["data"]:
            if node["attributes"]["name"].lower() not in ["in1", "paris"]:
                nodes.append(app_commands.Choice(name=node["attributes"]["name"], value=str(node["attributes"]["id"])))
    return nodes

# Create server
@tree.command(name="createserver", description="Create a Minecraft server", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(node="Choose a node")
@app_commands.choices(node=get_nodes())
async def createserver(interaction: discord.Interaction, node: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    users = load_users()
    user_id = str(interaction.user.id)

    if user_id not in users:
        await interaction.followup.send("❌ You must register first using `/register`.")
        return

    user = users[user_id]
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    data = {
        "name": f"{interaction.user.name}-server",
        "user": user["ptero_id"],
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
            "locations": [int(node.value)],
            "dedicated_ip": False,
            "port_range": []
        },
        "start_on_completion": True
    }

    try:
        r = requests.post(f"{PANEL_URL}/api/application/servers", headers=headers, json=data)
        if r.status_code == 201:
            await interaction.followup.send("✅ Server created successfully!")
        else:
            await interaction.followup.send(f"❌ Server creation failed:\n{r.text}")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error occurred: {e}")

# Bot ready
@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ Bot is ready as {bot.user}!")

# Start bot
bot.run(TOKEN)
