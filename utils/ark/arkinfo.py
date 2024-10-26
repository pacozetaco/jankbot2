import discord, asyncio, config
from mcrcon import MCRcon
from discord.ui import View
import aiodocker

class ArkInfo():
    def __init__(self, bot, channel, chat_channel):
        self.bot = bot
        self.channel = channel
        self.chat_channel = chat_channel
        self.container_running = False
        self.ark_ping = False
        self.players = []
        self.message = None
        self.view = ArkControlView(self)
        self.bot.loop.create_task(self.container_manager())
        self.DOCKER_CLIENT = aiodocker.Docker()

    def message_manager(self):
        ping_color = "🟢" if self.ark_ping else "🔴"
        container_color = "🟢" if self.container_running else "🔴"
        online = len(self.players)
        self.message = (
        "```ARK Server Status\n"
        "----------------\n"
        f"{'Ping:':<7} {ping_color}\n"
        f"{'Server:':<4} {container_color}\n\n"
        f"{online} Players Online\n"
        "----------------\n"
        )
        if self.players:
            self.message += "\n".join(self.players)
        self.message += (
            "\n\nARK Server Info\n"
            "----------------\n"
            f"Name: {config.ARK_SERVER_NAME}\n"
            f"Pass: {config.ARK_SERVER_PASS}```"
        )

    async def container_manager(self):
        CONTAINER = await self.DOCKER_CLIENT.containers.get(config.ARK_CONTAINER_NAME)
        while True:
            try:
                self.container_running = (await CONTAINER.show())['State']['Running']
                if self.container_running:
                    rcon = ArkRcon("ListPlayers")
                    player_output = rcon.execute_command()
                    self.players.clear()
                    if player_output != None:
                        i = 1
                        for player in player_output.split("\n"):
                            if player.strip():
                                player_info = player.split(". ")
                                if len(player_info) > 1:
                                    player_name = player_info[1].split(",")[0]
                                    self.players.append(f"{i}. {player_name}")
                                    i += 1
               #     print("Players updated...", flush=True)
                    rcon = ArkRcon("GetChat")
                    chat_messages = rcon.execute_command()
                    if not chat_messages == None and chat_messages != 'Server received, But no response!! \n ' and not chat_messages.startswith('SERVER:'):
                        await self.chat_channel.send(chat_messages) 
                else:
                    self.container_running = False
            except Exception as e:
                print(f"Error in container manager: {e}", flush=True)
            await asyncio.sleep(3)

    async def ping_manager(self):
        command = ['ping', config.ARK_CONTAINER_IP, '-c', '1', '-W', '1']
        if self.container_running:
            ping = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await ping.wait()
            self.ark_ping = ping.returncode == 0
        else:
            self.ark_ping = False

    async def loop(self):
        await self.channel.purge(limit=None)
        self.message_instance = await self.channel.send(content=f"{self.message}", view=self.view)
        while True:
            self.message_manager()
            await self.ping_manager()
            if str(self.message) != str(self.message_instance.content):
                self.view.update_button_states()
                self.message_instance = await self.message_instance.edit(content=self.message, view=self.view)
            await asyncio.sleep(5)

    @classmethod
    async def start_loop(cls, bot, channel, chat_channel):
        instance = cls(bot, channel, chat_channel)
        await instance.loop()

class ArkControlView(View):
    def __init__(self, ark_info):
        super().__init__(timeout=None)
        self.ark_info = ark_info
        self.start_button = discord.ui.Button(label="Start", style=discord.ButtonStyle.green)
        self.stop_button = discord.ui.Button(label="Stop", style=discord.ButtonStyle.red)
        self.wipe_dinos = discord.ui.Button(label="Wipe Dinos", style=discord.ButtonStyle.blurple)
        self.start_button.callback = self.start_button_callback
        self.stop_button.callback = self.stop_button_callback
        self.wipe_dinos.callback = self.wipe_dinos_callback
        self.add_item(self.start_button)
        self.add_item(self.stop_button)
        self.add_item(self.wipe_dinos)

    def update_button_states(self):
        self.start_button.disabled = self.ark_info.container_running
        self.wipe_dinos.disabled = not self.ark_info.container_running
        self.stop_button.disabled = not self.ark_info.container_running

    async def start_button_callback(self, interaction):
        CONTAINER = await self.ark_info.DOCKER_CLIENT.containers.get(config.ARK_CONTAINER_NAME)
        arkadmin_role = discord.utils.get(interaction.user.roles, name="arkadmin")
        if not arkadmin_role:
            return await interaction.response.send_message("you dont have the right, ooooooo you dont have the right", ephemeral=True, delete_after=5)
        await interaction.response.send_message(f"Starting the ARK server...",ephemeral=True, delete_after=5)
        await CONTAINER.start()

    async def stop_button_callback(self, interaction):
        CONTAINER = await self.ark_info.DOCKER_CLIENT.containers.get(config.ARK_CONTAINER_NAME)
        arkadmin_role = discord.utils.get(interaction.user.roles, name="arkadmin")
        if not arkadmin_role:
            return await interaction.response.send_message("you dont have the right, ooooooo you dont have the right", ephemeral=True, delete_after=5)
        await interaction.response.send_message(f"Stopping the ARK server...Give this a sec, takes a bit.",ephemeral=True, delete_after=15)
        rcon = ArkRcon("saveworld")
        rcon.execute_command()
        await CONTAINER.stop()

    async def wipe_dinos_callback(self, interaction):
        arkadmin_role = discord.utils.get(interaction.user.roles, name="arkadmin")
        if not arkadmin_role:
            return await interaction.response.send_message("you dont have the right, ooooooo you dont have the right", ephemeral=True, delete_after=5)
        rcon = ArkRcon("destroywilddinos")
        rcon.execute_command()
        rcon = ArkRcon("ServerChat No Dinos?")
        rcon.execute_command()
        await interaction.response.send_message(f"Wiping Wild Dinos...",ephemeral=True, delete_after=5)

class ArkRcon():
    def __init__(self, command):
        self.command = command
        self.RCON_HOST = str(config.ARK_RCON_HOST)
        self.RCON_PORT = int(config.ARK_RCON_PORT)
        self.RCON_PASSWORD = str(config.ARK_ADMIN_PW)

    def execute_command(self):
        try:
            with MCRcon(self.RCON_HOST, self.RCON_PASSWORD, self.RCON_PORT) as mcr:
                reply = mcr.command(self.command)
                return reply
        except ConnectionRefusedError:
            return None
        except Exception as e:
            return None
