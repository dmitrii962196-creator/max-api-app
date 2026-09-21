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
        # 1. Запрашиваем точный список моделей у вашего аккаунта APImira
        models_resp = requests.get("https://apimira.com/v1/models", headers=headers, timeout=15)
        
        if models_resp.status_code != 200:
            raise Exception(f"Не удалось получить модели ({models_resp.status_code}): {models_resp.text}")

        models_data = models_resp.json()
        all_ids = [m.get("id") for m in models_data.get("data", [])]

        # Ищем модели для картинок (image, flux, dalle, sd, midjourney)
        image_models = [m for m in all_ids if any(k in m.lower() for k in ["image", "flux", "dall", "sd", "midjourney", "diffusion"])]

        # 2. Если нашли подходящую модель для картинок — пробуем сделать генерацию
        if image_models:
            chosen_model = image_models[0]
            url = "https://apimira.com/v1/images/generations"
            payload = {
                "model": chosen_model,
                "prompt": req.prompt,
                "size": "1024x1024",
                "n": 1
            }
            gen_resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if gen_resp.status_code == 200:
                data = gen_resp.json()
                image_url = data["data"][0].get("url") or data["data"][0].get("b64_json")
                return {"type": "image", "url": image_url}
            else:
                raise Exception(f"Модель {chosen_model} выдала ошибку: {gen_resp.text}")

        # 3. Если автоматический фильтр не нашел слово 'image', покажем список всех доступных в аккаунте моделей
        raise Exception(f"Список доступных моделей на аккаунте: {all_ids[:8]}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
