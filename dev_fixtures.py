"""Worst-case UI fixtures, loaded only by `streamlit run app.py -- --ui-dev`.

Fakes replace the data modules at the import boundary, so nothing here reaches
the real database, profile file, YouTube API or browser automation.
"""

import html
from datetime import date, timedelta

import streamlit as st

MODES = {"worst": "Worst case", "empty": "Empty", "one": "One"}

_LONG_EMAIL = "bartholomew.fitzgerald@northwind-industries-holdings.example.com"
_NOW = "2026-11-05T09:30:00Z"
_THUMB = "https://i.ytimg.com/vi/aqz-KE-bpKQ/hqdefault.jpg"
_BROKEN_THUMB = "https://example.invalid/broken-thumbnail.jpg"


def _video(video_id, title, channel="연애 상담소", thumb=_THUMB, published=_NOW, views="1284", comments="12"):
    return {
        "videoId": video_id,
        "title": title,
        "channelTitle": channel,
        "publishedAt": published,
        "thumbnail": thumb,
        "description": "설명 " * 300,
        "viewCount": views,
        "commentCount": comments,
    }


def _worst_videos():
    rows = [
        _video(
            "worst-long-",
            "헤어진지삼년된전남자친구에게서갑자기새벽세시에연락이왔는데이걸받아야할지말아야할지정말모르겠어서조언을구합니다결혼을앞두고있는데도요정말로요",
            channel="대한민국에서가장오래된연애상담및결혼정보전문채널공식유튜브계정입니다",
            views="1284567890",
            comments="1284567",
        ),
        _video("worst-html-", '<b>속보</b> & "연애" **마크다운** $100 vs $200 :red[색상] <img src=x> # 제목'),
        _video("worst-short", "J", channel="", thumb="", published="", views="0", comments="0"),
        _video("worst-broke", "썸네일 주소가 깨진 영상", thumb=_BROKEN_THUMB, views="1", comments="1"),
        _video("worstPosted", "이미 댓글을 게시한 영상입니다 — 선택할 수 없어야 합니다"),
        _video("worst-rtl--", "نور الهدى عبد الرحمن — كيف تعرف أنه يحبك؟", channel="نور الهدى"),
        _video("worst-emoji", "👩🏽‍💻💔🦊 연애 고민 " * 12),
        _video("worst-line-", "첫째 줄\n\n둘째 줄   공백이    많은   제목"),
        _video("worst-null-", "조회수가 없는 영상", channel="Aleksandra Wiśniewska-Kowalczyk", views=None, comments=None),
        _video("worst-viet-", "Đặng Thị Ngọc Hân — Tình yêu và hôn nhân"),
    ]
    page2 = [_video(f"worst-p2-{i:02d}", f"두 번째 페이지 영상 {i}") for i in range(10)]
    page3 = [_video(f"worst-p3-{i:02d}", f"마지막 페이지 영상 {i}") for i in range(3)]
    return [rows, page2, page3]


def _pages(mode):
    if mode == "worst":
        return _worst_videos()
    if mode == "one":
        return [[_video("one-video-1", "영상이 하나뿐인 검색 결과")]]
    return []


class _Proxy:
    def __init__(self, real, mode):
        self._real = real
        self._mode = mode

    def __getattr__(self, name):
        return getattr(self._real, name)


class FakeYouTube(_Proxy):
    def search_videos(self, keyword="연애", max_results=10, page_token=None):
        pages = _pages(self._mode)
        index = int(page_token) if page_token else 0
        if index >= len(pages):
            return {"videos": [], "nextPageToken": None, "totalResults": 0}
        # search.list returns HTML-escaped titles; videos.list does not.
        videos = [
            {**v, "title": html.escape(v["title"]), "channelTitle": html.escape(v["channelTitle"])}
            for v in pages[index]
        ]
        for v in videos:
            v.pop("viewCount")
            v.pop("commentCount")
        return {
            "videos": videos,
            "nextPageToken": str(index + 1) if index + 1 < len(pages) else None,
            "totalResults": sum(len(p) for p in pages),
        }

    def get_video_details(self, video_id):
        for page in _pages(self._mode):
            for video in page:
                if video["videoId"] == video_id:
                    return video
        return None

    def get_popular_comments(self, video_id, max_results=10):
        if self._mode != "worst":
            return []
        return [
            {"text": "ㅋ" * 300, "likeCount": 1284567, "author": "a"},
            {"text": "**굵게** <b>태그</b> $1 $2", "likeCount": 0, "author": ""},
        ]

    def get_video_captions(self, video_id):
        return None


class FakeDatabase(_Proxy):
    def today_count(self):
        return {"worst": 7, "one": 1}.get(self._mode, 0)

    def can_post(self, video_id):
        if video_id == "worstPosted":
            return False, "이 영상에는 이미 댓글을 달았습니다. (영상당 1개)"
        return True, ""

    def get_posted_video_ids(self):
        return {"worstPosted"} if self._mode == "worst" else set()

    def log_comment(self, *args, **kwargs):
        pass

    def get_history_by_date(self, target_date=None, limit=100):
        today = date.today()
        if self._mode == "empty":
            return []
        if target_date == today - timedelta(days=1):
            return [self._row("어제 날짜의 기록입니다", "날짜 이동 확인용 댓글", True, target_date)]
        if target_date != today:
            return []
        if self._mode == "one":
            return [self._row("기록이 하나뿐입니다", "짧은 댓글", True, today)]
        rows = [
            self._row(
                '<script>alert(1)</script> **제목** $100 vs $200 :red[색상]',
                "<b>굵은 태그</b> **마크다운** " + "아주 긴 댓글 내용입니다 " * 12,
                True,
                today,
            ),
            self._row(
                "실패한영상제목이아주아주길어서공백도없이계속이어지는경우입니다정말로요계속계속계속계속",
                "ㅎ" * 120,
                False,
                today,
                error=f"Timeout 30000ms exceeded waiting for selector ytd-comment-simplebox-renderer at {_LONG_EMAIL} " * 2,
            ),
            self._row("", "", True, today, profile_index=99),
        ]
        rows += [self._row(f"일반 기록 {i}", "보통 길이의 댓글입니다.", True, today) for i in range(40)]
        return rows[:limit]

    @staticmethod
    def _row(title, comment, success, day, error=None, profile_index=0):
        return {
            "video_id": "x",
            "video_title": title,
            "profile_index": profile_index,
            "comment": comment,
            "success": 1 if success else 0,
            "error": error,
            "created_at": f"{day.isoformat()} 09:30:00",
        }


class FakeConfig(_Proxy):
    YOUTUBE_API_KEY = "fixture"

    def __init__(self, real, mode):
        super().__init__(real, mode)
        self._profiles = {
            "worst": [
                {"name": "Aleksandra Wiśniewska-Kowalczyk Christopher Alexander Montgomery III", "email": _LONG_EMAIL,
                 "picture": "", "path": "C:/Users/Worst/AppData/Local/Google/Chrome/User Data/Profile 12"},
                {"name": "Jo", "email": "a@b.co", "picture": "", "path": ""},
                {"name": "👩🏽‍💻 Priya", "email": "first.last+billing-notifications@example.com",
                 "picture": _BROKEN_THUMB, "path": "Default"},
                {"name": "  Sam   Lee ", "email": "", "picture": "", "path": "Profile 1"},
                {"name": "", "email": "only.email@example.com", "picture": "", "path": "Profile 2"},
                {"name": "<b>태그</b> **이름**", "email": "ops@sub.department.region.example.co.uk",
                 "picture": "", "path": "Profile 3"},
                {"name": "نور الهدى عبد الرحمن", "email": "noor@example.org", "picture": "", "path": "Profile 4"},
            ],
            "one": [{"name": "Smartphone Test", "email": "test@example.com", "picture": "", "path": "Default"}],
        }.get(mode, [])

    def load_profiles(self):
        return list(self._profiles)

    def save_profiles(self, profiles):
        self._profiles = list(profiles)

    def read_chrome_profile_info(self, profile_path):
        return {"name": "", "email": "", "picture": ""}

    def detect_chrome_profiles(self):
        return []

    def find_chrome_profile_by_email(self, email):
        return ""

    def log_error(self, source, error, context=""):
        pass

    def read_error_log_by_date(self, target_date=None, limit=50):
        today = date.today()
        if self._mode == "empty":
            return []
        if target_date == today - timedelta(days=1):
            return [f"[{target_date.isoformat()} 09:30:00] [search_videos] 어제 날짜의 오류입니다"]
        if target_date != today:
            return []
        stamp = f"[{today.isoformat()} 09:30:00]"
        if self._mode == "one":
            return [f"{stamp} [search_videos] HttpError: quota exceeded"]
        return [
            f"{stamp} [post_comment] TimeoutError: " + "unbreakable_token_without_any_spaces_" * 12,
            f"{stamp} [search_videos] HttpError: <HttpError 403 when requesting https://youtube.googleapis.com/"
            f"youtube/v3/search?part=snippet&q=%EC%97%B0%EC%95%A0&maxResults=10 returned quotaExceeded> | context: "
            + "keyword=연애 " * 30,
            f"{stamp} [generate_comment] KeyError: **'choices'** <b>tag</b>",
        ]


class FakeBrowser(_Proxy):
    def get_available_profiles(self):
        names = ["Aleksandra Wiśniewska-Kowalczyk Christopher Alexander Montgomery III", "Jo"]
        return [{"index": i, "name": n, "path": "fixture"} for i, n in enumerate(names)]

    def post_comment(self, video_id, comment, profile_index, status_callback=None):
        return {"success": False, "error": "픽스처 모드에서는 게시하지 않습니다. " + "x" * 200}


class FakeAI(_Proxy):
    def generate_comment(self, title, description, captions, popular_comments):
        return {
            "concern": "상대방의연락이갑자기줄어들어서불안해하는고민이영상전체에걸쳐공백없이이어지고있습니다" * 3 + " **마크다운** $1 $2",
            "comment": "저도 비슷한 고민이 있었는데 운명원에서 상담받고 마음이 많이 편해졌어요. " * 2,
            "reasoning": "분석 근거 " * 80,
            "warning": "브랜드 언급이 너무 직접적일 수 있습니다. " * 6,
        }


def activate(mode, *modules):
    """Return fakes for (ai_comment, browser_automation, config, database, youtube_api)."""
    ai_comment, browser_automation, config, database, youtube_api = modules
    return (
        FakeAI(ai_comment, mode),
        FakeBrowser(browser_automation, mode),
        FakeConfig(config, mode),
        FakeDatabase(database, mode),
        FakeYouTube(youtube_api, mode),
    )


def render_toggle(active):
    def segment(label, href, is_active):
        style = "background:#fff;color:#111;" if is_active else "color:#555;"
        return (
            f'<a href="{href}" target="_self" style="{style}padding:4px 10px;border-radius:6px;'
            f'text-decoration:none;font:12px system-ui,sans-serif;">{label}</a>'
        )

    links = [segment("Real", "?", active is None)]
    links += [segment(label, f"?data={key}", active == key) for key, label in MODES.items()]
    st.markdown(
        '<div style="position:fixed;bottom:12px;left:50%;transform:translateX(-50%);z-index:999999;'
        'display:flex;gap:2px;padding:3px;background:#e5e5e5;border-radius:8px;white-space:nowrap;">'
        + "".join(links)
        + "</div>",
        unsafe_allow_html=True,
    )
