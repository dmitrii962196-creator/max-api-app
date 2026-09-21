import urllib.parse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    "Реализм": "photorealistic, hyperrealistic, 8k, detailed, raw photo",
    "Кино": "cinematic lighting, 35mm film photograph, masterpiece",
    "Аниме": "anime style, Makoto Shinkai aesthetic, vibrant colors",
    "3D": "3D render, Unreal Engine 5, Octane render, volumetric lighting",
    "GTA 5": "Grand Theft Auto V art style, loading screen illustration"
}

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    try:
        style_suffix = STYLE_MODIFIERS.get(req.style, "")
        full_prompt = f"{req.prompt}, {style_suffix}".strip(", ")
        encoded_prompt = urllib.parse.quote(full_prompt)

        # Разрешения под соотношение сторон
        dimensions = {
            "1:1": (1024, 1024),
            "9:16": (768, 1344),
            "16:9": (1344, 768)
        }
        width, height = dimensions.get(req.ratio, (1024, 1024))

        # Бесплатная генерация Flux через открытый шлюз Pollinations
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"

        return {"type": "image", "url": image_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
