"""YouTube Data API v3 integration module."""

import re
from datetime import datetime

from googleapiclient.discovery import build

import config


def _get_service():
    """Build and return a YouTube API service client."""
    return build("youtube", "v3", developerKey=config.youtube_api_key())


def _execute(make_request):
    """Run make_request(service).execute(), riding out a short HTTPS interception window.

    Each try builds a new service, so a new httplib2.Http and a fresh TLS handshake.
    execute(num_retries=...) is not used: it reuses one Http and also retries 403/429 replies.
    HttpError replies (4xx/5xx) are raised at once.
    """
    return config.with_tls_retry(lambda: make_request(_get_service()).execute())


def _thumbnail_url(snippet: dict) -> str:
    thumbnails = snippet.get("thumbnails", {})
    return (
        thumbnails.get("high", {}).get("url")
        or thumbnails.get("medium", {}).get("url")
        or thumbnails.get("default", {}).get("url", "")
    )


def search_videos(
    keyword: str = "연애",
    max_results: int = 10,
    page_token: str | None = None,
) -> dict:
    """Search YouTube videos by keyword with pagination support.

    Args:
        keyword: Search query string.
        max_results: Number of results per page (default 10, max 50).
        page_token: Token for fetching the next page of results.

    Returns a dict with keys:
        videos        - list[dict] with videoId, title, channelTitle, etc.
        nextPageToken - str or None; pass to the next call for more results.
        totalResults  - YouTube's estimate of the total result count.

    Raises on API failure so the caller can log it and tell the user.
    """
    request_kwargs = dict(
        q=keyword,
        part="snippet",
        type="video",
        maxResults=min(max_results, 50),
        order="relevance",
        regionCode="KR",
        relevanceLanguage="ko",
    )
    if page_token:
        request_kwargs["pageToken"] = page_token

    response = _execute(lambda service: service.search().list(**request_kwargs))

    videos = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        videos.append({
            "videoId": item["id"]["videoId"],
            "title": snippet.get("title", ""),
            "channelTitle": snippet.get("channelTitle", ""),
            "publishedAt": snippet.get("publishedAt", ""),
            "thumbnail": _thumbnail_url(snippet),
            "description": snippet.get("description", ""),
        })

    return {
        "videos": videos,
        "nextPageToken": response.get("nextPageToken"),
        "totalResults": response.get("pageInfo", {}).get("totalResults", 0),
    }


def get_video_details(video_id: str) -> dict | None:
    """Get detailed information for a single video.

    Returns a dict with keys:
        videoId, title, channelTitle, publishedAt, thumbnail, description,
        viewCount, commentCount
    Returns None on failure.
    """
    try:
        response = _execute(lambda service: service.videos().list(
            id=video_id,
            part="snippet,statistics",
        ))

        items = response.get("items", [])
        if not items:
            return None

        item = items[0]
        snippet = item["snippet"]
        statistics = item.get("statistics", {})

        return {
            "videoId": video_id,
            "title": snippet.get("title", ""),
            "channelTitle": snippet.get("channelTitle", ""),
            "publishedAt": snippet.get("publishedAt", ""),
            "thumbnail": _thumbnail_url(snippet),
            "description": snippet.get("description", ""),
            "viewCount": statistics.get("viewCount", "0"),
            "commentCount": statistics.get("commentCount", "0"),
        }

    except Exception as e:
        if config.is_cert_failure(e):
            raise  # the caller logs it and tells the user about the interception, not a bad URL
        config.log_error("get_video_details", e)
        return None


def get_popular_comments(video_id: str, max_results: int = 10) -> list[dict]:
    """Get top comments for a video, sorted by relevance (likes).

    Returns a list of dicts with keys: text, likeCount, author
    """
    try:
        response = _execute(lambda service: service.commentThreads().list(
            videoId=video_id,
            part="snippet",
            maxResults=min(max_results, 100),
            order="relevance",
            textFormat="plainText",
        ))

        comments = []
        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "text": top.get("textDisplay", ""),
                "likeCount": top.get("likeCount", 0),
                "author": top.get("authorDisplayName", ""),
            })
        return comments

    except Exception as e:
        config.log_error("get_popular_comments", e)
        return []


def _clean_caption(text: str) -> str:
    """Drop auto-caption noise: speaker markers (>>) and sound tags like [음악]."""
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = text.replace(">>", " ")
    return re.sub(r"\s+", " ", text).strip()


def get_transcript(video_id: str) -> str | None:
    """The video's spoken captions only: Korean auto-generated (CC) first, then Korean
    uploaded captions, then any other track translated to Korean.

    Uses the youtube-transcript-api 1.x instance API (`list`, snippets with `.text`).
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return None

    # HTTPS here is sometimes intercepted for a few seconds (see config.with_tls_retry).
    # Captions are optional (the description stands in), so the retry is kept short.
    # A new YouTubeTranscriptApi per try means a new requests session and handshake.
    try:
        return config.with_tls_retry(lambda: _fetch_transcript(YouTubeTranscriptApi(), video_id),
                                     delays=(1.0, 2.0, 3.0))
    except Exception as e:
        config.log_error("get_transcript", e, f"videoId={video_id}")
        return None


def _fetch_transcript(api, video_id: str) -> str | None:
    transcripts = api.list(video_id)
    transcript = None
    for find in (transcripts.find_generated_transcript, transcripts.find_manually_created_transcript):
        try:
            transcript = find(["ko"])
            break
        except Exception:
            continue
    if transcript is None:
        first = next(iter(transcripts), None)
        if first is None:
            return None
        transcript = first.translate("ko") if first.is_translatable else first

    raw = " ".join(snippet.text for snippet in transcript.fetch())
    text = _clean_caption(raw)
    # Shorts with only a background song get auto-captions of the lyrics; those aren't what the video says
    if _MUSIC_TAG.search(raw) and len(text) < _MIN_SPEECH_CHARS:
        return None
    return text or None


_MUSIC_TAG = re.compile(r"\[(음악|노래|Music|music|♪)[^\]]*\]|♪")
_MIN_SPEECH_CHARS = 200


def extract_video_id(url: str) -> str | None:
    """Extract a YouTube video ID from various URL formats.

    Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/shorts/VIDEO_ID
        - Plain VIDEO_ID (11 characters)
    """
    if not url:
        return None

    url = url.strip()

    # Direct video ID (11 alphanumeric chars, hyphens, underscores)
    if re.match(r"^[A-Za-z0-9_-]{11}$", url):
        return url

    patterns = [
        r"(?:youtube\.com/watch\?.*v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def format_publish_date(published_at: str) -> str:
    """Format an ISO 8601 date string to a readable Korean format."""
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return published_at or ""


def format_view_count(count_str: str) -> str:
    """Format a view count number into a readable Korean string."""
    try:
        count = int(count_str)
        if count >= 100_000_000:
            return f"{count / 100_000_000:.1f}억회"
        if count >= 10_000:
            return f"{count / 10_000:.1f}만회"
        if count >= 1_000:
            return f"{count / 1_000:.1f}천회"
        return f"{count}회"
    except (ValueError, TypeError):
        return count_str or "0회"
