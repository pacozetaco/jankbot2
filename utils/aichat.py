import ollama

OLLAMA_URL = "http://127.0.0.1:11434"  

async def chat(prompt):
    response = ollama.chat(
    model="llama2-uncensored",
    messages=[
        {"role": "user", "content": prompt}
    ],
    options={"num_predict": 300},
)
    return response['message']['content']