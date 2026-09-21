import base64
import os
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
    "Реализм": "hyperrealistic photography, 8k, raw photo, realistic lighting, 35mm lens, masterpiece",
    "Кино": "cinematic lighting, 35mm film still, dramatic atmosphere, cinematic, masterpiece",
    "Аниме": "anime illustration, vibrant colors, Makoto Shinkai style, high quality art",
    "3D": "3D digital render, Unreal Engine 5, Octane render, ultra-detailed textures",
    "GTA 5": "Grand Theft Auto V art style, loading screen illustration, Rockstar Games"
}

def translate_prompt(text: str, api_key: str | None) -> str:
    # 1. Попытка перевода через APImira (модель openai/gpt-6-astra)
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
                        "content": "Translate the user text into a concise, detailed English visual prompt for image generation. Return ONLY the English translation, no notes."
                    },
                    {"role": "user", "content": text}
                ],
                "max_tokens": 100
            }
            res = requests.post(url, headers=headers, json=payload, timeout=5)
            if res.status_code == 200:
                t = res.json()["choices"][0]["message"]["content"].strip()
                if t:
                    return t
        except Exception:
            pass

    # 2. Надежный резервный переводчик
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": text}
        res = requests.get(url, params=params, timeout=4).json()
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
        # Очистка вводных слов
        clean_text = req.prompt.lower()
        for w in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
            clean_text = clean_text.replace(w, "")
        clean_text = clean_text.strip()

        # Точный перевод
        en_prompt = translate_prompt(clean_text, api_key)

        # Добавляем выбранный стиль
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        final_prompt = f"a detailed {en_prompt}, {style_suffix}".strip(", ")
        encoded = urllib.parse.quote(final_prompt)

        dimensions = {
            "1:1": (768, 768),
            "9:16": (576, 1024),
            "16:9": (1024, 576)
        }
        w, h = dimensions.get(req.ratio, (768, 768))
        seed = random.randint(1000, 9999999)

        # Запрос к скоростному шлюзу через прямой endpoint с подменой User-Agent
        gen_url = f"https://pollinations.ai/p/{encoded}?width={w}&height={h}&seed={seed}&model=turbo&nologo=true"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        resp = requests.get(gen_url, headers=headers, timeout=25)

        if resp.status_code != 200:
            raise Exception(f"Ошибка шлюза ({resp.status_code})")

        # Отдаем готовую сгенерированную картинку прямо в Base64, чтобы обойти любые кеши и блокировки
        b64_img = base64.b64encode(resp.content).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64_img}"

        return {"type": "image", "url": data_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
