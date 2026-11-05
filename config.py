import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

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
