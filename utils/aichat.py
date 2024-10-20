import ollama, asyncio
from concurrent.futures import ThreadPoolExecutor

# Define the URL for your Ollama instance or API endpoint

OLLAMA_URL = "http://127.0.0.1:11434" 

def chat(prompt):
    response = ollama.chat(
    model="llama2-uncensored",  
    messages=[
        {"role": "user", "content": prompt}
    ],
    options={"num_predict": 300},
)
    return response['message']['content']

async def process_ai_request(message):
    executor = ThreadPoolExecutor()
    ai_message = await message.reply(content="```Thinking...```")
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(executor, chat, message.content)
    await ai_message.edit(content=f"```{response}```")
    executor.shutdown()