from utils.ark.arkinfo import ArkRcon 
import asyncio

class ArkChat():
    def __init__(self, channel, bot):
        self.bot = bot
        self.channel = channel
        self.bot.loop.create_task(self.log_chat())

    def get_chat(self):
        rcon = ArkRcon("GetChat")
        try:
            results = rcon.execute_command()
            return results
        except:
            return None
    
    async def log_chat(self):
        while True:
            chat_messages = self.get_chat()
            if chat_messages is None
                await asyncio.sleep(1)
                continue
            if chat_messages != 'Server received, But no response!! \n ':
                await self.channel.send(chat_messages)  # Send the message to the channel
            await asyncio.sleep(1)  # Adjust the sleep duration as needed
