import discord
from discord.ext import commands
from discord import app_commands
import json
import aiohttp
import asyncio
import os
from datetime import datetime

# Load Admin ID and Token from config
with open("config.json") as f:
    config = json.load(f)

TOKEN = config["token"]
ADMIN_ID = config["admin_id"]
PANEL_URL = "https://dragoncloud.godanime.net"
HEADERS = {"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# Util: Load/Save JSON
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Gamerzhacker"))
    print(f"Bot is ready as {bot.user}")

# Check admin
def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

# /ping
@tree.command(name="ping", description="Show bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! `{round(bot.latency * 1000)}ms`")

# /botinfo
@tree.command(name="botinfo", description="Show bot developer")
async def botinfo(interaction: discord.Interaction):
    await interaction.response.send_message("🤖 Bot made by Gamerzhacker")

# /addadmin
@tree.command(name="addadmin", description="Add a new admin (only owner)")
@app_commands.describe(userid="User ID to add as admin")
async def addadmin(interaction: discord.Interaction, userid: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return
    config["admin_id"] = userid
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)
    await interaction.response.send_message(f"✅ Admin updated to {userid}", ephemeral=True)

# /createaccount
@tree.command(name="createaccount", description="Create DragonCloud account (admin only)")
@app_commands.describe(userid="Discord User ID", email="Email", password="Password")
@admin_only()
async def createaccount(interaction: discord.Interaction, userid: str, email: str, password: str):
    payload = {
        "username": userid,
        "email": email,
        "first_name": "Dragon",
        "last_name": "User",
        "password": password
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{PANEL_URL}/api/application/users", headers=HEADERS, json=payload) as resp:
            data = await resp.json()
            if resp.status == 201:
                try:
                    user = await bot.fetch_user(int(userid))
                    await user.send(f"✅ Your DragonCloud account has been created!\nEmail: `{email}`\nPassword: `{password}`")
                except:
                    pass
                await interaction.response.send_message("✅ Account created and sent via DM.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Failed to create account: {data}", ephemeral=True)

# /new
@tree.command(name="new", description="Send a message to channel ID")
@app_commands.describe(channel_id="Target Channel ID", message="Message to send")
async def new(interaction: discord.Interaction, channel_id: str, message: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return
    channel = bot.get_channel(int(channel_id))
    if channel:
        await channel.send(message)
        await interaction.response.send_message("✅ Message sent.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)

# /createmsg
@tree.command(name="createmsg", description="Save custom message")
@app_commands.describe(name="Name", message="Message content")
async def createmsg(interaction: discord.Interaction, name: str, message: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return
    data = load_json("custommsgs.json")
    data[name] = message
    save_json("custommsgs.json", data)
    await interaction.response.send_message(f"✅ Message `{name}` saved.", ephemeral=True)

# /antinuke
@tree.command(name="antinuke", description="Antinuke settings")
@app_commands.describe(action="enable/disable/add/remove", usertag="User tag (for add/remove)")
async def antinuke(interaction: discord.Interaction, action: str, usertag: str = None):
    if not interaction.guild:
        await interaction.response.send_message("❌ Use in server only.", ephemeral=True)
        return
    settings = load_json("antinuke.json")
    gid = str(interaction.guild.id)
    settings.setdefault(gid, {"enabled": False, "whitelist": []})

    if action == "enable":
        settings[gid]["enabled"] = True
        await interaction.response.send_message("✅ Antinuke enabled.", ephemeral=True)
    elif action == "disable":
        settings[gid]["enabled"] = False
        await interaction.response.send_message("✅ Antinuke disabled.", ephemeral=True)
    elif action == "add" and usertag:
        settings[gid]["whitelist"].append(usertag)
        await interaction.response.send_message(f"✅ {usertag} whitelisted.", ephemeral=True)
    elif action == "remove" and usertag:
        if usertag in settings[gid]["whitelist"]:
            settings[gid]["whitelist"].remove(usertag)
            await interaction.response.send_message(f"✅ {usertag} removed from whitelist.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ User not in whitelist.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Invalid usage.", ephemeral=True)
    save_json("antinuke.json", settings)

# /serverlist
@tree.command(name="serverlist", description="List all servers (admin only)")
async def serverlist(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PANEL_URL}/api/application/servers", headers=HEADERS) as resp:
            data = await resp.json()
            servers = data.get("data", [])
            msg = "\n".join([f"`{s['attributes']['name']}` - ID: {s['attributes']['id']}" for s in servers])
            await interaction.response.send_message(f"🖥️ Servers:\n{msg or 'None'}", ephemeral=True)

# /removeserver
@tree.command(name="removeserver", description="Remove a server by name (admin only)")
@app_commands.describe(name="Server name to remove")
async def removeserver(interaction: discord.Interaction, name: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PANEL_URL}/api/application/servers", headers=HEADERS) as resp:
            servers = await resp.json()
            for server in servers.get("data", []):
                if server["attributes"]["name"] == name:
                    sid = server["attributes"]["id"]
                    await session.delete(f"{PANEL_URL}/api/application/servers/{sid}", headers=HEADERS)
                    await interaction.response.send_message(f"✅ Server `{name}` removed.", ephemeral=True)
                    return
            await interaction.response.send_message("❌ Server not found.", ephemeral=True)

# /manage
@tree.command(name="manage", description="Manage user server")
@app_commands.describe(userid="User ID")
async def manage(interaction: discord.Interaction, userid: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PANEL_URL}/api/application/users", headers=HEADERS) as r:
            users = await r.json()
            for user in users.get("data", []):
                if user["attributes"]["username"] == userid:
                    user_id = user["attributes"]["id"]
                    break
            else:
                await interaction.response.send_message("❌ User not found.", ephemeral=True)
                return

        async with session.get(f"{PANEL_URL}/api/application/users/{user_id}/servers", headers=HEADERS) as r:
            servers = await r.json()
            if not servers.get("data"):
                await interaction.response.send_message("❌ No server found for user.", ephemeral=True)
                return
            server = servers["data"][0]["attributes"]
            embed = discord.Embed(title=f"Manage {userid}", color=discord.Color.green())
            embed.add_field(name="🟢 Start", value="Successfully started server.")
            embed.add_field(name="🔴 Stop", value="Successfully stopped server.")
            embed.add_field(name="🔁 Reinstall", value="Successfully reinstalled server.")
            embed.set_footer(text=f"Server IP: {server['allocation']['ip']}:{server['allocation']['port']}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(TOKEN)
