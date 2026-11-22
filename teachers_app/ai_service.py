import json
import os
from pypdf import PdfReader
from pptx import Presentation
from google import genai
from google.genai import types


DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")


def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=api_key)


def extract_text_from_file_field(file_field, max_chars: int = 12000) -> str:
    """Safely extracts text from a Django FileField/FieldFile (.pdf or .pptx)."""
    if not file_field:
        return ""

    name = getattr(file_field, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    text_parts = []

    try:
        file_field.open("rb")
        if ext == ".pdf":
            reader = PdfReader(file_field)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
        elif ext == ".pptx":
            prs = Presentation(file_field)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
                        text_parts.append(shape.text_frame.text)
    finally:
        try:
            file_field.close()
        except Exception:
            pass

    combined = "\n".join(text_parts).strip()
    return combined[:max_chars]


def generate_text_response(system_instruction: str, prompt: str, temperature: float = 0.4, model: str = None) -> str:
    client = get_gemini_client()
    response = client.models.generate_content(
        model=model or DEFAULT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
        ),
    )
    return (response.text or "").strip()


def generate_json_response(system_instruction: str, prompt: str, json_schema: dict, temperature: float = 0.2, model: str = None) -> dict:
    """Enforces structured JSON output matching json_schema."""
    client = get_gemini_client()
    response = client.models.generate_content(
        model=model or DEFAULT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json",
            response_json_schema=json_schema,
        ),
    )
    raw = (response.text or "").strip()
    return json.loads(raw)