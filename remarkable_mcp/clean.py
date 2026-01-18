import json
import os
import urllib.error
import urllib.request
from pathlib import Path

# Load env variables if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_REPAIR_MODEL = os.environ.get("OPENAI_REPAIR_MODEL", "gpt-4o-mini").strip()
# Set to 'true' by default, can be disabled via env
ENABLE_REPAIR = os.environ.get("ENABLE_REPAIR", "true").lower() in ("true", "1", "yes")

PROMPT_FILE = Path(__file__).parent / "openai_cleanup_prompt.txt"

def _read_prompt_instructions() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8").strip()
    return "Clean this OCR text."

def _openai_chat(prompt: str) -> str:
    """
    Minimal OpenAI-compatible chat call via HTTP.
    Uses OPENAI_API_KEY and OPENAI_REPAIR_MODEL.
    """
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY not set. Skipping text cleanup.")
        return ""

    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": OPENAI_REPAIR_MODEL,
        "messages": [
            {"role": "system", "content": "You clean OCR text with minimal rewriting. Preserve wording."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {OPENAI_API_KEY}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            j = json.loads(body)
            # Handle potential API errors in response body if status was 200 (less likely with urllib)
            return j["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        print(f"OpenAI API HTTP Error: {e.code} {e.reason}")
        # Try to read error body
        try:
             err_body = e.read().decode('utf-8')
             print(f"Details: {err_body}")
        except:
             pass
        return ""
    except urllib.error.URLError as e:
        print(f"OpenAI API Connection Error: {e.reason}")
        return ""
    except Exception as e:
        print(f"OpenAI Unexpected Error: {e}")
        return ""

def repair_text_with_openai(text: str) -> str:
    """
    Clean up OCR text using OpenAI.
    Returns the cleaned text, or the original text if repair fails/disabled.
    """
    if not ENABLE_REPAIR:
        return text

    if not OPENAI_API_KEY:
        # Warn once? Or just return text
        return text

    if not text or not text.strip():
        return text

    instructions = _read_prompt_instructions()
    prompt = f"{instructions}\n\nTEXT:\n{text}"

    out = _openai_chat(prompt)
    if not out:
        return text # Fallback to original

    return out.strip()
