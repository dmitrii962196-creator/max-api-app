import os
import time
import random
import urllib.parse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI(title="MAX AI Generator Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    mode: str
    prompt: str
    style: str
    ratio: str

STYLE_MODIFIERS = {
    "Реализм": "realistic photo, 8k, detailed fur, highly detailed photo, 35mm lens, sharp focus",
    "Кино": "cinematic movie scene, dramatic lighting, 35mm photography, cinematic atmosphere",
    "Аниме": "vibrant anime style illustration, Makoto Shinkai art, beautiful anime colors",
    "3D": "3D digital render, Unreal Engine 5, Octane 3D render, smooth raytracing",
    "GTA 5": "Grand Theft Auto V video game loading screen art style, Rockstar art"
}

def translate_to_en(text: str, api_key: str | None) -> str:
    # 1. Точный перевод через вашу подключенную модель APImira
    if api_key:
        try:
            url = "https://apimira.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "openai/gpt-6-astra",
                "messages": [
                    {
                        "role": "system",
                        "content": "Translate the user input into a concise English descriptive prompt for image generation. Return ONLY the translation, no extra words."
                    },
                    {"role": "user", "content": text}
                ],
                "max_tokens": 70
            }
            r = requests.post(url, headers=headers, json=payload, timeout=6)
            if r.status_code == 200:
                t = r.json()["choices"][0]["message"]["content"].strip()
                if t:
                    return t.replace('"', '').replace("'", "")
        except Exception:
            pass

    # 2. Быстрый резервный перевод через Google
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": text}
        res = requests.get(url, params=params, timeout=3).json()
        t = "".join([s[0] for s in res[0] if s[0]])
        if t:
            return t
    except Exception:
        pass

    return text

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    api_key = os.getenv("APIMIRA_KEY")

    try:
        # 1. Очистка слов-паразитов
        clean_text = req.prompt.lower()
        for w in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
            clean_text = clean_text.replace(w, "")
        clean_text = clean_text.strip()

        # 2. Получаем английский текст (например: "raccoon in military uniform")
        english_prompt = translate_to_en(clean_text, api_key)
        
        # 3. Соединяем со стилем
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        full_prompt = f"{english_prompt}, {style_suffix}".strip(", ")
        encoded_prompt = urllib.parse.quote(full_prompt)

        # 4. Размеры
        dimensions = {
            "1:1": (768, 768),
            "9:16": (576, 1024),
            "16:9": (1024, 576)
        }
        w, h = dimensions.get(req.ratio, (768, 768))

        # 5. Уникальный seed и временная метка для полного сброса кэша
        seed = random.randint(100000, 9999999)
        timestamp = int(time.time())

        # Чистый endpoint Flux с отключением кэша и дефолтных заглушек
        image_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={w}&height={h}&model=flux&seed={seed}&nologo=true&cache=false&t={timestamp}"
        )

        return {"type": "image", "url": image_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
