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
    "Реализм": "hyperrealistic photography, 8k, raw photo, detailed, photorealistic",
    "Кино": "cinematic lighting, dramatic atmosphere, cinematic shot, movie still",
    "Аниме": "anime style art, vibrant colors, detailed line art, Makoto Shinkai aesthetic",
    "3D": "3D digital render, Unreal Engine 5, Octane 3D, detailed textures",
    "GTA 5": "Grand Theft Auto V art style, loading screen illustration, Rockstar Games art"
}

def translate_to_en(text: str) -> str:
    """Перевод через Google Translate с очисткой ответа"""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "ru",
            "tl": "en",
            "dt": "t",
            "q": text
        }
        res = requests.get(url, params=params, timeout=4).json()
        translated = "".join([s[0] for s in res[0] if s[0]])
        return translated if translated else text
    except Exception:
        return text

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    try:
        raw_text = req.prompt.lower()
        for word in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
            raw_text = raw_text.replace(word, "")
        raw_text = raw_text.strip()

        # 1. Переводим русский текст на английский
        english_prompt = translate_to_en(raw_text)

        # 2. Соединяем со стилем
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        full_prompt = f"{english_prompt}, {style_suffix}".strip(", ")

        # 3. Экранируем пробелы и спецсимволы
        encoded_prompt = urllib.parse.quote(full_prompt)

        dimensions = {
            "1:1": (768, 768),
            "9:16": (576, 1024),
            "16:9": (1024, 576)
        }
        width, height = dimensions.get(req.ratio, (768, 768))
        seed = random.randint(1000, 999999)

        # 4. Формируем URL без лишних параметров, с жестко заданной моделью flux
        image_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=flux&seed={seed}&nologo=true&enhance=false"
        )

        return {
            "type": "image", 
            "url": image_url,
            "translated": english_prompt
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
