import config, discord, utils.ark.config_uploader as config_uploader 
from discord.ext import commands
from utils.ark.arkinfo import ArkInfo, ArkRcon
from games.baccarat import BaccaratManager
from utils.aichat import process_ai_request
#testing new shit
class JankBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all()
        )

    #load cogs
    async def setup_hook(self):

        await self.load_extension('cogs.pitboss')
        opus_path = '/usr/lib/libopus.so.0.10.1'  
        try:
            discord.opus.load_opus(opus_path)
        except Exception as e:
            print(f"Error loading Opus: {e}", flush=True)


    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message) 
        if message.channel.name == "ai-chat":
            await process_ai_request(message)
        if message.channel.id == int(config.ARK_CONFIG_CHANNEL):
            await config_uploader.upload_config(message)
        if message.channel.id == int(config.ARK_CHAT_CHANNEL):
            rcon = ArkRcon(f"ServerChat {str(message.author)} {str(message.content)}")
            rcon.execute_command()
    
    async def on_ready(self):
        print("Logged in as", self.user, flush=True)
        # Attempt to initialize ArkInfo
        try:
            chat_channel = self.get_channel(int(config.ARK_CHAT_CHANNEL))
            channel = self.get_channel(int(config.ARK_STATUS_CHANNEL))
            if channel != None and chat_channel != None:
                await channel.purge(limit=None)
                self.loop.create_task(ArkInfo.start_loop(self, channel, chat_channel))
            else:
                print("Failed to initialize ArkInfo: Channels not found", flush=True)
        except Exception as e:
            print(f"Error initializing ArkInfo: {e}", flush=True)
        
        # guilds = self.guilds
        # for guild in guilds:
        #     for channel in guild.channels:
        #         if channel.name.lower().startswith("baccarat"):
        #             self.loop.create_task(BaccaratManager.start_manager(self, channel))
    
        # Attempt to initialize Jukebox
        try:
            jukebox_channel = self.get_channel(int(config.JUKEBOX_INFO_CHANNEL))
            if jukebox_channel != None:
                from cogs import jukebox
                self.loop.create_task(jukebox.setup(self, jukebox_channel))
            else:
                print("Failed to initialize Jukebox: Channel not found", flush=True)
        except Exception as e:
            print(f"Error initializing Jukebox: {e}", flush=True)

#main entry
if __name__ == "__main__":
    JankBot().run(config.DISCORD_TOKEN)
    print("Bot started successfully", flush=True)