import os
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
    "Реализм": "фотореализм, высокое разрешение, 8k, детальная текстура, реалистичное освещение, шедевр",
    "Кино": "кадр из фильма, кинематографичное освещение, 35мм, кинематограф, глубокие тени",
    "Аниме": "аниме стиль, яркие цвета, стилистика Макото Синкая, качественный арт",
    "3D": "3D рендер, Unreal Engine 5, Octane render, объемное освещение, четкие детали",
    "GTA 5": "стиль загрузочного экрана GTA V, цифровая иллюстрация Rockstar Games"
}

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    api_key = os.getenv("APIMIRA_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="APIMIRA_KEY не настроен на Render")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        # 1. Формируем промпт
        raw_text = req.prompt.lower()
        for word in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
            raw_text = raw_text.replace(word, "")
        raw_text = raw_text.strip()

        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        final_prompt = f"{raw_text}, {style_suffix}".strip(", ")

        dimensions = {
            "1:1": "1024x1024",
            "9:16": "1024x1792",
            "16:9": "1792x1024"
        }
        size = dimensions.get(req.ratio, "1024x1024")

        # 2. Список наиболее вероятных названий моделей для изображений в APImira
        candidates = [
            "openai/dall-e-3",
            "black-forest-labs/flux-1-schnell",
            "black-forest-labs/flux-1-dev",
            "stabilityai/stable-diffusion-xl-base-1.0",
            "dall-e-3"
        ]

        # 3. Делаем попытку отправки запроса
        last_error = ""
        for model_name in candidates:
            url = "https://apimira.com/v1/images/generations"
            payload = {
                "model": model_name,
                "prompt": final_prompt,
                "size": size,
                "n": 1
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                image_url = data["data"][0].get("url") or data["data"][0].get("b64_json")
                return {"type": "image", "url": image_url}
            else:
                last_error = f"{model_name}: {resp.text}"

        # Если ни одна стандартная модель не подошла, выводим ответ сервиса
        raise Exception(f"Доступные модели отклонили запрос: {last_error}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
