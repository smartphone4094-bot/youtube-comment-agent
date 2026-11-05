import json
import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# OpenRouter 설정 (무료 모델 지원)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3.1-flash-lite")

# Anthropic 설정 (유료, 선택)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 어떤 AI를 쓸지: "openrouter" 또는 "anthropic"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter")

DAILY_MAX_COMMENTS = int(os.getenv("DAILY_MAX_COMMENTS", "10"))
COMMENT_MIN_CHARS = int(os.getenv("COMMENT_MIN_CHARS", "40"))
COMMENT_MAX_CHARS = int(os.getenv("COMMENT_MAX_CHARS", "120"))
BRAND_NAME = os.getenv("BRAND_NAME", "운명원")

# ---------------------------------------------------------------------------
# Chrome profiles: JSON file takes priority, .env as fallback
# ---------------------------------------------------------------------------
_PROFILES_PATH = os.path.join(os.path.dirname(__file__), "data", "profiles.json")


def _load_profiles_from_json() -> list[dict]:
    if not os.path.exists(_PROFILES_PATH):
        return []
    with open(_PROFILES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_profiles_from_env() -> list[dict]:
    profiles = []
    for i in range(1, 4):
        path = os.getenv(f"CHROME_PROFILE_{i}", "")
        if path:
            profiles.append({"name": f"유튜브{i}", "path": path})
    return profiles


def load_profiles() -> list[dict]:
    profiles = _load_profiles_from_json()
    if profiles:
        return profiles
    return _load_profiles_from_env()


def save_profiles(profiles: list[dict]):
    os.makedirs(os.path.dirname(_PROFILES_PATH), exist_ok=True)
    with open(_PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)


CHROME_PROFILES = [p["path"] for p in load_profiles()]
