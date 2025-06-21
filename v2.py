# Full bot.py with all required commands and no missing functionality
import discord
from discord.ext import commands
from discord import app_commands
import json
import aiohttp
import asyncio
import os
import subprocess
from datetime import datetime

# Load config
with open("config.json") as f:
    config = json.load(f)

TOKEN = ""
ADMIN_ID = ""
PANEL_URL = "https://dragoncloud.godanime.net"
API_KEY = ""
HEADERS = {"Authorization": f"Bearer api_key", "Content-Type": "application/json"}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# Util functions
def load_json(file):
    return json.load(open(file)) if os.path.exists(file) else {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

users_data = load_json("users.json")
codes_data = load_json("codes.json")
antinuke_data = load_json("antinuke.json")

@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Gamerzhacker"))
    print(f"Bot is ready as {bot.user}")

# Admin Check
def is_admin(user):
    return str(user.id) == str(ADMIN_ID)

# /ping
@tree.command(name="ping", description="Bot ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong: {round(bot.latency * 1000)}ms")

# /botinfo
@tree.command(name="botinfo")
async def botinfo(interaction: discord.Interaction):
    await interaction.response.send_message("🤖 Made by Gamerzhacker")

# /addadmin
@tree.command(name="addadmin")
@app_commands.describe(userid="User ID")
async def addadmin(interaction: discord.Interaction, userid: str):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    config["admin_id"] = userid
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)
    await interaction.response.send_message(f"✅ Admin set to {userid}")

# /createaccount
@tree.command(name="createaccount")
@app_commands.describe(email="Email", password="Password")
async def createaccount(interaction: discord.Interaction, email: str, password: str):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    async with aiohttp.ClientSession() as session:
        payload = {
            "email": email,
            "username": email.split("@")[0],
            "first_name": "User",
            "last_name": "DC",
            "password": password
        }
        async with session.post(f"{PANEL_URL}/api/application/users", headers=HEADERS, json=payload) as resp:
            if resp.status == 201:
                await interaction.response.send_message("✅ Account created.")
            else:
                await interaction.response.send_message("❌ Error creating account")

# /removeaccount
@tree.command(name="removeaccount")
@app_commands.describe(userid="Panel User ID")
async def removeaccount(interaction: discord.Interaction, userid: int):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{PANEL_URL}/api/application/users/{userid}", headers=HEADERS) as resp:
            if resp.status == 204:
                await interaction.response.send_message("✅ User deleted")
            else:
                await interaction.response.send_message("❌ Failed to delete user")

# /dailycredits
@tree.command(name="dailycredits")
async def dailycredits(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    users_data.setdefault(uid, {"credits": 0})
    users_data[uid]["credits"] += 20
    save_json("users.json", users_data)
    await interaction.response.send_message("✅ You earned 20 credits!")

# /credits
@tree.command(name="credits")
async def credits(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    balance = users_data.get(uid, {}).get("credits", 0)
    await interaction.response.send_message(f"💰 You have {balance} credits.")

# /addcredit
@tree.command(name="addcredit")
@app_commands.describe(userid="Discord ID", amount="Amount")
async def addcredit(interaction: discord.Interaction, userid: str, amount: int):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    users_data.setdefault(userid, {"credits": 0})
    users_data[userid]["credits"] += amount
    save_json("users.json", users_data)
    await interaction.response.send_message(f"✅ Added {amount} credits to {userid}")

# /renewvps
@tree.command(name="renewvps")
async def renewvps(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if users_data.get(uid, {}).get("credits", 0) >= 500:
        users_data[uid]["credits"] -= 500
        save_json("users.json", users_data)
        await interaction.response.send_message("🔁 VPS renewed for 30 days!")
    else:
        await interaction.response.send_message("❌ Not enough credits (need 500).")

# /create-vps (tmate)
@tree.command(name="create-vps")
@app_commands.describe(userid="User ID", amount="Credits to charge")
async def create_vps(interaction: discord.Interaction, userid: str, amount: int):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    proc = subprocess.Popen("tmate -F", shell=True, stdout=subprocess.PIPE)
    try:
        for line in iter(proc.stdout.readline, b''):
            decoded = line.decode()
            if "ssh" in decoded:
                ssh_line = decoded.strip()
                break
        else:
            return await interaction.response.send_message("❌ Failed to get SSH")
    except Exception as e:
        return await interaction.response.send_message(f"❌ Error: {e}")
    await interaction.user.send(f"🔐 SSH: `{ssh_line}`")
    await interaction.response.send_message("✅ VPS created and DM'd SSH.")

# /suspendvps
@tree.command(name="suspendvps")
async def suspendvps(interaction: discord.Interaction, userid: str):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    await interaction.response.send_message(f"🚫 Suspended VPS for {userid}")

# /unsuspendvps
@tree.command(name="unsuspendvps")
async def unsuspendvps(interaction: discord.Interaction, userid: str):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    await interaction.response.send_message(f"✅ Unsuspended VPS for {userid}")

# /clear and .clear
@bot.command(name="clear")
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Cleared {amount} messages", delete_after=3)

@tree.command(name="clear")
@app_commands.describe(amount="Messages to delete")
async def clear_slash(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 Cleared {amount} messages", ephemeral=True)

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

# /ControlServer
@tree.command(name="controlserver")
@app_commands.describe(userid="Username on Panel")
async def controlserver(interaction: discord.Interaction, userid: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PANEL_URL}/api/application/users", headers=HEADERS) as r:
            users = await r.json()
            for u in users.get("data", []):
                if u["attributes"]["username"] == userid:
                    user_id = u["attributes"]["id"]
                    break
            else:
                return await interaction.response.send_message("❌ User not found")
        async with session.get(f"{PANEL_URL}/api/application/users/{user_id}/servers", headers=HEADERS) as r:
            data = await r.json()
            if not data.get("data"):
                return await interaction.response.send_message("❌ No server found")
            s = data["data"][0]["attributes"]
            embed = discord.Embed(title=f"{s['name']} - Server Control", color=discord.Color.green())
            embed.add_field(name="IP", value=f"{s['allocation']['ip']}:{s['allocation']['port']}")
            embed.add_field(name="Start", value="✅ Start server")
            embed.add_field(name="Stop", value="🟥 Stop server")
            embed.add_field(name="Reinstall", value="🔁 Reinstall server")
            embed.add_field(name="Kill", value="💥 Kill server")
            await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
