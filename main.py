import base64
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
    "Реализм": "hyperrealistic photography, 8k, raw photo, highly detailed, photorealistic, 35mm lens",
    "Кино": "cinematic shot, dramatic atmosphere, cinematic lighting, masterpiece, movie still",
    "Аниме": "beautiful anime illustration, Makoto Shinkai style, vibrant colorful anime art",
    "3D": "3D digital render, Unreal Engine 5, Octane render, ultra-detailed 3d textures",
    "GTA 5": "GTA V loading screen art style, bold digital illustration, Rockstar Games art"
}

def translate_to_en(text: str) -> str:
    """Переводит русский запрос на английский"""
    try:
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair=ru|en"
        res = requests.get(url, timeout=5).json()
        translated = res.get("responseData", {}).get("translatedText")
        return translated if translated else text
    except Exception:
        return text

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    try:
        # 1. Очищаем лишние слова («создай», «нарисуй») и переводим
        clean_prompt = (
            req.prompt.lower()
            .replace("сгенерируй", "")
            .replace("создай", "")
            .replace("нарисуй", "")
            .strip()
        )
        english_prompt = translate_to_en(clean_prompt)
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        final_prompt = f"{english_prompt}, {style_suffix}".strip(", ")
        encoded_prompt = urllib.parse.quote(final_prompt)

        # 2. Размеры под телефон для быстрой отдачи
        dimensions = {
            "1:1": (768, 768),
            "9:16": (576, 1024),
            "16:9": (1024, 576)
        }
        width, height = dimensions.get(req.ratio, (768, 768))
        seed = random.randint(1, 9999999)

        # 3. Скоростной генератор
        target_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=turbo&seed={seed}&nologo=true"
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(target_url, headers=headers, timeout=30)

        if resp.status_code != 200:
            raise Exception(f"Ошибка шлюза: {resp.status_code}")

        # Отдаем готовую картинку в Base64
        b64_image = base64.b64encode(resp.content).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64_image}"

        return {"type": "image", "url": data_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
