"""YouTube Data API v3 integration module."""

import re
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config


def _get_service():
    """Build and return a YouTube API service client."""
    return build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)


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
    service = _get_service()
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

    response = service.search().list(**request_kwargs).execute()

    videos = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url", "")
        )
        videos.append({
            "videoId": item["id"]["videoId"],
            "title": snippet.get("title", ""),
            "channelTitle": snippet.get("channelTitle", ""),
            "publishedAt": snippet.get("publishedAt", ""),
            "thumbnail": thumbnail_url,
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
        service = _get_service()
        response = service.videos().list(
            id=video_id,
            part="snippet,statistics",
        ).execute()

        items = response.get("items", [])
        if not items:
            return None

        item = items[0]
        snippet = item["snippet"]
        statistics = item.get("statistics", {})
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url", "")
        )

        return {
            "videoId": video_id,
            "title": snippet.get("title", ""),
            "channelTitle": snippet.get("channelTitle", ""),
            "publishedAt": snippet.get("publishedAt", ""),
            "thumbnail": thumbnail_url,
            "description": snippet.get("description", ""),
            "viewCount": statistics.get("viewCount", "0"),
            "commentCount": statistics.get("commentCount", "0"),
        }

    except HttpError as e:
        config.log_error("get_video_details", e)
        return None
    except Exception as e:
        config.log_error("get_video_details", e)
        return None


def get_popular_comments(video_id: str, max_results: int = 10) -> list[dict]:
    """Get top comments for a video, sorted by relevance (likes).

    Returns a list of dicts with keys: text, likeCount, author
    """
    try:
        service = _get_service()
        response = service.commentThreads().list(
            videoId=video_id,
            part="snippet",
            maxResults=min(max_results, 100),
            order="relevance",
            textFormat="plainText",
        ).execute()

        comments = []
        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "text": top.get("textDisplay", ""),
                "likeCount": top.get("likeCount", 0),
                "author": top.get("authorDisplayName", ""),
            })
        return comments

    except HttpError as e:
        config.log_error("get_popular_comments", e)
        return []
    except Exception as e:
        config.log_error("get_popular_comments", e)
        return []


def get_video_captions(video_id: str) -> str | None:
    """Get Korean captions/transcript for a video.

    Tries youtube-transcript-api first. Falls back to the video description
    if the transcript library is unavailable or no Korean transcript exists.
    Returns None if nothing is available.
    """
    transcript = get_transcript(video_id)
    if transcript:
        return transcript

    # Fallback: return the video description
    try:
        details = get_video_details(video_id)
        if details and details.get("description"):
            return details["description"]
    except Exception:
        pass

    return None


def get_transcript(video_id: str) -> str | None:
    """The video's spoken transcript only (Korean, then auto-generated Korean, then English)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Prefer Korean, then auto-generated Korean, then any available
        transcript = None
        try:
            transcript = transcript_list.find_transcript(["ko"])
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(["ko"])
            except Exception:
                try:
                    transcript = transcript_list.find_transcript(["en"])
                except Exception:
                    pass

        if transcript:
            entries = transcript.fetch()
            text = " ".join(entry["text"] for entry in entries)
            return text.strip() if text.strip() else None

    except ImportError:
        pass  # youtube-transcript-api not installed
    except Exception as e:
        config.log_error("get_transcript", e, f"videoId={video_id}")

    return None


def search_trending_videos(keyword: str = "연애", max_results: int = 10) -> dict:
    """Search for videos that are about to trend.

    Criteria: 1,000~5,000 views uploaded within the last 24 hours,
    implying a growth rate of roughly 150+ views/hour.
    Returns the same dict shape as search_videos (with ``videos`` list and
    ``nextPageToken``).  Trending search does not paginate through YouTube
    API pages because it needs statistics filtering, so ``nextPageToken``
    is always ``None``.
    """
    try:
        from datetime import timedelta, timezone

        service = _get_service()
        after = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        response = (
            service.search()
            .list(
                q=keyword,
                part="snippet",
                type="video",
                maxResults=50,
                order="viewCount",
                regionCode="KR",
                relevanceLanguage="ko",
                publishedAfter=after,
            )
            .execute()
        )

        video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
        if not video_ids:
            return {"videos": [], "nextPageToken": None}

        stats_response = (
            service.videos()
            .list(id=",".join(video_ids), part="snippet,statistics")
            .execute()
        )

        now_utc = datetime.now(timezone.utc)
        results = []
        for item in stats_response.get("items", []):
            stats = item.get("statistics", {})
            snippet = item["snippet"]
            view_count = int(stats.get("viewCount", "0"))
            published = datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            )
            hours_since = max((now_utc - published).total_seconds() / 3600, 1)
            views_per_hour = view_count / hours_since

            if 1000 <= view_count <= 5000 and views_per_hour >= 150:
                thumbnails = snippet.get("thumbnails", {})
                thumbnail_url = (
                    thumbnails.get("high", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url", "")
                )
                results.append(
                    {
                        "videoId": item["id"],
                        "title": snippet.get("title", ""),
                        "channelTitle": snippet.get("channelTitle", ""),
                        "publishedAt": snippet.get("publishedAt", ""),
                        "thumbnail": thumbnail_url,
                        "description": snippet.get("description", ""),
                        "viewCount": str(view_count),
                        "viewsPerHour": round(views_per_hour),
                    }
                )

        results.sort(key=lambda v: v["viewsPerHour"], reverse=True)
        return {"videos": results[:max_results], "nextPageToken": None}

    except HttpError as e:
        config.log_error("search_trending_videos", e)
        return {"videos": [], "nextPageToken": None}
    except Exception as e:
        config.log_error("search_trending_videos", e)
        return {"videos": [], "nextPageToken": None}


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
