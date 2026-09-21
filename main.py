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
    "Реализм": "hyperrealistic photography, 8k resolution, raw photo, detailed, photorealistic",
    "Кино": "cinematic shot, dramatic atmosphere, cinematic lighting, masterpiece, movie scene",
    "Аниме": "anime illustration, vibrant colors, Makoto Shinkai style, high quality anime",
    "3D": "3D digital render, Unreal Engine 5, Octane 3D, detailed textures",
    "GTA 5": "Grand Theft Auto V art style, loading screen illustration, Rockstar Games art"
}

def translate_to_en(text: str) -> str:
    """Безотказный быстрый перевод через открытый шлюз Google"""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "en",
            "dt": "t",
            "q": text
        }
        res = requests.get(url, params=params, timeout=5).json()
        translated = "".join([sentence[0] for sentence in res[0]])
        return translated if translated else text
    except Exception:
        return text

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    try:
        # 1. Убираем лишние слова-команды
        raw_text = req.prompt.lower()
        for word in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
            raw_text = raw_text.replace(word, "")
        raw_text = raw_text.strip()

        # 2. Переводим фразу («енот в военной форме» -> «raccoon in military uniform»)
        english_prompt = translate_to_en(raw_text)

        # 3. Добавляем визуальные стили
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        final_prompt = f"{english_prompt}, {style_suffix}".strip(", ")
        encoded_prompt = urllib.parse.quote(final_prompt)

        # 4. Размеры
        dimensions = {
            "1:1": (768, 768),
            "9:16": (576, 1024),
            "16:9": (1024, 576)
        }
        width, height = dimensions.get(req.ratio, (768, 768))
        seed = random.randint(1, 9999999)

        # 5. Ссылка на генерацию
        direct_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=turbo&seed={seed}&nologo=true"
        )

        return {"type": "image", "url": direct_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
