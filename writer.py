from groq import Groq

async def generate_script(niche, api_key):
    client = Groq(api_key=api_key)
    prompt = f"Напиши короткий сценарий для YouTube Shorts про {niche}. Верни ответ в JSON: {{'title': '...', 'text': '...', 'prompts': ['промпт1', 'промпт2']}}"
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile"
    
        
    )
    return completion.choices[0].message.content
  
