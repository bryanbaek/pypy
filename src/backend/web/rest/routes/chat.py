from fastapi import APIRouter, HTTPException, Body
from src.backend.services.google import (
    get_gemini_pro_response,
    get_gemini_lite_response,
)
from src.backend.services.openai import get_gpt_4o_response


router = APIRouter()


@router.post("/chat")
def chat(prompt: str = Body(...), model: str = Body(...)):
    try:
        if model == "gemini-pro":
            response_text = get_gemini_pro_response(prompt)
            return response_text
        elif model == "gemini-lite":
            response_text = get_gemini_lite_response(prompt)
            return response_text
        elif model == "gpt-4o":
            response_text = get_gpt_4o_response(prompt)
            return response_text
        else:
            raise HTTPException(status_code=400, detail="Invalid model specified")

        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
