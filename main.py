import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import replicate

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
    "Реализм": "photorealistic, hyperrealistic, 8k resolution, highly detailed, raw photo",
    "Кино": "cinematic lighting, 35mm film photograph, dramatic atmosphere, cinematic composition",
    "Аниме": "anime style, Makoto Shinkai aesthetic, vibrant colors, detailed line art",
    "3D": "3D render, Unreal Engine 5, Octane render, smooth lighting, volumetric glow",
    "GTA 5": "Grand Theft Auto V art style, loading screen illustration, bold digital painting"
}

@app.get("/")
def health_check():
    return {"status": "ok", "service": "AI Studio Backend"}

@app.post("/api/generate")
def generate_media(req: GenerateRequest):
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise HTTPException(status_code=500, detail="REPLICATE_API_TOKEN не настроен на сервере")

    style_suffix = STYLE_MODIFIERS.get(req.style, "")
    full_prompt = f"{req.prompt}, {style_suffix}".strip(", ")

    try:
        if req.mode == "image":
            output = replicate.run(
                "black-forest-labs/flux-schnell",
                input={
                    "prompt": full_prompt,
                    "aspect_ratio": req.ratio,
                    "output_format": "webp",
                    "output_quality": 90
                }
            )
            result_url = str(output[0])
            return {"type": "image", "url": result_url}

        elif req.mode == "video":
            output = replicate.run(
                "minimax/video-01",
                input={
                    "prompt": full_prompt,
                    "prompt_optimizer": True
                }
            )
            result_url = str(output)
            return {"type": "video", "url": result_url}

        else:
            raise HTTPException(status_code=400, detail="Неверный режим")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")
