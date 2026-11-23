"""
Gemini helpers for SmartAcademic (assistive marking + report form editing).

What this module guarantees
- Every failure is raised as AIServiceError with a clear message and an HTTP-like
  status_code, so views can show the real reason instead of a generic 500.
- JSON output uses standard (lowercase) JSON Schema via `response_json_schema`,
  and automatically falls back to `response_schema` on older SDK versions.
- Transient errors (429 / 5xx) are retried; a missing model (404) falls back to
  the models listed in GEMINI_FALLBACK_MODELS.
- Files are read from storage safely: a missing or unreadable file gives "" / None
  instead of crashing the request.
- PDFs and images can be sent to Gemini natively (handles scanned / handwritten work).

Environment variables
  GEMINI_API_KEY            (required)
  GEMINI_MODEL              default: gemini-3.6-flash
  GEMINI_FALLBACK_MODELS    comma separated, default: gemini-2.5-flash
  GEMINI_MAX_RETRIES        default: 2
  GEMINI_TIMEOUT_SECONDS    default: 60
"""
import io
import json
import logging
import os
import re
import time
from functools import lru_cache
from typing import Any, List, Optional

from google import genai
from google.genai import types
from pptx import Presentation
from pypdf import PdfReader

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
FALLBACK_MODELS = [
    m.strip()
    for m in os.environ.get("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash").split(",")
    if m.strip()
]
MAX_RETRIES = int(os.environ.get("GEMINI_MAX_RETRIES", "2"))
TIMEOUT_SECONDS = int(os.environ.get("GEMINI_TIMEOUT_SECONDS", "60"))

MAX_READ_BYTES = 25 * 1024 * 1024      # never load files bigger than this into memory
MAX_INLINE_BYTES = 15 * 1024 * 1024    # Gemini inline data limit (keep well under 20 MB)

MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class AIServiceError(Exception):
    """Raised for any AI failure. `status_code` is the HTTP status the view should return."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise AIServiceError(
            "GEMINI_API_KEY is not configured on the server. Add it in the Render environment settings.",
            status_code=503,
        )
    try:
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000),
        )
    except Exception:
        # Older SDK without http_options.timeout
        return genai.Client(api_key=api_key)


def _status_of(exc: Exception) -> Optional[int]:
    for attr in ("code", "status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def _model_chain(model: Optional[str]) -> List[str]:
    chain = [model or DEFAULT_MODEL, *FALLBACK_MODELS]
    seen, ordered = set(), []
    for name in chain:
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def _friendly(exc: Exception, model: str) -> AIServiceError:
    code = _status_of(exc)
    detail = str(getattr(exc, "message", "") or exc)[:300]
    if code == 400:
        return AIServiceError(f"The AI request was rejected (400): {detail}", 400)
    if code in (401, 403):
        return AIServiceError(
            "The Gemini API key was rejected. Check GEMINI_API_KEY and that the key has access to the model.",
            503,
        )
    if code == 404:
        return AIServiceError(
            f"The AI model '{model}' was not found. Set GEMINI_MODEL to a model your key can use.", 503
        )
    if code == 429:
        return AIServiceError("The AI service is busy or the quota is used up. Try again in a minute.", 429)
    return AIServiceError(f"The AI service failed ({code or 'network'}): {detail}", 502)


def _generate(contents: Any, config: "types.GenerateContentConfig", model: Optional[str]) -> str:
    """Call Gemini with retries and model fallback. Returns the response text."""
    client = get_gemini_client()
    last_error: Optional[AIServiceError] = None

    for model_name in _model_chain(model):
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model_name, contents=contents, config=config
                )
                text = (getattr(response, "text", None) or "").strip()
                if not text:
                    raise AIServiceError(
                        "The AI returned an empty response (it may have been blocked). Try again or mark manually.",
                        502,
                    )
                return text
            except AIServiceError:
                raise
            except Exception as exc:  # noqa: BLE001 - classified below
                code = _status_of(exc)
                if code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                last_error = _friendly(exc, model_name)
                logger.warning("Gemini call failed on %s: %s", model_name, exc)
                if code == 404:
                    break  # try the next model in the chain
                raise last_error from exc

    raise last_error or AIServiceError("The AI service is unavailable.", 502)


# ---------------------------------------------------------------------------
# Text and JSON generation
# ---------------------------------------------------------------------------
def _build_contents(prompt: str, parts: Optional[list]) -> list:
    return [*(parts or []), prompt]


def generate_text_response(
    system_instruction: str,
    prompt: str,
    temperature: float = 0.4,
    model: Optional[str] = None,
    parts: Optional[list] = None,
) -> str:
    config = types.GenerateContentConfig(
        system_instruction=system_instruction, temperature=temperature
    )
    return _generate(_build_contents(prompt, parts), config, model)


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S | re.I)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise AIServiceError("The AI returned an invalid answer (not valid JSON). Please try again.", 502)


def generate_json_response(
    system_instruction: str,
    prompt: str,
    json_schema: dict,
    temperature: float = 0.2,
    model: Optional[str] = None,
    parts: Optional[list] = None,
) -> dict:
    """
    Structured output. `json_schema` must be standard JSON Schema with LOWERCASE types
    ("object", "string", "number", "boolean", "array", "integer").
    """
    base = dict(
        system_instruction=system_instruction,
        temperature=temperature,
        response_mime_type="application/json",
    )
    configs = []
    for key in ("response_json_schema", "response_schema"):
        try:
            configs.append(types.GenerateContentConfig(**base, **{key: json_schema}))
        except Exception:  # SDK version does not know this field
            continue
    if not configs:
        configs.append(types.GenerateContentConfig(**base))

    contents = _build_contents(prompt, parts)
    for index, config in enumerate(configs):
        try:
            return _parse_json(_generate(contents, config, model))
        except AIServiceError as exc:
            if exc.status_code == 400 and index < len(configs) - 1:
                continue  # schema field not accepted, try the other one
            raise
    raise AIServiceError("The AI service is unavailable.", 502)


# ---------------------------------------------------------------------------
# File helpers (safe: never raise)
# ---------------------------------------------------------------------------
def _ext_of(file_field) -> str:
    return os.path.splitext(getattr(file_field, "name", "") or "")[1].lower()


def _read_bytes(file_field, max_bytes: int = MAX_READ_BYTES) -> Optional[bytes]:
    if not file_field:
        return None
    try:
        file_field.open("rb")
        try:
            data = file_field.read(max_bytes + 1)
        finally:
            try:
                file_field.close()
            except Exception:  # noqa: BLE001
                pass
    except Exception as exc:  # noqa: BLE001 - file missing on disk / storage error
        logger.warning("Could not read file %s: %s", getattr(file_field, "name", "?"), exc)
        return None
    if len(data) > max_bytes:
        return None
    return data


def extract_text_from_file_field(file_field, max_chars: int = 12000) -> str:
    """Extract text from .pdf, .pptx, .docx or .txt. Returns '' when nothing can be read."""
    if not file_field:
        return ""
    ext = _ext_of(file_field)
    if ext not in (".pdf", ".pptx", ".docx", ".txt"):
        return ""
    data = _read_bytes(file_field)
    if not data:
        return ""

    chunks: List[str] = []
    try:
        if ext == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:  # noqa: BLE001
                    return ""
            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                except Exception:  # noqa: BLE001
                    page_text = ""
                if page_text:
                    chunks.append(page_text)
        elif ext == ".pptx":
            for slide in Presentation(io.BytesIO(data)).slides:
                for shape in slide.shapes:
                    if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
                        chunks.append(shape.text_frame.text)
                    if getattr(shape, "has_table", False) and shape.has_table:
                        for row in shape.table.rows:
                            chunks.append(" | ".join(cell.text for cell in row.cells))
        elif ext == ".docx":
            try:
                import docx  # python-docx is optional

                document = docx.Document(io.BytesIO(data))
                chunks.extend(p.text for p in document.paragraphs if p.text)
            except ImportError:
                return ""
        elif ext == ".txt":
            chunks.append(data.decode("utf-8", errors="ignore"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Text extraction failed for %s: %s", getattr(file_field, "name", "?"), exc)
        return ""

    return "\n".join(chunks).strip()[:max_chars]


def file_to_part(file_field, max_bytes: int = MAX_INLINE_BYTES):
    """Return a Gemini Part for a PDF or image (so scanned/handwritten work can be read), else None."""
    mime = MIME_BY_EXT.get(_ext_of(file_field))
    if not mime:
        return None
    data = _read_bytes(file_field, max_bytes)
    if not data:
        return None
    try:
        return types.Part.from_bytes(data=data, mime_type=mime)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not build file part: %s", exc)
        return None