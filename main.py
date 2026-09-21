import os
import time
import random
import urllib.parse
from fastapi import FastAPI, HTTPException, Response
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
    # 1. Перевод через APImira
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

    # 2. Резервный перевод Google
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

# Эндпоинт прямого проксирования изображения
@app.get("/api/image-proxy")
def image_proxy(prompt: str, style: str = "Реализм", ratio: str = "1:1"):
    api_key = os.getenv("APIMIRA_KEY")

    # Очистка
    clean_text = prompt.lower()
    for w in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
        clean_text = clean_text.replace(w, "")
    clean_text = clean_text.strip()

    english_prompt = translate_to_en(clean_text, api_key)
    style_suffix = STYLE_MODIFIERS.get(style, "")
    full_prompt = f"a detailed photo of {english_prompt}, {style_suffix}".strip(", ")
    encoded_prompt = urllib.parse.quote(full_prompt)

    dimensions = {
        "1:1": (768, 768),
        "9:16": (576, 1024),
        "16:9": (1024, 576)
    }
    w, h = dimensions.get(ratio, (768, 768))
    seed = random.randint(100000, 9999999)

    # Сервер сам скачивает сгенерированную картинку
    source_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={w}&height={h}&model=flux&seed={seed}&nologo=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    img_resp = requests.get(source_url, headers=headers, timeout=40)

    if img_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Ошибка загрузки изображения")

    # Отдаем байты картинки напрямую клиенту под видом локального файла
    return Response(content=img_resp.content, media_type="image/jpeg")

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    encoded_prompt = urllib.parse.quote(req.prompt)
    encoded_style = urllib.parse.quote(req.style)
    encoded_ratio = urllib.parse.quote(req.ratio)
    
    # Возвращаем ссылку на наш собственный бэкенд на Render!
    internal_url = f"https://max-ai-backend-9qd1.onrender.com/api/image-proxy?prompt={encoded_prompt}&style={encoded_style}&ratio={encoded_ratio}&t={int(time.time())}"
    return {"type": "image", "url": internal_url}
