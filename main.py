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
    "Реализм": "photorealistic photography, 8k, highly detailed, realistic lighting",
    "Кино": "cinematic lighting, 35mm film photography, masterpiece, movie still",
    "Аниме": "anime illustration, Makoto Shinkai style, vibrant colors",
    "3D": "3D render, Octane render, Unreal Engine 5, ultra-detailed textures",
    "GTA 5": "Grand Theft Auto V art style, loading screen illustration"
}

def translate_to_en(text: str) -> str:
    """Безотказный перевод запроса через Google"""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": text}
        res = requests.get(url, params=params, timeout=4).json()
        translated = "".join([sentence[0] for sentence in res[0] if sentence[0]])
        return translated if translated else text
    except Exception:
        return text

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    try:
        # 1. Очищаем вводные слова
        clean_text = req.prompt.lower()
        for word in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
            clean_text = clean_text.replace(word, "")
        clean_text = clean_text.strip()

        # 2. Переводим на английский
        english_prompt = translate_to_en(clean_text)

        # 3. Соединяем со стилем
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        final_prompt = f"{english_prompt}, {style_suffix}".strip(", ")
        encoded_prompt = urllib.parse.quote(final_prompt)

        # 4. Размеры кадра
        dimensions = {
            "1:1": (768, 768),
            "9:16": (576, 1024),
            "16:9": (1024, 576)
        }
        width, height = dimensions.get(req.ratio, (768, 768))
        seed = random.randint(1000, 999999)

        # 5. Новый актуальный и стабильный endpoint gen.pollinations.ai
        image_url = (
            f"https://gen.pollinations.ai/image/{encoded_prompt}"
            f"?width={width}&height={height}&seed={seed}&nologo=true"
        )

        return {"type": "image", "url": image_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
