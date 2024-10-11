import docker, discord, asyncio, config
from mcrcon import MCRcon
from discord.ui import View

class ArkInfo():
    def __init__(self, bot, channel):
        self.bot = bot
        self.channel = channel
        self.container_running = False
        self.ark_ping = False
        self.players = []
        self.message = "Standby..."
        self.view = ArkControlView(self)
        self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        self.container = self.client.containers.get(config.ARK_CONTAINER_NAME)
        self.bot.loop.create_task(self.container_manager())
        self.bot.loop.create_task(self.ping_manager())
        self.bot.loop.create_task(self.message_manager())

    async def message_manager(self):
        while True:
            ping_color = "🟢" if self.ark_ping else "🔴"
            container_color = "🟢" if self.container_running else "🔴"
            online = len(self.players)
            self.message = (
            "ARK Server Status\n"
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
                f"Pass: {config.ARK_SERVER_PASS}"
            )
            await asyncio.sleep(5)

    async def container_manager(self):
        while True:
            try:
                self.container = self.client.containers.get(config.ARK_CONTAINER_NAME)
                if self.container.status == 'running':
                    self.container_running = True
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
                else:
                    self.container_running = False
            except:
                self.container_running = False
            await asyncio.sleep(5)

    async def ping_manager(self):
        command = ['ping', config.ARK_CONTAINER_IP, '-c', '1', '-W', '1']
        while True:
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
            await asyncio.sleep(5)

    async def loop(self):
        await self.channel.purge(limit=None)
        message_instance = await self.channel.send(content=f"```{self.message}```", view=self.view)
        while True:
            if self.message != str(message_instance.content):
                self.view.update_button_states()
                await message_instance.edit(content=f"```{self.message}```", view=self.view)
            await asyncio.sleep(2)

    @classmethod
    async def start_loop(cls, bot, channel):
        instance = cls(bot, channel)
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
        # Logic to start the ARK server container
        arkadmin_role = discord.utils.get(interaction.user.roles, name="arkadmin")
        if not arkadmin_role:
            return await interaction.response.send_message("you dont have the right, ooooooo you dont have the right", ephemeral=True, delete_after=5)
        await interaction.response.send_message(f"Starting the ARK server...", delete_after=5)
        await asyncio.to_thread(self.ark_info.container.start)

    async def stop_button_callback(self, interaction):
        # Logic to stop the ARK server container
        arkadmin_role = discord.utils.get(interaction.user.roles, name="arkadmin")
        if not arkadmin_role:
            return await interaction.response.send_message("you dont have the right, ooooooo you dont have the right", ephemeral=True, delete_after=5)
        self.ark_info.players_running = False
        await interaction.response.send_message(f"Stopping the ARK server...", delete_after=5)
        await asyncio.to_thread(self.ark_info.container.stop)

    async def wipe_dinos_callback(self, interaction):
        arkadmin_role = discord.utils.get(interaction.user.roles, name="arkadmin")
        if not arkadmin_role:
            return await interaction.response.send_message("you dont have the right, ooooooo you dont have the right", ephemeral=True, delete_after=5)
        # Logic to wipe the dino data
        command = "destroywilddinos"
        ArkRcon.send_command(command)
        command = "ServerChat No Dinos?"
        ArkRcon.send_command(command)
        await interaction.response.send_message(f"Wiping Wild Dinos...", delete_after=5)

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
            print("Connection Refused, is the server running or just boot up?", flush=True)
            return None
        except Exception as e:
            print(f"Error executing RCON command: {e}, is the server running or just booting up?", flush=True)
            return None
    