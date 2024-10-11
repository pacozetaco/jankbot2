import config, discord, os, utils.ark.config_uploader as config_uploader 
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
        cog_path = './cogs'
        for filename in os.listdir(cog_path):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}') 
                
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
        #get ark chat channel and ark info channel
        try:
            chat_channel = self.get_channel(int(config.ARK_CHAT_CHANNEL))
            channel = self.get_channel(int(config.ARK_STATUS_CHANNEL))
            await channel.purge(limit=None)
            await ArkInfo.start_loop(self, channel, chat_channel)
        except Exception as e:
            print(e)
#main entry
if __name__ == "__main__":
    JankBot().run(config.DISCORD_TOKEN)
