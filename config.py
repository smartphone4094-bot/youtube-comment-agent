import json
import os
import re
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

# Google OAuth 설정 (프로필 관리용)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

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


# ---------------------------------------------------------------------------
# Chrome profile auto-detection
# ---------------------------------------------------------------------------
def detect_chrome_profiles() -> list[dict]:
    """Scan Chrome User Data directory and return detected profiles.

    Each entry contains:
        name     - Chrome profile directory name (e.g. "Profile 1")
        path     - Full path to the profile directory
        email    - Google account email (if found in Preferences)
        display  - Google account display name (if found)
        picture  - Google account picture URL (if found)
    """
    username = os.getenv("USERNAME") or os.getenv("USER") or ""
    chrome_base = os.path.join(
        "C:/Users", username, "AppData/Local/Google/Chrome/User Data"
    )
    if not os.path.isdir(chrome_base):
        return []

    detected: list[dict] = []
    candidates = ["Default"] + [f"Profile {i}" for i in range(1, 20)]
    for profile_dir in candidates:
        profile_path = os.path.join(chrome_base, profile_dir)
        prefs_path = os.path.join(profile_path, "Preferences")
        if not os.path.isfile(prefs_path):
            continue
        try:
            with open(prefs_path, encoding="utf-8") as f:
                prefs = json.load(f)

            # Account info lives in different places depending on Chrome version
            account_info = prefs.get("account_info", [])
            email = ""
            display_name = ""
            picture_url = ""
            if account_info and isinstance(account_info, list):
                first = account_info[0] if account_info else {}
                email = first.get("email", "")
                display_name = first.get("full_name", "")
                picture_url = first.get("last_downloaded_image_url_with_size", "")

            # Fallback: profile.name
            if not display_name:
                display_name = prefs.get("profile", {}).get("name", profile_dir)

            detected.append({
                "name": display_name or profile_dir,
                "path": profile_path.replace("\\", "/"),
                "email": email,
                "display": display_name,
                "picture": picture_url,
            })
        except (json.JSONDecodeError, OSError, KeyError):
            continue

    return detected


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


def find_chrome_profile_by_email(email: str) -> str:
    """Try to find the Chrome profile path matching the given email.

    Returns the profile path string, or empty string if not found.
    """
    if not email:
        return ""
    detected = detect_chrome_profiles()
    for p in detected:
        if p.get("email", "").lower() == email.lower():
            return p["path"]
    return ""
