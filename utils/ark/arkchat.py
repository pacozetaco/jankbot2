from utils.ark.arkinfo import ArkRcon 
import config, asyncio

class ArkChat():
    def __init__(self, channel, bot):
        self.bot = bot
        self.channel = channel
        self.logged_messages = set()
        self.logged_messages.add('Server received, But no response!! \n ')
        self.bot.loop.create_task(self.log_chat())
        print(self.channel)

    async def get_chat(self):
        rcon = ArkRcon("GetChat")
        results = rcon.execute_command()
        if results:
            return results
    
    async def log_chat(self):
        while True:
            chat_messages = await self.get_chat()
            if chat_messages.startswith("SERVER"):
                continue
            if chat_messages != 'Server received, But no response!! \n ':
                self.logged_messages.add(chat_messages)
                await self.channel.send(chat_messages)  # Send the message to the channel
            await asyncio.sleep(1)  # Adjust the sleep duration as needed
