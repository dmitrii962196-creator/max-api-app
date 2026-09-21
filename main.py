import os
import random
import urllib.parse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI(title="MAX AI Generator Backend")

# Полный доступ без блокировок CORS
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
    "Реализм": "photorealistic photography, 8k resolution, raw photo, highly detailed, photorealistic",
    "Кино": "cinematic lighting, 35mm film photography, masterpiece, dramatic atmosphere, movie still",
    "Аниме": "anime illustration, Makoto Shinkai style, vibrant colors, clean lines",
    "3D": "3D digital render, Unreal Engine 5, Octane 3D render, smooth textures",
    "GTA 5": "Grand Theft Auto V loading screen art style, bold digital illustration, Rockstar Games art"
}

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    api_key = os.getenv("APIMIRA_KEY")

    # 1. Очищаем текст от лишних слов
    clean_text = req.prompt.lower()
    for w in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
        clean_text = clean_text.replace(w, "")
    clean_text = clean_text.strip()

    english_prompt = clean_text

    # 2. Переводим и улучшаем промпт через APImira (GPT), если ключ указан
    if api_key:
        try:
            apimira_url = "https://apimira.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            system_msg = "Translate the user input into a concise, detailed English image generation prompt. Output ONLY the English prompt, no explanations."
            payload = {
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": clean_text}
                ],
                "max_tokens": 80
            }
            res = requests.post(apimira_url, headers=headers, json=payload, timeout=7)
            if res.status_code == 200:
                english_prompt = res.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # 3. Добавляем стиль
    style_suffix = STYLE_MODIFIERS.get(req.style, "")
    full_prompt = f"{english_prompt}, {style_suffix}".strip(", ")
    encoded_prompt = urllib.parse.quote(full_prompt)

    # 4. Размеры
    dimensions = {
        "1:1": (768, 768),
        "9:16": (576, 1024),
        "16:9": (1024, 576)
    }
    width, height = dimensions.get(req.ratio, (768, 768))
    seed = random.randint(1000, 9999999)

    # 5. Прямой CDN-генератор Flux
    image_url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={width}&height={height}&model=flux&seed={seed}&nologo=true"
    )

    return {"type": "image", "url": image_url}
