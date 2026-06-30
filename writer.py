from groq import Groq

async def generate_script(niche, api_key):
    client = Groq(api_key=api_key)
    prompt = f"Напиши короткий сценарий для YouTube Shorts про {niche}. Верни ответ в JSON: {{'title': '...', 'text': '...', 'prompts': ['промпт1', 'промпт2']}}"
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-70b-8192"
    )
    return completion.choices[0].message.content
  
