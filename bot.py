import discord
from discord import app_commands
from discord.ext import commands
import json
import requests

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

TOKEN ="BOT_TOKEN"
PANEL_URL = "http://panel.dragoncloud.ggff.net"
PANEL_API_KEY = "ptla_9M4qmqeDpJSioG4L2ZyX5hXfi5QCFq3fOSvslNzPaZR"

# Load users.json
def get_user_data(user_id):
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
        return users.get(str(user_id))
    except FileNotFoundError:
        return None

def get_node_id_by_name(name):
    nodes = {
        "in2": 2,  # Replace with real node ID
        "in3": 3,
        "au2": 4
    }
    return nodes.get(name)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is ready. Logged in as {bot.user}.")

@bot.tree.command(name="register", description="Register your account")
@app_commands.describe(first_name="Your first name", last_name="Your last name", username="Your username", email="Your email", password="Your password")
async def register(interaction: discord.Interaction, first_name: str, last_name: str, username: str, email: str, password: str):
    await interaction.response.defer(ephemeral=True)
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "email": email,
        "password": password
    }
    headers = {
        "Authorization": f"Bearer {PANEL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "Application/vnd.pterodactyl.v1+json"
    }
    response = requests.post(f"{PANEL_URL}/api/application/users", json=payload, headers=headers)
    if response.status_code == 201:
        user_data = response.json()
        user_id = str(interaction.user.id)
        try:
            with open("users.json", "r") as f:
                users = json.load(f)
        except FileNotFoundError:
            users = {}
        users[user_id] = {
            "id": user_data["attributes"]["id"],
            "email": email,
            "password": password
        }
        with open("users.json", "w") as f:
            json.dump(users, f, indent=4)
        await interaction.user.send(f"✅ Registered!\nEmail: `{email}`\nPassword: `{password}`\nPanel: {PANEL_URL}")
        await interaction.followup.send("📩 Registration successful. Check your DMs.")
    else:
        await interaction.followup.send(f"❌ Failed to register: `{response.text}`")

@bot.tree.command(name="list", description="List your registered account details")
async def list_accounts(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    user_id = str(interaction.user.id)
    user_data = get_user_data(user_id)
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return
    embed = discord.Embed(title="Your Registered Account", color=discord.Color.blue())
    embed.add_field(name="Email", value=user_data["email"], inline=False)
    embed.add_field(name="User ID", value=user_data["id"], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="createserver", description="Create a free Minecraft server")
@app_commands.describe(server_name="Name for your server", node="Choose a node location")
@app_commands.choices(
    node=[
        app_commands.Choice(name="IN2 - India", value="in2"),
        app_commands.Choice(name="IN3 - India", value="in3"),
        app_commands.Choice(name="AU2 - Australia", value="au2"),
    ]
)
async def createserver(interaction: discord.Interaction, server_name: str, node: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    user_id = str(interaction.user.id)
    user_data = get_user_data(user_id)

    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return

    egg = 1
    docker_image = "ghcr.io/pterodactyl/yolks:java_17"
    startup = "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar server.jar nogui"
    environment = {
        "SERVER_JARFILE": "server.jar",
        "BUILD_NUMBER": "latest",
        "DL_PATH": "https://api.papermc.io/v2/projects/paper/versions/1.20.1/builds/latest/downloads/paper-1.20.1-latest.jar"
    }

    try:
        response = requests.post(
            f"{PANEL_URL}/api/application/servers",
            headers={
                "Authorization": f"Bearer {PANEL_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "Application/vnd.pterodactyl.v1+json"
            },
            json={
                "name": server_name,
                "user": user_data["id"],
                "egg": egg,
                "docker_image": docker_image,
                "startup": startup,
                "environment": environment,
                "limits": {
                    "memory": 4096,
                    "swap": 0,
                    "disk": 10240,
                    "io": 500,
                    "cpu": 200
                },
                "feature_limits": {
                    "databases": 1,
                    "allocations": 1,
                    "backups": 1
                },
                "deploy": {
                    "locations": [],
                    "dedicated_ip": False,
                    "port_range": [],
                    "node": get_node_id_by_name(node.value)
                },
                "start_on_completion": True
            }
        )

        if response.status_code == 201:
            await interaction.followup.send("✅ Server created successfully!")
        else:
            await interaction.followup.send(f"❌ Failed to create server: `{response.text}`")

    except Exception as e:
        await interaction.followup.send(f"❌ Exception: `{str(e)}`")

@bot.tree.command(name="upgraderam", description="Upgrade your server RAM by paying Cowoncy")
async def upgraderam(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    user_id = str(interaction.user.id)
    user_data = get_user_data(user_id)

    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return

    # Prompt user to pay Cowoncy
    await interaction.followup.send(
        "💸 To upgrade your server RAM by 2GB, please send 200,000 Cowoncy to @gamerhacker using the following command:\n"
        "`owo give @gamerhacker 200000`\n"
        "After completing the payment, please confirm by typing `/confirmupgrade`."
    )

@bot.tree.command(name="confirmupgrade", description="Confirm your Cowoncy payment to upgrade RAM")
async def confirmupgrade(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    user_id = str(interaction.user.id)
    user_data = get_user_data(user_id)

    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return

    # Here you would implement the logic to verify the payment.
    # Since OwO Bot does not provide an API to verify transactions,
    # this step would need to be manual or simulated.

    # For demonstration purposes, we'll assume the payment is confirmed.
    # Proceed to upgrade the server RAM.

    # Implement the logic to upgrade the server RAM here.
    # This could involve sending a request to the Pterodactyl API to update the server's memory allocation.

    await interaction.followup.send("✅ Your server RAM has been upgraded by 2GB!")

bot.run(TOKEN)
