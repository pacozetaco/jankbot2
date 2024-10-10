import config, discord, os, utils.ark.config_uploader as config_uploader
from discord.ext import commands
from utils.ark.arkinfo import ArkInfo

class JankBot(commands.Bot):
    def __init__(self):
            #command prefix for all commands is !
            super().__init__(
                command_prefix="!",
                intents=discord.Intents.all()
            )
    #load cogs
    async def setup_hook(self):
        cog_path = './cogs'
        for filename in os.listdir(cog_path):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}') 
                print(f"loaded {filename}")
                
    async def on_message(self, message):
        if message.author.bot:
            return  # Ignore messages from itself and bots/system msgs
        if message.channel.id == int(config.ARK_CONFIG_CHANNEL):
            await config_uploader.upload_config(message)
        await self.process_commands(message)
    
    async def on_ready(self):
        #READY
        print(f"Logged in as {self.user}", flush=True)

        #ARK STATUS CHANNEL BOOT
        channel = self.get_channel(int(config.ARK_STATUS_CHANNEL))
        print(channel)
        await channel.purge(limit=None)
        ArkInfo(self, channel)


# Start the bot
if __name__ == "__main__":
    JankBot().run(config.DISCORD_TOKEN)
