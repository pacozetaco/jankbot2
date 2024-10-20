import ollama

# Define the URL for your Ollama instance or API endpoint
OLLAMA_URL = "http://127.0.0.1:11434"  # Replace with your actual URL if different

async def chat(prompt):
    response = ollama.chat(
    model="llama3.2:latest",  # Replace with your desired model
    messages=[
        {"role": "user", "content": prompt}
    ],
    options={"num_predict": 300},
)
    return response['message']['content']