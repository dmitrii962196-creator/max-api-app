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
    "Реализм": "hyperrealistic photography, 8k, raw photo, highly detailed, photorealistic",
    "Кино": "cinematic shot, dramatic atmosphere, cinematic lighting, masterpiece",
    "Аниме": "anime illustration, vibrant colorful aesthetic, Makoto Shinkai style",
    "3D": "3D digital render, Unreal Engine 5, Octane render, highly detailed 3d",
    "GTA 5": "Grand Theft Auto V art style, bold digital illustration, video game concept art"
}

def translate_to_en(text: str) -> str:
    """Переводит русский запрос на английский язык"""
    try:
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair=ru|en"
        res = requests.get(url, timeout=3).json()
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
        # Очищаем лишние слова («сгенерируй», «создай», «нарисуй»)
        clean_prompt = (
            req.prompt.lower()
            .replace("сгенирируй", "")
            .replace("сгенерируй", "")
            .replace("создай", "")
            .replace("нарисуй", "")
            .strip()
        )
        english_prompt = translate_to_en(clean_prompt)
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        final_prompt = f"{english_prompt}, {style_suffix}".strip(", ")
        encoded_prompt = urllib.parse.quote(final_prompt)

        dimensions = {
            "1:1": (768, 768),
            "9:16": (576, 1024),
            "16:9": (1024, 576)
        }
        width, height = dimensions.get(req.ratio, (768, 768))
        seed = random.randint(1, 999999)

        # Формируем прямую ссылку на скоростной поток
        direct_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=turbo&seed={seed}&nologo=true"
        )

        return {"type": "image", "url": direct_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
