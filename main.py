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
    "Реализм": "photorealistic photography, 8k resolution, raw photo, highly detailed, photorealistic, 35mm lens",
    "Кино": "cinematic lighting, 35mm film photography, masterpiece, dramatic atmosphere, movie still",
    "Аниме": "anime illustration, Makoto Shinkai style, vibrant colors, clean lines, detailed art",
    "3D": "3D digital render, Unreal Engine 5, Octane 3D render, smooth textures",
    "GTA 5": "Grand Theft Auto V loading screen art style, bold digital illustration, Rockstar Games art"
}

def translate_to_en(text: str, api_key: str | None) -> str:
    # 1. Точный перевод через ваш ключ APImira
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
                        "content": "Translate the user input into a concise English descriptive prompt for image generation. Return ONLY the translation."
                    },
                    {"role": "user", "content": text}
                ],
                "max_tokens": 80
            }
            r = requests.post(url, headers=headers, json=payload, timeout=5)
            if r.status_code == 200:
                t = r.json()["choices"][0]["message"]["content"].strip()
                if t:
                    return t
        except Exception:
            pass

    # 2. Резервный переводчик
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
        clean_text = req.prompt.lower()
        for w in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
            clean_text = clean_text.replace(w, "")
        clean_text = clean_text.strip()

        english_prompt = translate_to_en(clean_text, api_key)
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        final_prompt = f"a photo of {english_prompt}, {style_suffix}".strip(", ")
        encoded_prompt = urllib.parse.quote(final_prompt)

        dimensions = {
            "1:1": (768, 768),
            "9:16": (576, 1024),
            "16:9": (1024, 576)
        }
        w, h = dimensions.get(req.ratio, (768, 768))
        seed = random.randint(1000, 9999999)

        # Прямая ссылка без ограничений по размеру и без Base64 блокировок
        direct_image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={w}&height={h}&seed={seed}&model=flux-realism&nologo=true"

        return {"type": "image", "url": direct_image_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
