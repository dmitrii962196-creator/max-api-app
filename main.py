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
    "Реализм": "photorealistic, hyperrealistic, 8k resolution, raw photo, highly detailed",
    "Кино": "cinematic lighting, 35mm film photography, masterpiece, dramatic atmosphere",
    "Аниме": "anime style, Makoto Shinkai aesthetic, vibrant colors, detailed line art",
    "3D": "3D digital render, Unreal Engine 5, Octane render, 3d model",
    "GTA 5": "Grand Theft Auto V art style, loading screen illustration, Rockstar Games"
}

def translate_to_en(text: str) -> str:
    """Переводит русский запрос на английский язык"""
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
        # 1. Очищаем лишние слова («Создай», «Нарисуй») и переводим
        clean_prompt = req.prompt.lower().replace("создай", "").replace("нарисуй", "").strip()
        english_prompt = translate_to_en(clean_prompt)

        # 2. Добавляем стили
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        final_prompt = f"{english_prompt}, {style_suffix}".strip(", ")
        encoded_prompt = urllib.parse.quote(final_prompt)

        # 3. Размеры кадра
        dimensions = {
            "1:1": (1024, 1024),
            "9:16": (768, 1344),
            "16:9": (1344, 768)
        }
        width, height = dimensions.get(req.ratio, (1024, 1024))
        seed = random.randint(1, 9999999)

        # 4. Формируем прямой запрос к Flux
        target_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=flux&seed={seed}&nologo=true"
        )

        # 5. Скачиваем картинку прямо на сервер и отдаем в формате base64
        # Это исключает проблемы с кэшированием или подменой картинки
        resp = requests.get(target_url, timeout=40)
        if resp.status_code != 200:
            raise Exception("Не удалось сгенерировать изображение, попробуйте еще раз.")

        b64_image = base64.b64encode(resp.content).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64_image}"

        return {"type": "image", "url": data_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
