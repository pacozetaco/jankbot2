import config, discord, utils.ark.config_uploader as config_uploader 
from discord.ext import commands
from utils.ark.arkinfo import ArkInfo, ArkRcon
from games.baccarat import BaccaratManager

print("Importing required modules...", flush=True)
print("Modules imported successfully", flush=True)

class JankBot(commands.Bot):
    print("Creating bot instance...", flush=True)
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all()
        )
        print("Bot initialized successfully", flush=True)
    
    #load cogs
    async def setup_hook(self):
        print("Loading cogs...", flush=True)
        await self.load_extension('cogs.pitboss')
        opus_path = '/usr/lib/libopus.so.0.10.1'  # apk add --no-cache opus-dev
        try:
            discord.opus.load_opus(opus_path)
            print("Opus loaded successfully", flush=True)
        except Exception as e:
            print(f"Error loading Opus: {e}", flush=True)

    async def on_message(self, message):
        if message.author.bot:
            print("Ignoring bot messages...", flush=True)
            return
        print("Processing commands...", flush=True)
        await self.process_commands(message) 
        if message.channel.id == int(config.ARK_CONFIG_CHANNEL):
            print("Uploading config to channel...", flush=True)
            await config_uploader.upload_config(message)
        if message.channel.id == int(config.ARK_CHAT_CHANNEL):
            print("Executing Rcon command...", flush=True)
            rcon = ArkRcon(f"ServerChat {str(message.author)} {str(message.content)}")
            rcon.execute_command()
    
    async def on_ready(self):
        print("Logged in as", self.user, flush=True)
        # Attempt to initialize ArkInfo
        try:
            print("Initializing ArkInfo...", flush=True)
            chat_channel = self.get_channel(int(config.ARK_CHAT_CHANNEL))
            channel = self.get_channel(int(config.ARK_STATUS_CHANNEL))
            if channel != None and chat_channel != None:
                print("ArkInfo initialized successfully", flush=True)
                await channel.purge(limit=None)
                self.loop.create_task(ArkInfo.start_loop(self, channel, chat_channel))
            else:
                print("Failed to initialize ArkInfo: Channels not found", flush=True)
        except Exception as e:
            print(f"Error initializing ArkInfo: {e}", flush=True)
        
        guilds = self.guilds
        for guild in guilds:
            for channel in guild.channels:
                if channel.name.lower().startswith("baccarat"):
                    self.loop.create_task(BaccaratManager.start_manager(self, channel))
        


        # Attempt to initialize Jukebox
        try:
            print("Initializing Jukebox...", flush=True)
            jukebox_channel = self.get_channel(int(config.JUKEBOX_INFO_CHANNEL))
            if jukebox_channel != None:
                from cogs import jukebox
                print("Jukebox initialized successfully", flush=True)
                self.loop.create_task(jukebox.setup(self, jukebox_channel))
            else:
                print("Failed to initialize Jukebox: Channel not found", flush=True)
        except Exception as e:
            print(f"Error initializing Jukebox: {e}", flush=True)


#main entry
print("Running bot with token...", flush=True)
if __name__ == "__main__":
    JankBot().run(config.DISCORD_TOKEN)
    print("Bot started successfully", flush=True)
