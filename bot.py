# Full DragonCloud bot.py with all commands (excluding AntiNuke)
import discord
from discord.ext import commands
from discord import app_commands
import json
import aiohttp
import asyncio
import os
import subprocess
from datetime import datetime
from typing import Optional

# Load config
with open("config.json") as f:
    config = json.load(f)

TOKEN = ""
ADMIN_ID = "1159037240622723092"
PANEL_URL = "https://dragoncloud.godanime.net"
PANEL_API_KEY = "ptla_OK2TnEswXZKYxMTNLQyJgcGQUEb4u0uLs8GEzUDAuIw"
API_KEY = "ptla_OK2TnEswXZKYxMTNLQyJgcGQUEb4u0uLs8GEzUDAuIw"
API_KEYS = "ptlc_gBDCPzaoIyETs1dm1X8mtcSojVFSKnwJUplnhdpVVSf"
ADMIN_IDS = "1159037240622723092"
HEADERS = {"Authorization": f"Bearer {PANEL_API_KEY}", "Content-Type": "application/json"}
EGG_ID = 1  # Replace with your Minecraft (Paper) egg ID
NODE_ID = 1  # Replace with your default node ID
PANEL_APP_ID = "1"  # Replace with Minecraft egg ID
NODE_ID = 1 # Replace with 1 node ID

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
giveaways_file = "giveaways.json"
accountapi_file = "accountapi.json"
account_data_file = "accounts.json"
status_channel_file = 'status_channel.txt'
CONFIG_FILE = "panel_config.json"

@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Pterodactyl Panel Manager"))
    print(f"Bot is ready as {bot.user}")

def is_admin(user):
    return str(user.id) == str(ADMIN_ID)

@tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong: {round(bot.latency * 1000)}ms")

@tree.command(name="botinfo")
async def botinfo(interaction: discord.Interaction):
    await interaction.response.send_message("** Bot Version 1.0.0 Dev. Gamerzhacker ")

@tree.command(name="addadmin")
@app_commands.describe(userid="User ID")
async def addadmin(interaction: discord.Interaction, userid: str):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    config["admin_id"] = userid
    with open("config.json", "w") as f: json.dump(config, f, indent=4)
    await interaction.response.send_message(f"✅ Admin set to {userid}")

@tree.command(name="createaccount")
@app_commands.describe(email="Email", password="Password")
async def createaccount(interaction: discord.Interaction, email: str, password: str):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    async with aiohttp.ClientSession() as session:
        payload = {"email": email, "username": email.split("@")[0], "first_name": "User", "last_name": "DC", "password": password}
        async with session.post(f"{PANEL_URL}/api/application/users", headers=HEADERS, json=payload) as resp:
            await interaction.response.send_message("✅ Account created." if resp.status == 201 else "❌ Error creating account")

@tree.command(name="removeaccount")
@app_commands.describe(userid="Panel User ID")
async def removeaccount(interaction: discord.Interaction, userid: int):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{PANEL_URL}/api/application/users/{userid}", headers=HEADERS) as resp:
            await interaction.response.send_message("✅ User deleted" if resp.status == 204 else "❌ Failed to delete user")

@tree.command(name="dailycredits")
async def dailycredits(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    users_data.setdefault(uid, {"credits": 0})
    users_data[uid]["credits"] += 20
    save_json("users.json", users_data)
    await interaction.response.send_message("✅ You earned 20 credits!")

@tree.command(name="credits")
async def credits(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    balance = users_data.get(uid, {}).get("credits", 0)
    await interaction.response.send_message(f"💰 You have {balance} credits.")

@tree.command(name="addcredit")
@app_commands.describe(userid="Discord ID", amount="Amount")
async def addcredit(interaction: discord.Interaction, userid: str, amount: int):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    users_data.setdefault(userid, {"credits": 0})
    users_data[userid]["credits"] += amount
    save_json("users.json", users_data)
    await interaction.response.send_message(f"✅ Added {amount} credits to {userid}")

@tree.command(name="renewvps")
async def renewvps(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if users_data.get(uid, {}).get("credits", 0) >= 500:
        users_data[uid]["credits"] -= 500
        save_json("users.json", users_data)
        await interaction.response.send_message("🔁 VPS renewed for 30 days!")
    else:
        await interaction.response.send_message("❌ Not enough credits (need 500).")

@tree.command(name="createredeemcode")
@app_commands.describe(code="Code", creditamount="Credits", claimlimit="Claim Limit")
async def createredeemcode(interaction: discord.Interaction, code: str, creditamount: int, claimlimit: int):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    codes_data[code] = {"credits": creditamount, "limit": claimlimit, "used": []}
    save_json("codes.json", codes_data)
    await interaction.response.send_message(f"✅ Redeem code `{code}` created")

@tree.command(name="redeemcode")
@app_commands.describe(code="Enter code")
async def redeemcode(interaction: discord.Interaction, code: str):
    uid = str(interaction.user.id)
    code_data = codes_data.get(code)
    if not code_data:
        return await interaction.response.send_message("❌ Invalid code")
    if uid in code_data["used"]:
        return await interaction.response.send_message("❌ Already redeemed")
    if len(code_data["used"]) >= code_data["limit"]:
        return await interaction.response.send_message("❌ Code limit reached")
    users_data.setdefault(uid, {"credits": 0})
    users_data[uid]["credits"] += code_data["credits"]
    code_data["used"].append(uid)
    save_json("codes.json", codes_data)
    save_json("users.json", users_data)
    await interaction.response.send_message(f"✅ Redeemed `{code}` for {code_data['credits']} credits!")

@tree.command(name="status")
async def status(interaction: discord.Interaction):
    await interaction.response.send_message("🟢 Panel Status: Online at https://zyrotheme.fluxhosting.cloud")

@tree.command(name="uptime")
async def uptime(interaction: discord.Interaction):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await interaction.response.send_message(f"🕒 Panel is reachable. Current Time: {now}")

@tree.command(name="freeserver")
async def freeserver(interaction: discord.Interaction):
    await interaction.response.send_message("🎁 Free Plan: 2GB RAM / 1 CPU\nCreate a ticket in <#ticket-channel>")

@tree.command(name="serverlist")
async def serverlist(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PANEL_URL}/api/application/servers", headers=HEADERS) as r:
            data = await r.json()
            servers = data.get("data", [])
            if not servers:
                return await interaction.response.send_message("❌ No servers found")
            msg = "\n".join([f"🖥️ {s['attributes']['name']} (ID: {s['attributes']['id']})" for s in servers])
            await interaction.response.send_message(f"📋 Servers:\n{msg}")

@tree.command(name="removeserver")
@app_commands.describe(serverid="Panel Server ID")
async def removeserver(interaction: discord.Interaction, serverid: str):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{PANEL_URL}/api/application/servers/{serverid}", headers=HEADERS) as r:
            await interaction.response.send_message("✅ Server removed" if r.status == 204 else "❌ Failed to remove")

@tree.command(name="createmsg")
@app_commands.describe(name="Message name", message="Message content")
async def createmsg(interaction: discord.Interaction, name: str, message: str):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    save_json(f"msg_{name}.json", {"content": message})
    await interaction.response.send_message(f"✅ Saved message `{name}`")

@tree.command(name="new")
@app_commands.describe(channelid="Channel ID", message="Message to send")
async def new(interaction: discord.Interaction, channelid: str, message: str):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
    channel = bot.get_channel(int(channelid))
    if channel:
        await channel.send(message)
        await interaction.response.send_message("✅ Message sent")
    else:
        await interaction.response.send_message("❌ Channel not found")

# -------------------- HELP --------------------
@bot.tree.command(name="help", description="Show list of available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📘 Command List", color=discord.Color.green())
    embed.add_field(name="/ownlist <userid>", value="🔒 Admin only: Generate server list for a user.", inline=False)
    embed.add_field(name="/list <userid>", value="📋 Show servers owned by a user.", inline=False)
    embed.add_field(name="/deleteownlist <userid>", value="🗑️ Admin only: Delete stored server list for a user.", inline=False)
    embed.add_field(name="/upgrademc <serverid> <ram> <cpu> <disk>", value="⚙️ Admin only: Upgrade server specs.", inline=False)
    embed.add_field(name="/manage <token>", value="🎮 View & control Minecraft servers (client token)", inline=False)
    embed.add_field(name="/register <userid> <username> <email> <password>", value="🧾 Create panel account.", inline=False)
    embed.add_field(name="/ac <userid> <email> <pass>", value="⚡ Quick account creation.", inline=False)
    embed.add_field(name="/createfree <servername> <email>", value="🚀 Create 4GB Minecraft server.", inline=False)
    embed.add_field(name="/creates", value="📦 Show plan selection (invite/boost).", inline=False)
    embed.add_field(name="/removeall <userid>", value="🗑 Remove all Minecraft servers.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# -------------------- OWNLIST --------------------
@bot.tree.command(name="ownlist", description="Generate random Minecraft server IDs for a user (admin only)")
@app_commands.describe(userid="User's Discord ID")
async def ownlist(interaction: discord.Interaction, userid: str):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    servers = [f"{random.randint(100000, 999999)}_IN" for _ in range(3)]

    if not os.path.exists(data_file):
        with open(data_file, "w") as f:
            json.dump({}, f)

    with open(data_file, "r") as f:
        data = json.load(f)
    data[userid] = servers
    with open(data_file, "w") as f:
        json.dump(data, f)

    await interaction.response.send_message(f"✅ Created server list for `{userid}`:\n" + "\n".join(servers), ephemeral=True)

# -------------------- LIST --------------------
@bot.tree.command(name="list", description="List Minecraft servers of a user from /ownlist")
@app_commands.describe(userid="User's Discord ID")
async def list_servers(interaction: discord.Interaction, userid: str):
    try:
        with open(data_file, "r") as f:
            data = json.load(f)
        servers = data.get(userid)
        if not servers:
            await interaction.response.send_message("❌ No servers found for this user.", ephemeral=True)
            return
        msg = f"📋 Servers owned by `{userid}`:\n" + "\n".join(f"- `{s}`" for s in servers)
        await interaction.response.send_message(msg, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Error reading list: {e}", ephemeral=True)

# -------------------- REGISTER --------------------
@bot.tree.command(name="register", description="Register a new panel account")
@app_commands.describe(userid="User ID", username="Username", email="Email", password="Password")
async def register(interaction: discord.Interaction, userid: str, username: str, email: str, password: str):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        return
    payload = {
        "username": username,
        "email": email,
        "first_name": username,
        "last_name": "user",
        "password": password
    }
    headers = {
        "Authorization": f"Bearer {PANEL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{PANEL_URL}/api/application/users", headers=headers, json=payload) as resp:
            if resp.status == 201:
                await interaction.response.send_message("✅ Account created successfully.", ephemeral=True)
            else:
                text = await resp.text()
                await interaction.response.send_message(f"❌ Failed: {resp.status} {text}", ephemeral=True)

# -------------------- CREATEFREE --------------------
@bot.tree.command(name="createfree", description="🎮 Create Free Minecraft Server")
@app_commands.describe(servername="Your server name", email="Your panel email")
async def createfree(interaction: discord.Interaction, servername: str, email: str):
    headers = {
        "Authorization": f"Bearer {PANEL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        # Find panel user by email
        async with session.get(f"{PANEL_URL}/api/application/users", headers=headers) as user_resp:
            users = await user_resp.json()
            user_id = None
            for u in users["data"]:
                if u["attributes"]["email"] == email:
                    user_id = u["attributes"]["id"]
                    break

        if not user_id:
            await interaction.response.send_message("❌ Panel user not found. Please create account using `/ac`.", ephemeral=True)
            return

        await interaction.response.send_message("⏳ Creating your server. Please wait...", ephemeral=True)

        # Server config
        server_data = {
            "name": servername,
            "user": user_id,
            "egg": MINECRAFT_EGG_ID,
            "docker_image": "ghcr.io/pterodactyl/yolks:java_17",
            "startup": "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar server.jar nogui",
            "limits": {"memory": 4096, "swap": 0, "disk": 10240, "io": 500, "cpu": 100},
            "feature_limits": {"databases": 0, "backups": 0, "allocations": 1},
            "environment": {
                "SERVER_JARFILE": "server.jar",
                "DL_PATH": "https://api.papermc.io/v2/projects/paper/versions/1.20.1/builds/103/downloads/paper-1.20.1-103.jar",
                "VERSION": "1.20.1",
                "TYPE": "vanilla"
            },
            "deploy": {"locations": [1], "dedicated_ip": False, "port_range": []},
            "start_on_completion": True
        }

        async with session.post(f"{PANEL_URL}/api/application/servers", headers=headers, json=server_data) as resp:
            if resp.status in [200, 201]:
                await interaction.followup.send("✅ Successfully created your server. Check panel link in DM!", ephemeral=True)
                await interaction.user.send(f"🎉 Your Minecraft server `{servername}` has been created!\n🔗 Panel: {PANEL_URL}")
            else:
                error = await resp.text()
                await interaction.followup.send(f"❌ Failed to create server: `{error}`", ephemeral=True)

# -------------------- REMOVEALL --------------------
@bot.tree.command(name="removeall", description="Remove all Minecraft servers by user ID")
@app_commands.describe(userid="User ID")
async def removeall(interaction: discord.Interaction, userid: str):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        return
    url = f"{PANEL_URL}/api/application/servers"
    headers = {"Authorization": f"Bearer {PANEL_API_KEY}", "Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                servers = [s for s in data['data'] if str(s['attributes']['user']) == str(userid)]
                count = 0
                for s in servers:
                    sid = s['attributes']['id']
                    await session.delete(f"{url}/{sid}", headers=headers)
                    count += 1
                await interaction.response.send_message(f"✅ Removed {count} servers.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error fetching server list.", ephemeral=True)

# -------------------- UPGRADEMC --------------------
@bot.tree.command(name="upgrademc", description="Upgrade Minecraft server specs")
@app_commands.describe(serverid="External Server ID", ram="RAM (MB)", cpu="CPU %", disk="Disk (MB)")
async def upgrademc(interaction: discord.Interaction, serverid: str, ram: int, cpu: int, disk: int):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Unauthorized", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    sid = await get_server_internal_id(serverid)
    if not sid:
        await interaction.followup.send("❌ Server ID not found.")
        return
    url = f"{PANEL_URL}/api/application/servers/{sid}/build"
    payload = {
        "memory": ram,
        "disk": disk,
        "cpu": cpu,
        "io": 500,
        "swap": 0,
        "feature_limits": {"databases": 5, "backups": 5, "allocations": 5}
    }
    headers = {"Authorization": f"Bearer {PANEL_API_KEY}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.patch(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                await interaction.followup.send("✅ Upgrade successful.", ephemeral=True)
            else:
                text = await resp.text()
                await interaction.followup.send(f"❌ Failed: {resp.status}\n{text}", ephemeral=True)

# -------------------- GET SERVER INTERNAL ID --------------------
async def get_server_internal_id(external_id):
    url = f"{PANEL_URL}/api/application/servers"
    headers = {"Authorization": f"Bearer {PANEL_API_KEY}", "Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                for s in data['data']:
                    if s['attributes']['identifier'] == external_id:
                        return s['attributes']['id']
    return None

# -------------------- MANAGE + BUTTONS --------------------
class ServerControlView(discord.ui.View):
    def __init__(self, token: str, serverid: str):
        super().__init__(timeout=None)
        self.token = token
        self.serverid = serverid

    async def send_power_signal(self, interaction: discord.Interaction, signal: str):
        url = f"https://dragoncloud.godanime.net/api/client/servers/{self.serverid}/power"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={"signal": signal}) as resp:
                if resp.status == 204:
                    await interaction.response.send_message(f"✅ `{signal}` sent to `{self.serverid}`.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ Failed to send `{signal}`. Status: {resp.status}", ephemeral=True)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.success)
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_power_signal(interaction, "start")

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_power_signal(interaction, "stop")

    @discord.ui.button(label="Restart", style=discord.ButtonStyle.primary)
    async def restart_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_power_signal(interaction, "restart")

    @discord.ui.button(label="Reinstall", style=discord.ButtonStyle.secondary)
    async def reinstall_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_power_signal(interaction, "reinstall")

    @discord.ui.button(label="Upload", style=discord.ButtonStyle.blurple, emoji="📥")
    async def upload_btn(self, i: discord.Interaction, _):
        await i.response.send_message("📎 Send me **one** attachment within 60 s.", ephemeral=True)

        def chk(m: discord.Message):
            return m.author == i.user and m.attachments

        try:
            msg = await bot.wait_for("message", timeout=60, check=chk)
        except asyncio.TimeoutError:
            await i.followup.send("❌ Timeout – no file.", ephemeral=True)
            return

        att: discord.Attachment = msg.attachments[0]
        data = await att.read()

        async with self._client() as s:
            async with s.put(f"{self.base}/files/write?file=/{att.filename}", data=data) as resp:
                if resp.status == 204:
                    await i.followup.send(f"✅ Uploaded `{att.filename}`", ephemeral=True)
                else:
                    await i.followup.send(f"❌ Upload failed ({resp.status}).", ephemeral=True)

    @discord.ui.button(label="IP Info", style=discord.ButtonStyle.gray, emoji="🌐")
    async def ipinfo_btn(self, i: discord.Interaction, _):
        async with self._client() as s:
            r = await s.get(f"{self.base}/network/allocations")
            al = await r.json()
        lines = [
            f"`{a['attributes']['ip']}:{a['attributes']['port']}` {'(primary)' if a['attributes']['is_default'] else ''}"
            for a in al["data"]
        ]
        embed = discord.Embed(title="🌐 Allocations", description="\n".join(lines), color=0x3498db)
        await i.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Delete File", style=discord.ButtonStyle.red, emoji="🗑")
    async def delete_file(self, i: discord.Interaction, _):
        class PathModal(discord.ui.Modal, title="Delete File"):
            file_path = discord.ui.TextInput(label="Path (e.g. server.jar)", required=True)

            async def on_submit(self, modal_i: discord.Interaction):
                path = "/" + self.file_path.value.lstrip("/")
                async with self._client() as s:
                    # must send array of objects: [{root,path}]
                    payload = [{"root": "/", "path": path}]
                    r = await s.post(f"{self.base}/files/delete", json=payload)
                if r.status == 204:
                    await modal_i.response.send_message(f"🗑 Deleted `{path}`", ephemeral=True)
                else:
                    await modal_i.response.send_message(f"❌ Delete failed ({r.status}).", ephemeral=True)

        await i.response.send_modal(PathModal())

@bot.tree.command(name="manage", description="Show Minecraft servers with token and control buttons")
@app_commands.describe(token="Your Pterodactyl Client API Token")
async def manage(interaction: discord.Interaction, token: str):
    await interaction.response.defer(ephemeral=True)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.get("https://dragoncloud.godanime.net/api/client", headers=headers) as resp:
            if resp.status != 200:
                await interaction.followup.send("❌ Invalid token.")
                return
            data = await resp.json()

    servers = data.get("data", [])
    if not servers:
        await interaction.followup.send("❌ No servers found.", ephemeral=True)
        return

    for server in servers:
        sid = server['attributes']['identifier']
        name = server['attributes']['name']
        embed = discord.Embed(title=f"🎮 {name} ({sid})", color=discord.Color.blurple())
        embed.add_field(name="Controls", value="Start / Stop / Restart / Reinstall / Upload / Ip Info / Delete File", inline=False)
        await interaction.followup.send(embed=embed, view=ServerControlView(token, sid), ephemeral=True)

# -------------------- GET SERVER INTERNAL ID --------------------
async def get_server_internal_id(identifier):
    url = "https://dragoncloud.godanime.net/api/application/servers"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            for s in data.get("data", []):
                if s['attributes']['identifier'] == identifier:
                    return s['attributes']['id']
    return None

# -------------------- GIVEAWAY --------------------
@bot.tree.command(name="gstart", description="🎉 Start a giveaway (admin only)")
@app_commands.describe(time="Time in minutes", winners="Number of winners", prize="Prize description")
async def gstart(interaction: discord.Interaction, time: int, winners: int, prize: str):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
        return

    end_time = datetime.utcnow() + timedelta(minutes=time)
    embed = discord.Embed(title="🎉 Giveaway Started!", color=discord.Color.gold())
    embed.add_field(name="Prize", value=prize, inline=False)
    embed.add_field(name="Ends In", value=f"{time} minutes", inline=False)
    embed.add_field(name="Host", value=interaction.user.mention)
    embed.set_footer(text=f"Ends at {end_time.strftime('%H:%M:%S UTC')}")

    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")
    await interaction.response.send_message("✅ Giveaway started!", ephemeral=True)

    await asyncio.sleep(time * 60)

    msg = await interaction.channel.fetch_message(msg.id)
    users = await msg.reactions[0].users().flatten()
    users = [u for u in users if not u.bot and u != interaction.user]
    if len(users) < winners:
        await interaction.channel.send("❌ Not enough participants.")
    else:
        winners_list = random.sample(users, winners)
        winner_mentions = ", ".join([w.mention for w in winners_list])
        await interaction.channel.send(f"🎉 Congratulations {winner_mentions}! You won **{prize}**")

# -------------------- CHANGEPASS --------------------
@bot.tree.command(name="changepass", description="🔐 Change user's Pterodactyl password (admin only)")
@app_commands.describe(userid="User ID", api_key="Account API key", newpass="New password", confirmpass="Confirm password")
async def changepass(interaction: discord.Interaction, userid: str, api_key: str, newpass: str, confirmpass: str):
    if newpass != confirmpass:
        await interaction.response.send_message("❌ Passwords do not match.", ephemeral=True)
        return

    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return

    headers = {
        "Authorization": f"Bearer {PANEL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"{PANEL_URL}/api/client/account/password"
    payload = {"current_password": newpass, "password": newpass, "password_confirmation": confirmpass}

    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                await interaction.user.send(f"🔐 Your password has been updated.")
                await interaction.user.send(f"🔑 Account API: `{api_key}`\n🔑 New Password: `{newpass}`")
                await interaction.response.send_message("✅ Password changed and DM sent.", ephemeral=True)
            else:
                text = await resp.text()
                await interaction.response.send_message(f"❌ Failed to update password.\n{text}", ephemeral=True)

# -------------------- ACCOUNTAPI STORE --------------------
@bot.tree.command(name="accountapi", description="📂 Add or show account API info")
@app_commands.describe(userid="User ID", name="Api name", msg="Api Key Enter")
async def accountapi(interaction: discord.Interaction, userid: str, api: str, name: str, msg: str):
    if not os.path.exists(accountapi_file):
        with open(accountapi_file, "w") as f:
            json.dump({}, f)

    with open(accountapi_file, "r") as f:
        data = json.load(f)

    data[userid] = {"name": name, "msg": msg}

    with open(accountapi_file, "w") as f:
        json.dump(data, f)

    await interaction.response.send_message(f"✅ API stored for `{userid}`.", ephemeral=True)
    user = bot.get_user(int(userid))
    if user:
        await user.send(f"📂 API Stored\n🔑 Key: `{api}`\n📛 Name: `{name}`\n📝 Message: {msg}")

# -------------------- Helper to get panel user ID --------------------
async def get_panel_user_id_by_email(email):
    headers = {"Authorization": f"Bearer {PANEL_API_KEY}", "Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PANEL_URL}/api/application/users", headers=headers) as resp:
            if resp.status == 200:
                users = await resp.json()
                for u in users["data"]:
                    if u["attributes"]["email"].lower() == email.lower():
                        return u["attributes"]["id"]
    return None

# -------------------- /ac COMMAND (store account info) --------------------
@bot.tree.command(name="ac", description="🔑 Store user account info")
@app_commands.describe(userid="User ID", email="Panel email", password="Password")
async def ac(interaction: discord.Interaction, userid: str, email: str, password: str):
    accounts = {}
    if os.path.exists(account_data_file):
        with open(account_data_file, "r") as f:
            accounts = json.load(f)

    accounts[userid] = {"email": email, "password": password}

    with open(account_data_file, "w") as f:
        json.dump(accounts, f)

    await interaction.response.send_message("✅ Account info saved for user.", ephemeral=True)

@bot.tree.command(name="creates", description="🎉 Boost / Invite plan server creator")
async def creates(interaction: discord.Interaction):
    class PlanSelect(discord.ui.Select):
        def __init__(self):
            opts = [
                discord.SelectOption(label="2× Boost (8 GB / 200 % / 30 GB)",  value="b2"),
                discord.SelectOption(label="4× Boost (14 GB / 300 % / 50 GB)", value="b4"),
                discord.SelectOption(label="6× Boost (20 GB / 400 % / 70 GB)", value="b6"),
                discord.SelectOption(label="Invite (14)  (12 GB)",             value="i14"),
                discord.SelectOption(label="Invite (19) (16 GB)",             value="i19"),
                discord.SelectOption(label="Invite (27+)  (20 GB)",           value="i27"),
            ]
            super().__init__(placeholder="Select a plan…", min_values=1, max_values=1, options=opts)

        async def callback(self, i2: discord.Interaction):
            plan = self.values[0]; m = i2.user; g = i2.guild
            allow = False

            if plan.startswith("b"):
                boost_needed = {"b2": 2, "b4": 4, "b6": 6}[plan]
                boost_count = sum(1 for r in m.roles if r.is_premium_subscriber())
                allow = boost_count >= boost_needed
                if not allow:
                    await i2.response.send_message(f"❌ Need {boost_needed} boosts; you have {boost_count}.", ephemeral=True)
                    return
            else:
                invites = await g.invites()
                uses = sum(inv.uses for inv in invites if inv.inviter and inv.inviter.id == m.id)
                needed = {"i14": 14, "i19": 19, "i27": 27}[plan]
                allow = uses >= needed
                if not allow:
                    await i2.response.send_message(f"❌ Need {needed}+ invites; you have {uses}.", ephemeral=True)
                    return

                # Role check
                I14 = 1393617300330123274
                I19 = 1393617394806820965
                I27 = 1393617507931259042
                rmap = {"i14": I14, "i19": I19, "i27": I27}
                needed_role = rmap[plan]
                if needed_role not in [r.id for r in m.roles]:
                    await i2.response.send_message("❌ You don’t have the required invite role.", ephemeral=True)
                    return

            await i2.response.send_message("⏳ Creating your server… check DM soon.", ephemeral=True)

            conf = {
                "b2":  (8196, 200,  20796),
                "b4":  (14976, 300, 30755),
                "b6":  (20768, 400, 40965),
                "i14": (12798, 200, 20796),
                "i19": (16768, 300, 30755),
                "i27": (20768, 400, 40965)
            }
            ram, cpu, disk = conf[plan]

            async def go():
                try:
                    await create_account_and_server(m, ram, cpu, disk)
                except Exception as e:
                    await m.send(f"❌ Internal error:\n```{e}```")
            asyncio.create_task(go())

    class V(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.add_item(PlanSelect())

    embed = discord.Embed(
        title="📦 Select Your Plan: Invite / Boost",
        description="Choose one of the available server plans to get started.",
        color=discord.Color.blurple()
    )
    embed.set_image(url="https://www.imghippo.com/i/bRzC6045UZ.png")
    embed.set_thumbnail(url="https://www.imghippo.com/i/PXAV9041Yyw.png")

    await interaction.response.send_message(embed=embed, view=V())

# -------------------- /multiple - Simple Multiplication Solver --------------------
@bot.tree.command(name="multiple", description="✖️ Multiply two numbers (admin + users)")
@app_commands.describe(a="First number", b="Second number")
async def multiple(interaction: discord.Interaction, a: int, b: int):
    await interaction.response.send_message(f"{a} × {b} = **{a * b}**", ephemeral=True)


@bot.tree.command(name="nodes", description="📊 Node dashboard")
async def nodes(interaction: discord.Interaction):
    await interaction.response.defer()
    headers = {"Authorization": f"Bearer {PANEL_API_KEY}", "Accept": "application/json"}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as ses:
        try:
            r = await ses.get(f"{PANEL_URL}/api/application/nodes", headers=headers)
            raw = await r.json()
        except Exception as e:
            await interaction.followup.send(f"⚠️ Panel timeout: {e}");  return

    emb = discord.Embed(
        title="🛡️ DragonCloud • Node Status",
        description=f"⌚ Last check: <t:{int(datetime.datetime.utcnow().timestamp())}:R>",
        color=0x5865f2
    )

    for node in raw["data"][:10]:              # show max 10
        a = node["attributes"]
        status = "🟢 Online" if a["public"] else "⏱ Timeout"
        emb.add_field(
            name=f"{a['name']} (ID {a['id']}) – {status}",
            value=(f"FQDN: `{a['fqdn']}:443`\n"
                   f"RAM: {a['allocated_resources']['memory']:,}/{a['memory']:,} MB\n"
                   f"Disk: {a['allocated_resources']['disk']:,}/{a['disk']:,} MB"),
            inline=False
        )
    await interaction.followup.send(embed=emb)

# ---------------- Helpers: Pterodactyl API ----------------
async def api_get(path: str):
    if not config.get("api_key") or not config.get("panel_url"):
        raise RuntimeError("Panel URL or API key not configured. Use /dashpanel (admin).")
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    url = config["panel_url"].rstrip("/") + path
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers, timeout=15) as r:
            text = await r.text()
            try:
                data = json.loads(text)
            except Exception:
                data = text
            return r.status, data


async def api_post(path: str, payload):
    if not config.get("api_key") or not config.get("panel_url"):
        raise RuntimeError("Panel URL or API key not configured. Use /dashpanel (admin).")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    url = config["panel_url"].rstrip("/") + path
    async with aiohttp.ClientSession() as s:
        async with s.post(url, headers=headers, json=payload, timeout=30) as r:
            text = await r.text()
            try:
                data = json.loads(text)
            except Exception:
                data = text
            return r.status, data


# fetch user id by email (application API)
async def get_user_id_by_email(email: str) -> Optional[int]:
    status, data = await api_get("/api/application/users")
    if status != 200:
        raise RuntimeError(f"Failed to fetch users: {data}")
    for u in data.get("data", []):
        if u["attributes"]["email"].lower() == email.lower():
            return u["attributes"]["id"]
    return None


# create panel user (admin application API)
async def create_panel_user(username: str, email: str, password: str):
    payload = {
        "username": username,
        "email": email,
        "first_name": username,
        "last_name": "User",
        "password": password,
        "root_admin": False,
        "language": "en"
    }
    status, data = await api_post("/api/application/users", payload)
    return status, data


# create server on panel (application API)
async def create_panel_server(server_name: str, user_id: int, egg: int, node: int, memory: int, cpu: int, disk: int, startup=None):
    if startup is None:
        startup = "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar server.jar nogui"
    payload = {
        "name": server_name,
        "user": user_id,
        "egg": egg,
        "docker_image": "ghcr.io/pterodactyl/yolks:java_17",
        "startup": startup,
        "limits": {"memory": memory, "swap": 0, "disk": disk, "io": 500, "cpu": cpu},
        "feature_limits": {"databases": 0, "backups": 0, "allocations": 1},
        "environment": {"SERVER_JARFILE": "server.jar", "VERSION": "latest", "TYPE": "paper"},
        "deploy": {"locations": [node], "dedicated_ip": False, "port_range": []},
        "start_on_completion": True
    }
    status, data = await api_post("/api/application/servers", payload)
    return status, data


# ---------------- Admin command: set panel URL + API key ----------------
@bot.tree.command(name="dashpanel", description="(Admin) Set Panel URL and Admin API key for DragonCloud")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(panel_url="Panel base URL (e.g. https://dragoncloud.godanime.net)", api_key="Application API Key")
async def dashpanel(interaction: discord.Interaction, panel_url: str, api_key: str):
    await interaction.response.defer(ephemeral=True)
    config["panel_url"] = panel_url.strip()
    config["api_key"] = api_key.strip()
    save_config(config)
    await interaction.followup.send("✅ Panel URL and API key saved.", ephemeral=True)


# show saved config (admin)
@bot.tree.command(name="dashboard", description="Show saved panel config (admins see details, users get actions)")
async def dashboard(interaction: discord.Interaction):
    # For admins, show config. For users, show interactive panel (Create Account / Create Server)
    if interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🛠 DragonCloud Panel Config",
                description=f"**Panel URL:** `{config.get('panel_url')}`\n**API Key:** `{'SET' if config.get('api_key') else 'NOT SET'}`",
                color=discord.Color.blurple()
            ),
            ephemeral=True
        )
        return

    # User interactive dashboard
    view = discord.ui.View(timeout=120)

    async def create_account_cb(i: discord.Interaction):
        # show modal for email + password
        class AccountModal(discord.ui.Modal, title="Create Panel Account"):
            email = discord.ui.TextInput(label="Email", style=discord.TextStyle.short, required=True)
            password = discord.ui.TextInput(label="Password", style=discord.TextStyle.short, required=True, min_length=8)

            async def on_submit(self, modal_i: discord.Interaction):
                await modal_i.response.defer(ephemeral=True)
                try:
                    username = self.email.value.split("@")[0]
                    status, data = await create_panel_user(username, self.email.value, self.password.value)
                    if status in (200, 201):
                        # find created user id if present
                        user_id = None
                        if isinstance(data, dict):
                            user_id = data.get("attributes", {}).get("id") or data.get("data", {}).get("attributes", {}).get("id")
                        await modal_i.followup.send("✅ Account created! Check your DMs.", ephemeral=True)
                        try:
                            await modal_i.user.send(f"✅ Panel account created.\nPanel: {config.get('panel_url')}\nEmail: `{self.email.value}`\nPassword: `{self.password.value}`")
                        except discord.Forbidden:
                            await modal_i.followup.send("⚠️ Could not DM you — please enable DMs.", ephemeral=True)
                    else:
                        await modal_i.followup.send(f"❌ Failed to create account:\n```{data}```", ephemeral=True)
                except Exception as e:
                    await modal_i.followup.send(f"❌ Error: {e}", ephemeral=True)

        await i.response.send_modal(AccountModal())

    async def create_server_cb(i: discord.Interaction):
        # Show select menus / inputs via a modal or series of selects.
        # We'll send an ephemeral message with a View that contains selects:
        class ServerView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)

                # preset options
                self.add_item(discord.ui.Select(
                    placeholder="Select RAM (MB) — max 4096",
                    options=[
                        discord.SelectOption(label="1 GB", value="1024"),
                        discord.SelectOption(label="2 GB", value="2048"),
                        discord.SelectOption(label="3 GB", value="3072"),
                        discord.SelectOption(label="4 GB", value="4096")
                    ],
                    custom_id="ram_select"
                ))

                self.add_item(discord.ui.Select(
                    placeholder="Select CPU (%) — max 200",
                    options=[
                        discord.SelectOption(label="50%", value="50"),
                        discord.SelectOption(label="100%", value="100"),
                        discord.SelectOption(label="150%", value="150"),
                        discord.SelectOption(label="200%", value="200")
                    ],
                    custom_id="cpu_select"
                ))

                self.add_item(discord.ui.Select(
                    placeholder="Select Disk (MB) — max 10240",
                    options=[
                        discord.SelectOption(label="5 GB", value="5120"),
                        discord.SelectOption(label="10 GB", value="10240")
                    ],
                    custom_id="disk_select"
                ))

                self.add_item(discord.ui.Select(
                    placeholder="Select Egg",
                    options=[
                        discord.SelectOption(label="Paper (recommended)", value="paper"),
                        discord.SelectOption(label="Villager", value="villager")
                    ],
                    custom_id="egg_select"
                ))

            @discord.ui.button(label="Continue", style=discord.ButtonStyle.success)
            async def continue_btn(self, button_i: discord.Interaction, _):
                # collect the selected options from message components
                msg = button_i.message
                selects = [c for c in msg.components[0].children] if msg.components else []
                # simpler: ask for server name and email via a modal now
                class ServerCreateModal(discord.ui.Modal, title="Server Details"):
                    server_name = discord.ui.TextInput(label="Server name", required=True, max_length=32)
                    owner_email = discord.ui.TextInput(label="Your panel email", required=True)

                    async def on_submit(self, modal_i: discord.Interaction):
                        await modal_i.response.defer(ephemeral=True)
                        try:
                            # read selections from the original message (component values)
                            parent_msg = await modal_i.channel.fetch_message(msg.id)
                            comp_values = {}
                            for row in parent_msg.components:
                                for child in row.children:
                                    if isinstance(child, discord.ui.Select):
                                        comp_values[child.custom_id] = child.values[0] if child.values else None

                            ram = int(comp_values.get("ram_select", "1024"))
                            cpu = int(comp_values.get("cpu_select", "100"))
                            disk = int(comp_values.get("disk_select", "5120"))
                            egg_choice = comp_values.get("egg_select", "paper")
                            egg_id = 1 if egg_choice == "paper" else 2  # adjust egg ids to your panel

                            # validate limits
                            if ram > 4096 or cpu > 200 or disk > 10240:
                                await modal_i.followup.send("❌ Selected resources exceed allowed maximums.", ephemeral=True)
                                return

                            # find or create user by email
                            user_id = await get_user_id_by_email(self.owner_email.value)
                            if not user_id:
                                # create a temporary account if user not found (use random password)
                                temp_pass = "TempPass123!"
                                st, dd = await create_panel_user(self.owner_email.value.split("@")[0], self.owner_email.value, temp_pass)
                                if st not in (200, 201):
                                    await modal_i.followup.send(f"❌ Failed to create panel account:\n```{dd}```", ephemeral=True)
                                    return
                                # try fetch user id again
                                user_id = await get_user_id_by_email(self.owner_email.value)
                                # DM user credentials
                                try:
                                    await modal_i.user.send(f"✅ Panel account created for `{self.owner_email.value}`\nPassword: `{temp_pass}`\nPanel: {config.get('panel_url')}")
                                except discord.Forbidden:
                                    await modal_i.followup.send("⚠️ Could not DM the user the account credentials.", ephemeral=True)

                            # create server in background
                            async def bg_create():
                                try:
                                    st2, d2 = await create_panel_server(self.server_name.value, user_id, egg_id, node=1, memory=ram, cpu=cpu, disk=disk)
                                    if st2 in (200, 201):
                                        try:
                                            await modal_i.user.send(f"✅ Server `{self.server_name.value}` created!\nPanel: {config.get('panel_url')}")
                                        except:
                                            pass
                                    else:
                                        try:
                                            await modal_i.user.send(f"❌ Server creation failed:\n```{d2}```")
                                        except:
                                            pass
                                except Exception as ee:
                                    try:
                                        await modal_i.user.send(f"❌ Background error: {ee}")
                                    except:
                                        pass

                            asyncio.create_task(bg_create())
                            await modal_i.followup.send("⏳ Server is being created in the background — you'll get a DM when ready.", ephemeral=True)
                        except Exception as e:
                            await modal_i.followup.send(f"❌ Error: {e}", ephemeral=True)

                await button_i.response.send_modal(ServerCreateModal())

        await i.response.send_message("📦 Choose resources for your free server (you will continue to enter name & email)...", view=ServerView(), ephemeral=True)

    b1 = discord.ui.Button(label="Create Account", style=discord.ButtonStyle.blurple)
    b2 = discord.ui.Button(label="Create Server", style=discord.ButtonStyle.green)

    async def b1_cb(interaction_btn: discord.Interaction):
        await create_account_cb(interaction_btn)

    async def b2_cb(interaction_btn: discord.Interaction):
        await create_server_cb(interaction_btn)

    b1.callback = b1_cb
    b2.callback = b2_cb

    view.add_item(b1)
    view.add_item(b2)

    await interaction.response.send_message("Welcome to DragonCloud Dashboard — choose an option:", view=view, ephemeral=True)


# ---------------- Admin createserver manual command (slash) ----------------
@bot.tree.command(name="createserver", description="(Admin) Create server for given owner email")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(server_name="Server name", owner_email="Owner email", node="Node ID", cpu="CPU %", memory="Memory MB", disk="Disk MB", egg="Egg ID")
async def createserver(interaction: discord.Interaction, server_name: str, owner_email: str, node: int, cpu: int, memory: int, disk: int, egg: int):
    await interaction.response.defer(ephemeral=True)
    if memory > 99000 or cpu > 9000 or disk > 2510240:
        await interaction.followup.send("❌ Resource values exceed allowed maximums.", ephemeral=True)
        return
    user_id = await get_user_id_by_email(owner_email)
    if not user_id:
        await interaction.followup.send("❌ Owner not found on panel by that email.", ephemeral=True)
        return
    st, data = await create_panel_server(server_name, user_id, egg, node, memory, cpu, disk)
    if st in (200, 201):
        await interaction.followup.send(f"✅ Server `{server_name}` created (owner `{owner_email}`).", ephemeral=True)
        # DM owner if possible
        try:
            # best effort: try to find discord user by email is not possible reliably; we simply notify the admin
            pass
        except:
            pass
    else:
        await interaction.followup.send(f"❌ Failed: {data}", ephemeral=True)


# ---------------- DM utility (admin only) ----------------
@bot.tree.command(name="dm", description="(Admin) Send DM to a user")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(target="User to DM", message="Message to send")
async def dm_cmd(interaction: discord.Interaction, target: discord.User, message: str):
    await interaction.response.defer(ephemeral=True)
    try:
        await target.send(message)
        await interaction.followup.send("✅ DM sent.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ Cannot DM that user.", ephemeral=True)

# ✅ /serverinfo command
@bot.tree.command(name="serverinfo", description="Show server info in green embed")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(
        title="📡 Server Information",
        color=discord.Color.green()
    )
    embed.add_field(name="👑 Server Owner", value=f"{guild.owner}", inline=True)
    embed.add_field(name="🆔 Owner ID", value=f"{guild.owner.id}", inline=True)
    embed.add_field(name="📶 Ping", value=f"{round(bot.latency * 1000)} ms", inline=True)
    embed.add_field(name="👥 Members", value=f"{guild.member_count}", inline=True)
    embed.set_footer(text="Bot Dev. Gamerzhacker | Bot Version 2.70")
    await interaction.response.send_message(embed=embed)

# ===== COMMAND: Create User =====
@tree.command(name="create", description="Create a Pterodactyl user (Admin only).")
@app_commands.describe(
    username="Username",
    email="Email",
    password="Password"
)
async def create_user(interaction: discord.Interaction, username: str, email: str, password: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)

    await interaction.response.send_message("🛠 Creating user... Please wait...", ephemeral=True)

    payload = {
        "username": username,
        "email": email,
        "first_name": username,
        "last_name": "User",
        "password": password,
        "root_admin": False,
        "language": "en"
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{PANEL_URL}/api/application/users", json=payload, headers=headers) as resp:
                data = await resp.json()
                if resp.status == 201:
                    await interaction.user.send(f"✅ User '{username}' created!\nEmail: {email}\nPassword: {password}\nPanel: {PANEL_URL}")
                else:
                    await interaction.user.send(f"❌ Failed to create user: {data}")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
        
bot.run(TOKEN)
