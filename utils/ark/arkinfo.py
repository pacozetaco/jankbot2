import docker, discord, asyncio, config
from mcrcon import MCRcon
from discord.ui import View

class ArkInfo():
    def __init__(self, bot, channel):
        self.bot = bot
        self.channel = channel
        self.container_running = False
        self.ping = False
        self.message_instance = None
        self.last_status_message = None
        self.status_message = "Standby..."
        self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        self.view = ArkControlView(self)
        self.bot.loop.create_task(self.check_container_status())

    async def check_container_status(self):
        if self.message_instance == None:
            await self.channel.purge(limit=None)
            self.message_instance = await self.channel.send(self.status_message)
        while True:
            try:
                self.container = self.client.containers.get(config.ARK_CONTAINER_NAME)
                self.container_running = self.container.status == 'running'
            except docker.errors.NotFound:
                self.container_running = False
            except Exception as e:
                print(e)
                self.container_running = False
            command = ['ping', config.ARK_CONTAINER_IP, '-c', '1', '-W', '1']
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
                self.ping = process.returncode == 0
            except Exception as e:
                self.ping = False
                print(e)
            await self.send_status_message()
            #print("sleeping for 5 seconds...", flush=True)
            await asyncio.sleep(10)

    async def send_status_message(self):
        # Determine the status colors
        players = None
        rcon = ArkRcon("ListPlayers")
        if self.ping and self.container_running:
            players = rcon.execute_command()
        i = 1
        playerlist = []
        if players:
            for player in players.split("\n"):
                if player.strip():
                    player_info = player.split(". ")
                    if len(player_info) > 1:
                        player_name = player_info[1].split(",")[0]
                        playerlist.append(f"{i}. {player_name}")
                        i += 1
        online = i-1
        ping_color = "🟢" if self.ping else "🔴"
        container_color = "🟢" if self.container_running else "🔴"
        self.status_message = (
            "ARK Server Status\n"
            "----------------\n"
            f"{'Ping:':<7} {ping_color}\n"
            f"{'Server:':<4} {container_color}\n\n"
            f"{online} Players Online\n"
            "----------------\n"
            )
        if playerlist:
            self.status_message += "\n".join(playerlist)
        if self.status_message != self.last_status_message:
            self.last_status_message = self.status_message
            self.view.update_button_states()
            await self.message_instance.edit(view=self.view, content=f"```{self.status_message}```")

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
        await interaction.response.send_message(f"Starting the ARK server...", delete_after=5)
        self.start_button.disabled = True
        await interaction.message.edit(view=self)
        self.ark_info.container.start()

    async def stop_button_callback(self, interaction):
        # Logic to stop the ARK server container
        await interaction.response.send_message(f"Stopping the ARK server...", delete_after=5)
        self.stop_button.disabled = True
        self.wipe_dinos.disabled = True
        await interaction.message.edit(view=self)
        self.ark_info.container.stop()

    async def wipe_dinos_callback(self, interaction):
        # Logic to wipe the dino data
        command = "destroywilddinos"
        ArkRcon.send_command(command)
        command = "ServerChat No Dinos?"
        ArkRcon.send_command(command)
        await interaction.response.send_message(f"Wiping Wild Dinos...", delete_after=5)
        

class ArkRcon:
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
            print("RCON connection refused. Check server settings.", flush=True)
            return None
        except Exception as e:
            print(f"Error executing RCON command: {e}", flush=True)
            return None
        

