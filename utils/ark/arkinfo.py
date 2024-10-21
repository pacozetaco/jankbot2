import docker, discord, asyncio, config
from mcrcon import MCRcon
from discord.ui import View

class ArkInfo():
    def __init__(self, bot, channel, chat_channel):
       # print("Initializing ArkInfo class...", flush=True)
        self.bot = bot
        self.channel = channel
        self.chat_channel = chat_channel
        self.container_running = False
        self.ark_ping = False
        self.players = []
        self.message = None
        self.view = ArkControlView(self)
      #  print("Creating Docker client...", flush=True)
        self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
      #  print("Getting container instance...", flush=True)
        self.container = self.client.containers.get(config.ARK_CONTAINER_NAME)
        self.bot.loop.create_task(self.container_manager())

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
       # print("message_manager Updating message...", flush=True)

    async def container_manager(self):
        while True:
            try:
                self.container = self.client.containers.get(config.ARK_CONTAINER_NAME)
                if self.container.status == 'running':
                    self.container_running = True
               #     print("Container running, checking players...", flush=True)
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
                    if chat_messages != 'Server received, But no response!! \n ' and not chat_messages.startswith('SERVER:') and not chat_messages == None:
               #         print("Sending chat messages...", flush=True)
                        await self.chat_channel.send(chat_messages) 
                else:
                    self.container_running = False
              #      print("Container not running...", flush=True)
            except Exception as e:
                print(f"Error in container manager: {e}", flush=True)
            await asyncio.sleep(3)

    async def ping_manager(self):
        command = ['ping', config.ARK_CONTAINER_IP, '-c', '1', '-W', '1']
        if self.container_running:
        #    print("Pinging container...", flush=True)
            ping = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await ping.wait()
            self.ark_ping = ping.returncode == 0
        else:
            self.ark_ping = False
     #   print("Pinging result:", self.ark_ping, flush=True)

    async def loop(self):
     #   print("Starting loop...", flush=True)
        await self.channel.purge(limit=None)
        self.message_instance = await self.channel.send(content=f"{self.message}", view=self.view)
        while True:
            self.message_manager()
            await self.ping_manager()
            if str(self.message) != str(self.message_instance.content):
                self.view.update_button_states()
                self.message_instance = await self.message_instance.edit(content=self.message, view=self.view)
         #       print("def loop Message updated...", flush=True)
            await asyncio.sleep(5)

    @classmethod
    async def start_loop(cls, bot, channel, chat_channel):
      #  print("Starting ArkInfo instance...", flush=True)
        instance = cls(bot, channel, chat_channel)
        await instance.loop()

class ArkControlView(View):
    def __init__(self, ark_info):
        super().__init__(timeout=None)
     #   print("Creating ArkControlView instance...", flush=True)
        self.ark_info = ark_info

        self.start_button = discord.ui.Button(label="Start", style=discord.ButtonStyle.green)
        self.stop_button = discord.ui.Button(label="Stop", style=discord.ButtonStyle.red)
        self.wipe_dinos = discord.ui.Button(label="Wipe Dinos", style=discord.ButtonStyle.blurple)
        self.start_button.callback = self.start_button_callback
        self.stop_button.callback = self.stop_button_callback
        self.wipe_dinos.callback = self.wipe_dinos_callback
      #  print("Adding buttons to view...", flush=True)
        self.add_item(self.start_button)
        self.add_item(self.stop_button)
        self.add_item(self.wipe_dinos)

    def update_button_states(self):
        self.start_button.disabled = self.ark_info.container_running
        self.wipe_dinos.disabled = not self.ark_info.container_running
        self.stop_button.disabled = not self.ark_info.container_running


    async def start_button_callback(self, interaction):
     #  print("Starting button callback...", flush=True)
        arkadmin_role = discord.utils.get(interaction.user.roles, name="arkadmin")
        if not arkadmin_role:
            return await interaction.response.send_message("you dont have the right, ooooooo you dont have the right", ephemeral=True, delete_after=5)
      #  print("Starting server...", flush=True)
        await interaction.response.send_message(f"Starting the ARK server...",ephemeral=True, delete_after=5)
        await asyncio.to_thread(self.ark_info.container.start)

    async def stop_button_callback(self, interaction):
      #  print("Stopping button callback...", flush=True)
        arkadmin_role = discord.utils.get(interaction.user.roles, name="arkadmin")
        if not arkadmin_role:
            return await interaction.response.send_message("you dont have the right, ooooooo you dont have the right", ephemeral=True, delete_after=5)
      #  print("Stopping server...", flush=True)
        await interaction.response.send_message(f"Stopping the ARK server...Give this a sec, takes a bit.",ephemeral=True, delete_after=15)
        await asyncio.to_thread(self.ark_info.container.stop)

    async def wipe_dinos_callback(self, interaction):
     #   print("Wipe dino button callback...", flush=True)
        arkadmin_role = discord.utils.get(interaction.user.roles, name="arkadmin")
        if not arkadmin_role:
            return await interaction.response.send_message("you dont have the right, ooooooo you dont have the right", ephemeral=True, delete_after=5)
      #  print("Wiping dino...", flush=True)
        rcon = ArkRcon("destroywilddinos")
        rcon.execute_command()
        rcon = ArkRcon("ServerChat No Dinos?")
        rcon.execute_command()
        await interaction.response.send_message(f"Wiping Wild Dinos...",ephemeral=True, delete_after=5)

class ArkRcon():
    def __init__(self, command):
       # print("Creating ArkRcon instance...", flush=True)
        self.command = command
        self.RCON_HOST = str(config.ARK_RCON_HOST)
        self.RCON_PORT = int(config.ARK_RCON_PORT)
        self.RCON_PASSWORD = str(config.ARK_ADMIN_PW)

    def execute_command(self):
        try:
         #   print("Executing RCON command...", flush=True)
            with MCRcon(self.RCON_HOST, self.RCON_PASSWORD, self.RCON_PORT) as mcr:
                reply = mcr.command(self.command)
                return reply
        except ConnectionRefusedError:
         #   print(f"Connection Refused: {self.RCON_HOST}", flush=True)
            return None
        except Exception as e:
          #  print(f"Error executing RCON command: {e}", flush=True)
            return None
