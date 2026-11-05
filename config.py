import json
import os
import re
import shutil
import uuid
from datetime import datetime
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
    # An existing file wins even when empty, so disconnected accounts stay disconnected.
    if os.path.exists(_PROFILES_PATH):
        return _load_profiles_from_json()
    return _load_profiles_from_env()


def save_profiles(profiles: list[dict]):
    os.makedirs(os.path.dirname(_PROFILES_PATH), exist_ok=True)
    with open(_PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)


# App-owned Chrome profiles hold Google login sessions, so they live outside the repository.
_MANAGED_PROFILES_DIR = os.path.join(
    os.getenv("LOCALAPPDATA") or os.path.join(os.path.dirname(__file__), "data"),
    "MarketingAIAgent",
    "chrome_profiles",
)


def new_managed_profile_dir() -> str:
    path = os.path.join(_MANAGED_PROFILES_DIR, uuid.uuid4().hex)
    os.makedirs(path)
    return path


def remove_managed_profile(path: str):
    """Delete an app-owned profile. Any other path, such as the user's own Chrome, is left alone."""
    root = os.path.normcase(os.path.abspath(_MANAGED_PROFILES_DIR)) + os.sep
    if path and os.path.normcase(os.path.abspath(path)).startswith(root):
        shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------------------
# Error logging
# ---------------------------------------------------------------------------
_ERROR_LOG_PATH = os.path.join(os.path.dirname(__file__), "data", "error.log")


def _ensure_log_dir():
    os.makedirs(os.path.dirname(_ERROR_LOG_PATH), exist_ok=True)


def log_error(source: str, error: Exception, context: str = ""):
    """Append a timestamped error entry to data/error.log."""
    _ensure_log_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{source}] {type(error).__name__}: {error}"
    if context:
        line += f" | context: {context}"
    # googleapiclient's HttpError includes the request URL, API key included.
    line = re.sub(r"(key=)[^&\s>]+", r"\1***", " ".join(line.split()))
    try:
        with open(_ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def read_error_log(limit: int = 50) -> list[str]:
    """Read the most recent *limit* lines from the error log."""
    if not os.path.isfile(_ERROR_LOG_PATH):
        return []
    try:
        with open(_ERROR_LOG_PATH, encoding="utf-8") as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines[-limit:]]
    except OSError:
        return []


def read_error_log_by_date(target_date=None, limit: int = 50) -> list[str]:
    if not os.path.isfile(_ERROR_LOG_PATH):
        return []
    try:
        with open(_ERROR_LOG_PATH, encoding="utf-8") as f:
            lines = f.readlines()
        if target_date:
            date_str = target_date.strftime("%Y-%m-%d")
            lines = [l for l in lines if f"[{date_str}" in l]
        return [l.rstrip() for l in lines[-limit:]]
    except OSError:
        return []


def read_chrome_profile_info(profile_path: str) -> dict:
    """Read Google account info from a Chrome profile's Preferences file.

    Args:
        profile_path: Path to the Chrome profile directory
                      (e.g. ``C:/Users/User/AppData/Local/Google/Chrome/User Data/Profile 1``).

    Returns a dict with keys:
        name    - Google account display name (or Chrome profile name)
        email   - Google account email (may be empty)
        picture - Profile picture URL (may be empty)
    """
    result = {"name": "", "email": "", "picture": ""}
    if not profile_path:
        return result

    prefs_path = os.path.join(profile_path.replace("/", os.sep), "Preferences")
    if not os.path.isfile(prefs_path):
        return result

    try:
        with open(prefs_path, encoding="utf-8") as f:
            prefs = json.load(f)

        account_info = prefs.get("account_info", [])
        if account_info and isinstance(account_info, list) and len(account_info) > 0:
            first = account_info[0]
            result["name"] = first.get("full_name", "")
            result["email"] = first.get("email", "")
            result["picture"] = first.get("picture_url", "") or first.get(
                "last_downloaded_image_url_with_size", ""
            )

        # Fallback to profile.name if no Google account name
        if not result["name"]:
            result["name"] = prefs.get("profile", {}).get("name", "")
    except (json.JSONDecodeError, OSError, KeyError):
        pass

    return result
