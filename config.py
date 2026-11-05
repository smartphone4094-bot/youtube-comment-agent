import copy
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime

import yaml

# ---------------------------------------------------------------------------
# Settings: everything lives in settings.yaml (git-ignored). No value is hardcoded here.
#   profiles - connected Google accounts      comment - min_chars / max_chars / brand
#   limits   - daily_max_comments, max_accounts   api - YouTube key, AI service, keys, models
# settings.example.yaml (committed, no secrets) seeds it on first run.
# ---------------------------------------------------------------------------
_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
_FROZEN = getattr(sys, "frozen", False)


def resource_path(*parts: str) -> str:
    """Read-only files shipped with the app (styles.css, settings.example.yaml, vendor/...).

    From source: the project folder. In the PyInstaller build: the unpacked bundle (sys._MEIPASS).
    """
    base = getattr(sys, "_MEIPASS", _SOURCE_DIR) if _FROZEN else _SOURCE_DIR
    return os.path.join(base, *parts)


def user_path(*parts: str) -> str:
    """Files the app writes (settings.yaml, data/, logs). From source: the project folder.
    In the PyInstaller build: the folder holding the .exe, so they are created next to it."""
    base = os.path.dirname(os.path.abspath(sys.executable)) if _FROZEN else _SOURCE_DIR
    return os.path.join(base, *parts)


SETTINGS_PATH = user_path("settings.yaml")
_EXAMPLE_PATH = resource_path("settings.example.yaml")

# Service metadata only (names and where to get a key) — keys and models are settings.
# "prefer": name fragments ranked for auto-selection from the service's live model list.
# Never full model IDs: those go stale, and a list match always exists on the service.
AI_PROVIDERS = {
    "openrouter": {"label": "OpenRouter", "key_url": "https://openrouter.ai/keys",
                   "shared_limit": True,  # the daily free limit covers every model on the account
                   "prefer": ("gemma", "nemotron-3.5-lightning", "nemotron")},
    "gemini": {"label": "Google Gemini", "key_url": "https://aistudio.google.com/apikey",
               "prefer": ("gemini-flash-latest", "flash"), "avoid": ("lite",)},
    "anthropic": {"label": "Claude (Anthropic)", "key_url": "https://console.anthropic.com/settings/keys",
                  "prefer": ("haiku", "sonnet")},
    "openai": {"label": "OpenAI", "key_url": "https://platform.openai.com/api-keys",
               "prefer": ("mini",)},
    "groq": {"label": "Groq (무료 등급)", "key_url": "https://console.groq.com/keys",
             "base_url": "https://api.groq.com/openai/v1",
             "extra_body": {"reasoning_effort": "low"},  # thinking otherwise uses up max_tokens
             "prefer": ("gpt-oss-120b", "qwen", "gpt-oss", "llama")},
    "cerebras": {"label": "Cerebras (무료 등급)", "key_url": "https://cloud.cerebras.ai",
                 "base_url": "https://api.cerebras.ai/v1",
                 "prefer": ("gpt-oss", "qwen", "llama")},
    "mistral": {"label": "Mistral (무료 등급)", "key_url": "https://console.mistral.ai/api-keys",
                "base_url": "https://api.mistral.ai/v1",
                "prefer": ("small-latest", "small", "medium")},
    "nvidia": {"label": "NVIDIA (무료 등급)", "key_url": "https://build.nvidia.com",
               "base_url": "https://integrate.api.nvidia.com/v1",
               "prefer": ("gpt-oss", "qwen", "llama", "nemotron")},
    "cohere": {"label": "Cohere (무료 등급)", "key_url": "https://dashboard.cohere.com/api-keys",
               "base_url": "https://api.cohere.ai/compatibility/v1",
               "prefer": ("command-a", "command")},
    "freellmapi": {"label": "FreeLLMAPI / 직접 지정 (OpenAI 호환)",
                   "key_url": "https://github.com/tashfeenahmed/freellmapi",
                   "base_url": "http://localhost:3001/v1", "base_url_editable": True, "default_model": "auto",
                   "note": "FreeLLMAPI를 이 PC에 먼저 실행하고, 대시보드의 통합 키를 넣으세요. "
                           "Ollama 같은 다른 OpenAI 호환 서버도 주소만 바꾸면 됩니다."},
}

_HEADER = (
    "# 운명원 마케팅 AI에이전트 설정 — API 키와 계정이 들어 있어 git에 올라가지 않습니다(.gitignore).\n"
    "# 앱의 [설정] 버튼과 계정 연결이 이 파일을 고칩니다. 직접 고쳐도 됩니다.\n\n"
)

_cache = {"mtime": None, "data": None}


def _read_yaml(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def _legacy_values() -> dict:
    """One-time carry-over from the old .env, data/profiles.json and data/settings.json."""
    from dotenv import dotenv_values

    env = dotenv_values(user_path(".env"))
    old = {}
    old_settings_path = user_path("data", "settings.json")
    if os.path.exists(old_settings_path):
        with open(old_settings_path, encoding="utf-8") as f:
            old = json.load(f)
    profiles = []
    old_profiles_path = user_path("data", "profiles.json")
    if os.path.exists(old_profiles_path):
        with open(old_profiles_path, encoding="utf-8") as f:
            profiles = json.load(f)
    else:
        profiles = [
            {"name": f"유튜브{i}", "email": "", "picture": "", "path": env[f"CHROME_PROFILE_{i}"]}
            for i in range(1, 4) if env.get(f"CHROME_PROFILE_{i}")
        ]
    return {"env": env, "old": old, "profiles": profiles}


def _create_settings() -> dict:
    settings = _read_yaml(_EXAMPLE_PATH)
    legacy = _legacy_values()
    env, old = legacy["env"], legacy["old"]
    settings["profiles"] = legacy["profiles"]
    comment = settings.setdefault("comment", {})
    for key, env_name in (("min_chars", "COMMENT_MIN_CHARS"), ("max_chars", "COMMENT_MAX_CHARS")):
        if env.get(env_name):
            comment[key] = int(env[env_name])
    if env.get("BRAND_NAME"):
        comment["brand"] = env["BRAND_NAME"]
    if env.get("DAILY_MAX_COMMENTS"):
        settings.setdefault("limits", {})["daily_max_comments"] = int(env["DAILY_MAX_COMMENTS"])
    api = settings.setdefault("api", {})
    api["youtube_api_key"] = old.get("youtube_api_key") or env.get("YOUTUBE_API_KEY") or ""
    api["ai_provider"] = old.get("ai_provider") or env.get("AI_PROVIDER") or api.get("ai_provider")
    keys, models = api.setdefault("ai_keys", {}), api.setdefault("ai_models", {})
    for provider in AI_PROVIDERS:
        env_key = env.get(f"{provider.upper()}_API_KEY")
        keys[provider] = (old.get("ai_keys") or {}).get(provider) or env_key or keys.get(provider) or ""
        models[provider] = (old.get("ai_models") or {}).get(provider) or models.get(provider) or ""
    if env.get("OPENROUTER_MODEL") and not (old.get("ai_models") or {}).get("openrouter"):
        models["openrouter"] = env["OPENROUTER_MODEL"]
    save_settings(settings)
    return settings


def load_settings() -> dict:
    """The whole settings file, re-read whenever it changes on disk (hand edits included)."""
    if not os.path.exists(SETTINGS_PATH):
        _create_settings()
    mtime = os.path.getmtime(SETTINGS_PATH)
    if _cache["mtime"] != mtime:
        _cache["data"], _cache["mtime"] = _read_yaml(SETTINGS_PATH), mtime
    return copy.deepcopy(_cache["data"])


def save_settings(settings: dict):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        f.write(_HEADER)
        yaml.safe_dump(settings, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    _cache["mtime"] = None


def _section(name: str) -> dict:
    value = load_settings().get(name)
    return value if isinstance(value, dict) else {}


# -- comment rules and limits ---------------------------------------------------------
def comment_min_chars() -> int:
    return int(_section("comment").get("min_chars", 0))


def comment_max_chars() -> int:
    return int(_section("comment").get("max_chars", 0))


def brand_name() -> str:
    return str(_section("comment").get("brand", "")).strip()


def daily_max_comments() -> int:
    return int(_section("limits").get("daily_max_comments", 0))


def max_accounts() -> int:
    return int(_section("limits").get("max_accounts", 0))


# -- API keys and AI service ----------------------------------------------------------
def youtube_api_key() -> str:
    return str(_section("api").get("youtube_api_key") or "").strip()


def ai_provider() -> str:
    provider = _section("api").get("ai_provider")
    return provider if provider in AI_PROVIDERS else next(iter(AI_PROVIDERS))


def ai_key(provider: str | None = None) -> str:
    provider = provider or ai_provider()
    return str((_section("api").get("ai_keys") or {}).get(provider) or "").strip()


def ai_model(provider: str | None = None) -> str:
    provider = provider or ai_provider()
    saved = str((_section("api").get("ai_models") or {}).get(provider) or "").strip()
    return saved or AI_PROVIDERS.get(provider, {}).get("default_model", "")


def ai_base_url(provider: str | None = None) -> str:
    provider = provider or ai_provider()
    saved = str((_section("api").get("ai_base_urls") or {}).get(provider) or "").strip()
    return saved or AI_PROVIDERS[provider].get("base_url", "")


def ai_ready() -> bool:
    return any(ai_key(provider) for provider in AI_PROVIDERS)


# -- connected Google accounts --------------------------------------------------------
def load_profiles() -> list[dict]:
    profiles = load_settings().get("profiles")
    return [_relocate_profile(p) for p in profiles] if isinstance(profiles, list) else []


def save_profiles(profiles: list[dict]):
    settings = load_settings()
    settings["profiles"] = profiles
    save_settings(settings)
    log_event("accounts_saved", f"count={len(profiles)}")


# App-owned Chrome profiles hold Google login sessions, so from source they live outside the
# repository. The portable program keeps them in its own data folder next to the .exe.
_MANAGED_PROFILES_DIR = user_path("data", "chrome_profiles") if _FROZEN else os.path.join(
    os.getenv("LOCALAPPDATA") or user_path("data"),
    "MarketingAIAgent",
    "chrome_profiles",
)


def _relocate_profile(profile: dict) -> dict:
    """The program folder may have moved (another drive, USB): find its profile under the new folder."""
    path = profile.get("path") if isinstance(profile, dict) else None
    if path and not os.path.isdir(path):
        moved = os.path.join(_MANAGED_PROFILES_DIR, os.path.basename(os.path.normpath(path)))
        if os.path.isdir(moved):
            return {**profile, "path": moved}
    return profile


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
_ERROR_LOG_PATH = user_path("data", "error.log")
_ACTIVITY_LOG_PATH = user_path("data", "activity.log")


def _ensure_log_dir():
    os.makedirs(os.path.dirname(_ERROR_LOG_PATH), exist_ok=True)


def log_error(source: str, error: Exception, context: str = ""):
    """Append a timestamped error entry to data/error.log."""
    _ensure_log_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{source}] {type(error).__name__}: {error}"
    if context:
        line += f" | context: {context}"
    line = _mask_secrets(line)
    _append_line(_ERROR_LOG_PATH, line)
    _append_line(_ACTIVITY_LOG_PATH, line)


def log_event(source: str, message: str = ""):
    """Append what the app did to data/activity.log, the full record next to the error log."""
    _ensure_log_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _append_line(_ACTIVITY_LOG_PATH, _mask_secrets(f"[{timestamp}] [{source}] {message}"))


def _mask_secrets(line: str) -> str:
    # googleapiclient's HttpError includes the request URL, API key included.
    line = re.sub(r"(key=)[^&\s>]+", r"\1***", " ".join(line.split()))
    return re.sub(r"Bearer \S+|AIza[\w-]{20,}|\b(?:sk|gsk|csk|nvapi)[-_][\w-]{16,}", "***", line)


def _append_line(path: str, line: str):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


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

    # A profile directory holds Preferences itself; an app-owned user-data dir keeps it in Default/.
    profile_dir = profile_path.replace("/", os.sep)
    candidates = [os.path.join(profile_dir, "Preferences"), os.path.join(profile_dir, "Default", "Preferences")]
    prefs_path = next((p for p in candidates if os.path.isfile(p)), None)
    if not prefs_path:
        return result

    try:
        with open(prefs_path, encoding="utf-8") as f:
            prefs = json.load(f)

        account_info = prefs.get("account_info", [])
        if account_info and isinstance(account_info, list):
            first = account_info[0]
            result["name"] = first.get("full_name", "")
            result["email"] = first.get("email", "")
            result["picture"] = first.get("picture_url", "") or first.get(
                "last_downloaded_image_url_with_size", ""
            )
        # profile.name is not used: it is Chrome's own label (e.g. "내 Chrome"), not the Google name.
    except (json.JSONDecodeError, OSError, KeyError):
        pass

    return result
