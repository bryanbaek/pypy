import google.generativeai as genai
from src.backend.core.config import settings

# Configuration for Google API
genai.configure(api_key=settings.GOOGLE_API_KEY)


def get_gemini_pro_response(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text


def get_gemini_lite_response(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-lite")
    response = model.generate_content(prompt)
    return response.text
