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
    "Реализм": "photorealistic photography, 8k resolution, raw photo, highly detailed, sharp focus, 35mm lens",
    "Кино": "cinematic movie still, 35mm film photography, dramatic atmospheric lighting, shallow depth of field",
    "Аниме": "vibrant Japanese anime style illustration, Makoto Shinkai aesthetic, distinct colorful lines",
    "3D": "3D digital render, Unreal Engine 5 style, Octane 3D render, smooth raytracing, 8k",
    "GTA 5": "Grand Theft Auto V loading screen concept art style, bold vector digital illustration, Rockstar Games"
}

def enhance_and_translate(text: str, api_key: str | None) -> str:
    clean = text.lower()
    for w in ["сгенерируй", "сгенирируй", "создай", "нарисуй", "покажи"]:
        clean = clean.replace(w, "")
    clean = clean.strip()

    # Специфические ключевые маркеры для частых животных/объектов
    extra_details = ""
    if any(k in clean for k in ["енот", "енота", "енотик"]):
        extra_details = "a genuine wild raccoon, Procyon lotor, black eye mask markings, ringed striped tail"

    translated = ""
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
                        "content": "Translate the user query into a descriptive English image prompt. Output ONLY the English words, no extra text."
                    },
                    {"role": "user", "content": clean}
                ],
                "max_tokens": 60
            }
            r = requests.post(url, headers=headers, json=payload, timeout=5)
            if r.status_code == 200:
                translated = r.json()["choices"][0]["message"]["content"].strip().replace('"', '').replace("'", "")
        except Exception:
            pass

    if not translated:
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": clean}
            res = requests.get(url, params=params, timeout=3).json()
            translated = "".join([s[0] for s in res[0] if s[0]])
        except Exception:
            translated = clean

    if extra_details:
        return f"{translated}, {extra_details}"
    return translated

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    api_key = os.getenv("APIMIRA_KEY")

    try:
        english_subject = enhance_and_translate(req.prompt, api_key)
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        full_prompt = f"{english_subject}, {style_suffix}".strip(", ")
        encoded_prompt = urllib.parse.quote(full_prompt)

        dimensions = {
            "1:1": (768, 768),
            "9:16": (576, 1024),
            "16:9": (1024, 576)
        }
        w, h = dimensions.get(req.ratio, (768, 768))
        seed = random.randint(100000, 9999999)

        # Выбираем случайное зеркало кластера, чтобы не ловить лимиты очередей
        cluster_node = random.choice(["image.pollinations.ai", "gen.pollinations.ai"])
        direct_url = f"https://{cluster_node}/prompt/{encoded_prompt}?width={w}&height={h}&seed={seed}&model=flux&nologo=true"

        return {"type": "image", "url": direct_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
