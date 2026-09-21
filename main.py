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
    "Реализм": "award-winning wildlife photography, photorealistic, 8k resolution, raw photo, highly detailed fur, crisp focus, studio lighting",
    "Кино": "cinematic movie still, 35mm film photography, dramatic atmospheric lighting, shallow depth of field, detailed fur texture",
    "Аниме": "vibrant Japanese anime style illustration, Makoto Shinkai aesthetic, distinct colorful lines, rich background",
    "3D": "3D digital render, Pixar and Unreal Engine 5 style, Octane 3D render, smooth cute 3D character",
    "GTA 5": "Grand Theft Auto V loading screen concept art style, bold vector digital illustration, Rockstar Games"
}

def enhance_and_translate(text: str, api_key: str | None) -> str:
    # Очистка вводных слов
    clean = text.lower()
    for w in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
        clean = clean.replace(w, "")
    clean = clean.strip()

    # Если в запросе упомянут енот — жестко прописываем ключевые видовые признаки, чтобы не было путаницы с котом
    extra_details = ""
    if any(k in clean for k in ["енот", "енота", "енотик"]):
        extra_details = "a genuine wild raccoon, Procyon lotor, black eye mask markings, ringed striped tail, raccoon whiskers"

    # Перевод через модель APImira
    translated = ""
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
                        "content": "Translate Russian query into a vivid English subject description. Output ONLY the English subject words, no extra commentary."
                    },
                    {"role": "user", "content": clean}
                ],
                "max_tokens": 50
            }
            r = requests.post(url, headers=headers, json=payload, timeout=5)
            if r.status_code == 200:
                translated = r.json()["choices"][0]["message"]["content"].strip()
                translated = translated.replace('"', '').replace("'", "")
        except Exception:
            pass

    # Резервный перевод Google
    if not translated:
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": clean}
            res = requests.get(url, params=params, timeout=3).json()
            translated = "".join([s[0] for s in res[0] if s[0]])
        except Exception:
            translated = clean

    # Собираем промпт с анатомическими уточнениями
    if extra_details:
        return f"{translated}, {extra_details}"
    return translated

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/api/image-proxy")
def image_proxy(prompt: str, style: str = "Реализм", ratio: str = "1:1"):
    api_key = os.getenv("APIMIRA_KEY")

    # Формируем точный детальный промпт
    english_subject = enhance_and_translate(prompt, api_key)
    style_suffix = STYLE_MODIFIERS.get(style, "")
    full_prompt = f"{english_subject}, {style_suffix}".strip(", ")
    encoded_prompt = urllib.parse.quote(full_prompt)

    dimensions = {
        "1:1": (768, 768),
        "9:16": (576, 1024),
        "16:9": (1024, 576)
    }
    w, h = dimensions.get(ratio, (768, 768))
    seed = random.randint(100000, 9999999)

    # Генерация через Flux
    source_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={w}&height={h}&model=flux&seed={seed}&nologo=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    resp = requests.get(source_url, headers=headers, timeout=40)
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Ошибка генерации изображения")

    return Response(content=resp.content, media_type="image/jpeg")

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    encoded_prompt = urllib.parse.quote(req.prompt)
    encoded_style = urllib.parse.quote(req.style)
    encoded_ratio = urllib.parse.quote(req.ratio)

    internal_url = f"https://max-ai-backend-9qd1.onrender.com/api/image-proxy?prompt={encoded_prompt}&style={encoded_style}&ratio={encoded_ratio}&t={int(time.time())}"
    return {"type": "image", "url": internal_url}
