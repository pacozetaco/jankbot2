import config, discord, utils.ark.config_uploader as config_uploader 
from discord.ext import commands
from utils.ark.arkinfo import ArkInfo, ArkRcon
class JankBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all()
        )
    #load cogs
    async def setup_hook(self):
        await self.load_extension('cogs.pitboss')
        opus_path = '/usr/lib/libopus.so.0.10.1'  # apk add --no-cache opus-dev
        discord.opus.load_opus(opus_path)
    async def on_message(self, message):
        if message.author.bot:
            return 
        if message.channel.id == int(config.ARK_CONFIG_CHANNEL):
            await config_uploader.upload_config(message)
        if message.channel.id == int(config.ARK_CHAT_CHANNEL):
            rcon = ArkRcon(f"ServerChat {str(message.author)} {str(message.content)}")
            rcon.execute_command()
        await self.process_commands(message)

    async def on_ready(self):
        print(f"Logged in as {self.user}", flush=True)

        # Attempt to initialize ArkInfo
        try:
            chat_channel = self.get_channel(int(config.ARK_CHAT_CHANNEL))
            channel = self.get_channel(int(config.ARK_STATUS_CHANNEL))
            await channel.purge(limit=None)
            self.loop.create_task(ArkInfo.start_loop(self, channel, chat_channel))
            print("Loaded ArkInfo", flush=True)
        except Exception as e:
            print(f"Error initializing ArkInfo: {e}", flush=True)

        # Attempt to initialize Jukebox
        try:
            jukebox_channel = self.get_channel(int(config.JUKEBOX_INFO_CHANNEL))
            from cogs import jukebox
            print("Loaded jukebox cog", flush=True)
            self.loop.create_task(jukebox.setup(self, jukebox_channel))
        except Exception as e:
            print(f"Error initializing Jukebox: {e}", flush=True)


#main entry
if __name__ == "__main__":
    JankBot().run(config.DISCORD_TOKEN)
