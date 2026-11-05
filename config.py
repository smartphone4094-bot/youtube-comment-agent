import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# OpenRouter 설정 (무료 모델 지원)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")

# Anthropic 설정 (유료, 선택)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 어떤 AI를 쓸지: "openrouter" 또는 "anthropic"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter")

CHROME_PROFILES = [
    p for p in [
        os.getenv("CHROME_PROFILE_1", ""),
        os.getenv("CHROME_PROFILE_2", ""),
        os.getenv("CHROME_PROFILE_3", ""),
    ] if p
]

DAILY_MAX_COMMENTS = int(os.getenv("DAILY_MAX_COMMENTS", "10"))
COMMENT_MIN_CHARS = int(os.getenv("COMMENT_MIN_CHARS", "40"))
COMMENT_MAX_CHARS = int(os.getenv("COMMENT_MAX_CHARS", "120"))
BRAND_NAME = os.getenv("BRAND_NAME", "운명원")
