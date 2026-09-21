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

# Стили для качественного визуала
STYLE_MODIFIERS = {
    "Реализм": "hyperrealistic photography, 8k resolution, shot on 35mm lens, highly detailed, photorealistic",
    "Кино": "cinematic shot, dramatic atmosphere, cinematic lighting, masterpiece, movie still",
    "Аниме": "beautiful anime illustration, Makoto Shinkai style, vibrant colorful anime art",
    "3D": "3D digital render, Unreal Engine 5 render, Octane 3D, ultra-detailed textures",
    "GTA 5": "GTA V loading screen art style, bold digital illustration, Rockstar Games art"
}

def translate_to_en(text: str) -> str:
    """Переводит промпт на английский для точной работы нейросети"""
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
        # 1. Автоперевод на английский
        clean_prompt = req.prompt.lower().replace("создай", "").replace("нарисуй", "").strip()
        english_prompt = translate_to_en(clean_prompt)

        # 2. Добавление модификаторов стиля
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        final_prompt = f"{english_prompt}, {style_suffix}".strip(", ")
        encoded_prompt = urllib.parse.quote(final_prompt)

        # 3. Разрешения экрана
        dimensions = {
            "1:1": (1024, 1024),
            "9:16": (768, 1344),
            "16:9": (1344, 768)
        }
        width, height = dimensions.get(req.ratio, (1024, 1024))
        seed = random.randint(1, 999999)

        # 4. Прямой URL генератора Flux
        image_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=flux&seed={seed}&nologo=true"
        )

        return {"type": "image", "url": image_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
