"""YouTube Comment Agent Dashboard - Main Streamlit application (step-based wizard)."""

import html
import math
import re
import sys
from datetime import date, timedelta
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components

import ai_comment
import browser_automation
import config
import database
import youtube_api


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="마케팅AI 에이전트",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "--ui-dev" in sys.argv:
    import dev_fixtures

    _fixture_mode = st.query_params.get("data")
    if _fixture_mode in dev_fixtures.MODES:
        ai_comment, browser_automation, config, database, youtube_api = dev_fixtures.activate(
            _fixture_mode, ai_comment, browser_automation, config, database, youtube_api
        )
    dev_fixtures.render_toggle(_fixture_mode)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Colors derive from the inherited text color, so they hold in any Streamlit theme. */
    :root {
        --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
        --text-secondary: color-mix(in srgb, currentColor 62%, transparent);
        --hairline: rgba(128, 128, 128, 0.22);
        --fill: rgba(128, 128, 128, 0.12);
        --border-strong: rgba(128, 128, 128, 0.38);
        /* One accent, reserved for the main action on each screen */
        --accent: #E8484C;
        --accent-hover: #D33C40;
        --accent-ring: rgba(232, 72, 76, 0.28);
        --font-system: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Segoe UI",
            "Malgun Gothic", "Noto Sans KR", system-ui, sans-serif;
    }

    /* ── Page chrome ── */
    .stDeployButton,
    [data-testid="stToolbar"],
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    [data-testid="stHeader"] {
        background: transparent !important;
        pointer-events: none;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 960px;
        margin-inline: auto;
        padding-top: 3rem !important;
        padding-bottom: 6rem !important;
    }
    /* Breathing room between stacked elements */
    [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {
        gap: 1.1rem;
    }

    /* ── Typography: tracking and leading follow size ── */
    .stApp, .stApp *:not([data-testid="stIconMaterial"]):not(code):not(pre):not(.log-line):not(.log-line *) {
        font-family: var(--font-system) !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    .stApp h1 {
        font-size: clamp(1.75rem, 5vw, 2.5rem) !important;
        font-weight: 700 !important;
        line-height: 1.1 !important;
        letter-spacing: -0.02em;
        word-break: keep-all;
        overflow-wrap: anywhere;
    }
    .stApp h2, .stApp h3 {
        line-height: 1.25 !important;
        letter-spacing: -0.015em;
        word-break: keep-all;
    }
    .stApp h3 {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        padding-top: 0.75rem !important;
        padding-bottom: 0 !important;
    }
    /* Streamlit pulls the next element up under headings; let the block gap do the spacing */
    [data-testid="stHeading"] [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    [data-testid="stWidgetLabel"] p {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stMarkdownContainer"] {
        word-break: keep-all;
        overflow-wrap: anywhere;
    }

    /* ── Buttons: feedback lands on press, release settles ── */
    .stButton button,
    [data-testid="stPopover"] button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: transform 160ms var(--ease-out), background-color 150ms ease,
            border-color 150ms ease, color 150ms ease, box-shadow 150ms ease !important;
    }
    .stButton button {
        min-height: 44px;
        padding: 0.55rem 1.1rem !important;
    }
    .stButton button p {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
    }
    /* Primary: solid accent with a soft lift */
    .stButton button[kind="primary"] {
        background: var(--accent) !important;
        border: 1px solid var(--accent) !important;
        color: #fff !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(232, 72, 76, 0.22),
            inset 0 1px 0 rgba(255, 255, 255, 0.16);
    }
    @media (hover: hover) and (pointer: fine) {
        .stButton button[kind="primary"]:hover:not(:disabled) {
            background: var(--accent-hover) !important;
            border-color: var(--accent-hover) !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1), 0 4px 14px rgba(232, 72, 76, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.16);
        }
    }
    /* Secondary: a visible outline that fills on hover */
    .stButton button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid var(--border-strong) !important;
        color: inherit !important;
    }
    @media (hover: hover) and (pointer: fine) {
        .stButton button[kind="secondary"]:hover:not(:disabled) {
            background: var(--fill) !important;
            border-color: color-mix(in srgb, currentColor 45%, transparent) !important;
        }
    }
    .stButton button:focus-visible {
        outline: none !important;
        box-shadow: 0 0 0 3px var(--accent-ring) !important;
    }
    /* Disabled: clearly present, clearly unavailable */
    .stButton button:disabled {
        background: var(--fill) !important;
        border: 1px dashed var(--border-strong) !important;
        color: var(--text-secondary) !important;
        box-shadow: none !important;
        cursor: not-allowed;
        opacity: 1 !important;
    }
    .stButton button:active:not(:disabled),
    [data-testid="stPopover"] button:active:not(:disabled) {
        transform: scale(0.97);
        transition-duration: 60ms !important;
    }

    /* ── Inputs ── */
    [data-baseweb="input"],
    [data-baseweb="textarea"],
    [data-baseweb="select"] > div {
        border-radius: 10px !important;
    }
    [data-baseweb="input"]:focus-within,
    [data-baseweb="textarea"]:focus-within {
        box-shadow: 0 0 0 3px rgba(255, 75, 75, 0.16);
        transition: box-shadow 150ms ease;
    }

    hr {
        margin: 0.75rem 0 !important;
        border-color: var(--hairline) !important;
    }
    [data-testid="stExpander"] summary {
        padding-block: 0.8rem !important;
    }
    [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
        line-height: 1.65;
    }
    .stExpander details {
        border-radius: 12px !important;
        border-color: var(--hairline) !important;
    }
    [data-testid="stAlert"] > div {
        border-radius: 12px;
    }

    /* ── Video rows ── */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .thumb) {
        gap: 1.25rem;
    }
    .thumb {
        position: relative;
        aspect-ratio: 16 / 9;
        border-radius: 12px;
        overflow: hidden;
        background: var(--fill);
    }
    .thumb::before {
        content: "▶";
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        color: var(--text-secondary);
    }
    .bg-image {
        position: absolute;
        inset: 0;
        background-position: center;
        background-repeat: no-repeat;
        background-size: cover;
    }
    .video-title {
        font-size: 0.95rem;
        font-weight: 600;
        line-height: 1.35;
        margin-bottom: 4px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .video-title.full {
        font-size: 1.05rem;
        display: block;
    }
    .video-meta {
        font-size: 0.8rem;
        line-height: 1.5;
        color: var(--text-secondary);
        margin-bottom: 0.5rem;
        font-variant-numeric: tabular-nums;
    }
    .video-posted {
        font-size: 0.85rem;
        color: var(--text-secondary);
    }
    /* Row buttons sit short at the bottom-right of the card instead of spanning it */
    [class*="st-key-select_"],
    [class*="st-key-resume_"] {
        display: flex;
        justify-content: flex-end;
    }
    [class*="st-key-select_"] .stButton,
    [class*="st-key-resume_"] .stButton {
        width: auto !important;
        margin-left: auto;
    }
    /* Stretch the info column to the thumbnail's height so the button can sink to the bottom */
    [data-testid="stColumn"]:has(> [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] > :is([class*="st-key-select_"], [class*="st-key-resume_"])) {
        align-self: stretch;
    }
    [data-testid="stColumn"]:has(> [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] > :is([class*="st-key-select_"], [class*="st-key-resume_"])) > [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stColumn"]:has(> [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] > :is([class*="st-key-select_"], [class*="st-key-resume_"])) > [data-testid="stVerticalBlockBorderWrapper"] > div,
    [data-testid="stVerticalBlock"]:has(> :is([class*="st-key-select_"], [class*="st-key-resume_"])) {
        height: 100%;
    }
    [class*="st-key-select_"],
    [class*="st-key-resume_"] {
        margin-top: auto;
    }
    [class*="st-key-select_"] button {
        min-width: 96px;
        padding-inline: 1.4rem !important;
    }

    /* ── Status badge ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
    }
    .status-ok { background-color: #d4edda; color: #155724; }
    .status-warn { background-color: #fff3cd; color: #856404; }
    .status-full { background-color: #f8d7da; color: #721c24; }
    [data-testid="stHorizontalBlock"]:has(.status-badge) {
        flex-wrap: nowrap !important;
        align-items: center;
    }
    [data-testid="stHorizontalBlock"]:has(.status-badge) > [data-testid="stColumn"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0 !important;
    }
    [data-testid="stHorizontalBlock"]:has(.status-badge) > [data-testid="stColumn"]:last-child {
        flex: 0 0 6.5rem !important;
    }
    [data-testid="stPopover"] button,
    [data-testid="stPopover"] button * {
        white-space: nowrap;
    }

    /* ── Step indicator: a translucent layer content scrolls beneath ── */
    [data-testid="stElementContainer"]:has(.step-bar) {
        position: sticky;
        top: 0.75rem;
        z-index: 30;
        pointer-events: none;
    }
    .step-bar {
        display: flex;
        width: fit-content;
        max-width: 100%;
        align-items: center;
        gap: 4px;
        margin: 0.75rem auto 1rem;
        padding: 5px;
        background: color-mix(in srgb, Canvas 72%, transparent);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        backdrop-filter: blur(20px) saturate(180%);
        border-radius: 999px;
        box-shadow: 0 0 0 1px var(--hairline);
    }
    .step-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 16px 6px 7px;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--text-secondary);
        white-space: nowrap;
        transition: background-color 200ms var(--ease-out), color 200ms var(--ease-out);
    }
    /* Neutral ink for "you are here", so the accent stays on the action buttons */
    .step-item.active {
        background: CanvasText;
        color: Canvas;
        font-weight: 600;
    }
    .step-item.completed {
        color: #28a745;
    }
    .step-connector {
        width: 10px;
        height: 2px;
        border-radius: 999px;
        background: var(--hairline);
        flex-shrink: 0;
    }
    .step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        font-size: 0.75rem;
        font-weight: 600;
        background: var(--fill);
        flex-shrink: 0;
        font-variant-numeric: tabular-nums;
    }
    .step-item.active .step-num {
        background: Canvas;
        color: CanvasText;
    }
    .step-item.completed .step-num {
        background: #28a745;
        color: #fff;
    }
    @media (max-width: 480px) {
        .step-item:not(.active) { padding: 6px 7px; }
        .step-item:not(.active) .step-label { display: none; }
    }

    /* ── Profile popover: its transform is the position, so it must not be animated ── */
    [data-testid="stPopover"] button {
        border-radius: 20px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    [data-testid="stPopoverBody"] {
        width: min(420px, calc(100vw - 24px)) !important;
        min-width: 0 !important;
        max-width: calc(100vw - 24px) !important;
        border-radius: 14px !important;
        box-shadow: 0 10px 38px rgba(0, 0, 0, 0.14), 0 4px 12px rgba(0, 0, 0, 0.08) !important;
    }
    .profile-popover-header {
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 2px;
    }
    .profile-popover-hint {
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin-bottom: 12px;
        line-height: 1.55;
    }
    .profile-item-divider {
        border: none;
        border-top: 1px solid var(--hairline);
        margin: 10px 0 8px 0 !important;
    }
    .profile-empty-state {
        text-align: center;
        padding: 20px 8px;
        color: var(--text-secondary);
        font-size: 0.875rem;
    }
    [data-testid="stPopoverBody"] [data-testid="stHorizontalBlock"]:has(.profile-account-card) {
        flex-wrap: nowrap !important;
        align-items: center;
    }
    [data-testid="stPopoverBody"] [data-testid="stHorizontalBlock"]:has(.profile-account-card) > [data-testid="stColumn"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0 !important;
    }
    [data-testid="stPopoverBody"] [data-testid="stHorizontalBlock"]:has(.profile-account-card) > [data-testid="stColumn"]:last-child {
        flex: 0 0 2.75rem !important;
    }
    .profile-account-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px;
        border-radius: 10px;
        transition: background-color 150ms ease;
    }
    @media (hover: hover) and (pointer: fine) {
        .profile-account-card:hover {
            background: var(--fill);
        }
    }
    .profile-avatar {
        position: relative;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        font-weight: 600;
        color: #fff;
        flex-shrink: 0;
    }
    .profile-avatar.color-1 { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .profile-avatar.color-2 { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .profile-avatar.color-3 { background: linear-gradient(135deg, #4facfe 0%, #00a8e8 100%); }
    .profile-avatar.color-4 { background: linear-gradient(135deg, #2bb673 0%, #1fa2a2 100%); }
    .profile-avatar.color-5 { background: linear-gradient(135deg, #fa709a 0%, #f5a623 100%); }
    .profile-account-info {
        flex: 1;
        min-width: 0;
    }
    .profile-account-name,
    .profile-account-email {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .profile-account-name {
        font-size: 0.9rem;
        font-weight: 600;
    }
    .profile-account-email {
        font-size: 0.8rem;
        color: var(--text-secondary);
    }

    /* ── Pagination ── */
    [data-testid="stHorizontalBlock"]:has(.pagination-info) {
        flex-wrap: nowrap !important;
        align-items: center;
    }
    [data-testid="stHorizontalBlock"]:has(.pagination-info) > [data-testid="stColumn"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0 !important;
    }
    .pagination-info {
        font-size: 0.9rem;
        font-weight: 500;
        color: var(--text-secondary);
        text-align: center;
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
    }

    /* ── Dialogs: dim to focus, surface materializes ── */
    [data-testid="stDialog"] {
        background: transparent !important;
        -webkit-backdrop-filter: blur(6px) saturate(140%);
        backdrop-filter: blur(6px) saturate(140%);
    }
    [data-testid="stDialog"] > div {
        background: rgba(0, 0, 0, 0.38) !important;
    }
    [data-testid="stDialog"] [role="dialog"] {
        border-radius: 18px;
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28), 0 6px 18px rgba(0, 0, 0, 0.12);
        animation: surface-in 220ms var(--ease-out);
    }
    [role="dialog"] [data-testid="stVerticalBlock"] {
        width: 100% !important;
    }
    [role="dialog"] [data-testid="stHorizontalBlock"]:has(.stDateInput) {
        flex-wrap: nowrap !important;
        align-items: center;
        gap: 0.5rem;
    }
    [role="dialog"] [data-testid="stHorizontalBlock"]:has(.stDateInput) > [data-testid="stColumn"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 0 0 3rem !important;
    }
    [role="dialog"] [data-testid="stHorizontalBlock"]:has(.stDateInput) > [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 0 !important;
    }
    .dialog-count {
        font-size: 0.8rem;
        color: var(--text-secondary);
        font-variant-numeric: tabular-nums;
    }
    .record {
        padding: 12px 0;
        border-bottom: 1px solid var(--hairline);
    }
    .record:last-child {
        border-bottom: none;
    }
    .record-title {
        display: flex;
        gap: 6px;
        font-size: 0.92rem;
        font-weight: 600;
        line-height: 1.35;
    }
    .record-meta {
        font-size: 0.78rem;
        color: var(--text-secondary);
        margin: 2px 0 4px;
        font-variant-numeric: tabular-nums;
    }
    .record-comment {
        font-size: 0.875rem;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .record-error {
        font-size: 0.8rem;
        line-height: 1.5;
        color: #dc3545;
        margin-top: 4px;
    }
    .log-line {
        font-family: ui-monospace, SFMono-Regular, Consolas, "Malgun Gothic", monospace;
        font-size: 0.78rem;
        line-height: 1.55;
        padding: 10px 0;
        word-break: normal;
        overflow-wrap: anywhere;
        border-bottom: 1px solid var(--hairline);
    }
    .log-line:last-child {
        border-bottom: none;
    }

    @keyframes surface-in {
        from { opacity: 0; transform: scale(0.97); }
        to { opacity: 1; transform: scale(1); }
    }
    @keyframes surface-fade {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    /* ── Accessibility preferences ── */
    @media (prefers-reduced-motion: reduce) {
        .stButton button:active:not(:disabled),
        [data-testid="stPopover"] button:active:not(:disabled) {
            transform: none;
        }
        [data-testid="stDialog"] [role="dialog"] {
            animation: surface-fade 150ms ease;
        }
    }
    @media (prefers-reduced-transparency: reduce) {
        .step-bar,
        [data-testid="stDialog"] {
            -webkit-backdrop-filter: none;
            backdrop-filter: none;
        }
        .step-bar {
            background: Canvas;
        }
        [data-testid="stDialog"] > div {
            background: rgba(0, 0, 0, 0.6) !important;
        }
    }
    @media (prefers-contrast: more) {
        :root {
            --text-secondary: currentColor;
            --hairline: currentColor;
        }
        .step-bar {
            border: 1px solid currentColor;
        }
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
defaults = {
    "videos": [],
    "selected_video": None,
    "search_keyword": "연애",
    "last_search": "",
    "current_step": 1,
    "ai_result": None,
    "confirmed_comment": None,
    "edited_comment": "",
    "posting_status": None,
    "post_result": None,
    # Pagination state
    "search_current_page": 1,
    "search_page_tokens": {},      # {page_number: nextPageToken}
    "search_pages_cache": {},      # {page_number: list[dict]}
    "search_total_results": 0,
    "search_has_more": False,
    "search_mode": "",             # "search" or "trending"
    "login_notice": None,          # (st.toast | st.warning | st.error name, message)
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ---------------------------------------------------------------------------
# Helper: go to a step
# ---------------------------------------------------------------------------
def go_to_step(step: int):
    st.session_state.current_step = step
    st.rerun()


# ---------------------------------------------------------------------------
# Helpers: rendering untrusted text
# ---------------------------------------------------------------------------
def _clean(text) -> str:
    """Single-line HTML-safe text. search.list titles arrive entity-encoded, videos.list titles don't."""
    return html.escape(" ".join(html.unescape(str(text or "")).split()))


def _plain_md(text) -> str:
    """Escape Markdown, LaTeX ($) and Streamlit directives so data renders literally."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!$:~<>|])", r"\\\1", str(text or ""))


def _background_image(url) -> str:
    # A CSS background shows nothing when the URL fails; <img> would paint a broken-image icon.
    safe_url = quote(html.unescape(url or ""), safe=":/?&=%#~@+,;")
    return f'<div class="bg-image" style="background-image:url(&quot;{safe_url}&quot;)"></div>' if url else ""


def _thumb_html(url) -> str:
    return f'<div class="thumb">{_background_image(url)}</div>'


def _video_meta(*parts) -> str:
    return " &middot; ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Google login
# ---------------------------------------------------------------------------
def _google_login_button(location: str):
    if browser_automation.google_login_status():
        st.button("로그인 진행 중…", key=f"google_login_{location}", use_container_width=True, disabled=True)
        return
    if st.button(
        "Google 계정으로 로그인",
        key=f"google_login_{location}",
        use_container_width=True,
        type="primary",
        icon=":material/login:",
    ):
        try:
            browser_automation.start_google_login()
        except Exception as e:
            config.log_error("start_google_login", e)
            st.session_state.login_notice = (
                "error", "Chrome을 열 수 없습니다. Google Chrome이 설치되어 있는지 확인해주세요."
            )
        st.rerun()


def _save_google_account(account: dict):
    profiles = st.session_state.profiles_list
    for i, profile in enumerate(profiles):
        if account["email"] and profile.get("email", "").lower() == account["email"].lower():
            config.remove_managed_profile(profile.get("path", ""))
            profiles[i] = account
            break
    else:
        profiles.append(account)
    config.save_profiles(profiles)


def _finish_google_login():
    with st.spinner("계정 정보를 확인하는 중..."):
        try:
            account = browser_automation.finish_google_login()
        except Exception as e:
            config.log_error("finish_google_login", e)
            st.session_state.login_notice = ("error", "계정 정보를 확인하지 못했습니다. 다시 로그인해주세요.")
            return
    if not account:
        st.session_state.login_notice = (
            "warning", "로그인이 확인되지 않아 계정을 연결하지 않았습니다. 로그인한 뒤 Chrome 창을 닫아주세요."
        )
        return
    _save_google_account(account)
    label = _plain_md(account["name"] or account["email"])
    st.session_state.login_notice = ("toast", f"{label} 계정이 연결되었습니다.")


@st.fragment(run_every=2)
def _google_login_watcher():
    if browser_automation.google_login_status() != "open":
        _finish_google_login()
        st.rerun()
    message_col, cancel_col = st.columns([5, 1])
    with message_col:
        st.info("열린 Chrome 창에서 Google에 로그인한 뒤, **그 창을 닫으면** 계정이 연결됩니다.")
    with cancel_col:
        if st.button("취소", key="cancel_google_login", use_container_width=True):
            browser_automation.cancel_google_login()
            st.rerun()


@st.dialog("로그인이 필요합니다")
def show_login_required_dialog():
    st.markdown("댓글을 게시하려면 Google 계정을 먼저 연결해야 합니다.")
    _google_login_button("dialog")


# ---------------------------------------------------------------------------
# Initialize Chrome profiles & Header with profile popover
# ---------------------------------------------------------------------------
if "profiles_list" not in st.session_state:
    st.session_state.profiles_list = config.load_profiles()

st.title("마케팅AI 에이전트 (운명원)")

# Profile popover placed next to the daily comment badge below the title
_profiles_list = st.session_state.profiles_list
_profile_count = len(_profiles_list)

# Today's comment count / daily limit
posted_today = database.today_count()
daily_max = config.DAILY_MAX_COMMENTS
remaining = max(0, daily_max - posted_today)

if remaining == 0:
    badge_class = "status-full"
    badge_text = f"오늘 댓글 {posted_today}/{daily_max} (한도 초과)"
elif remaining <= 3:
    badge_class = "status-warn"
    badge_text = f"오늘 댓글 {posted_today}/{daily_max} (잔여 {remaining}개)"
else:
    badge_class = "status-ok"
    badge_text = f"오늘 댓글 {posted_today}/{daily_max} (잔여 {remaining}개)"

_badge_col, _profile_col = st.columns([6, 1])
with _badge_col:
    st.markdown(
        f'<span class="status-badge {badge_class}">{badge_text}</span>',
        unsafe_allow_html=True,
    )
with _profile_col:
    profiles_list = _profiles_list
    with st.popover(f"👤 {_profile_count}", use_container_width=True):
        st.markdown(
            '<div class="profile-popover-header">Google 계정 관리</div>'
            '<div class="profile-popover-hint">'
            '댓글 게시에 사용할 Google 계정을 연결하세요.<br>'
            '버튼을 누르면 Chrome에서 Google 로그인 페이지가 열립니다.'
            '</div>',
            unsafe_allow_html=True,
        )

        # --- Connected accounts list ---
        if not profiles_list:
            st.markdown(
                '<div class="profile-empty-state">'
                '연결된 계정이 없습니다.<br>'
                '아래 버튼으로 Google에 로그인해주세요.'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            for i, profile in enumerate(profiles_list):
                p_path = profile.get("path", "")

                # Enrich with live Chrome Preferences data when path exists
                chrome_info = config.read_chrome_profile_info(p_path)
                p_name = (chrome_info["name"] or profile.get("name", "")).strip()
                p_email = (chrome_info["email"] or profile.get("email", "")).strip()
                p_picture = chrome_info["picture"] or profile.get("picture", "")

                primary = p_name or p_email or "이름 없음"
                secondary = p_email if p_name else ""
                avatar_letter = html.escape(primary[0].upper())
                color_class = f"color-{(i % 5) + 1}"
                # The letter sits beneath the image, so a broken picture falls back to it.
                avatar_html = (
                    f'<div class="profile-avatar {color_class}">'
                    f'{avatar_letter}{_background_image(p_picture)}</div>'
                )

                email_line = (
                    f'<div class="profile-account-email" title="{_clean(secondary)}">'
                    f'<bdi>{_clean(secondary)}</bdi></div>'
                    if secondary else ""
                )

                card_col, del_col = st.columns([6, 1])
                with card_col:
                    st.markdown(
                        f'<div class="profile-account-card">'
                        f'{avatar_html}'
                        f'<div class="profile-account-info">'
                        f'<div class="profile-account-name" title="{_clean(primary)}">'
                        f'<bdi>{_clean(primary)}</bdi></div>'
                        f'{email_line}'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                with del_col:
                    if st.button("✕", key=f"pdel_{i}", help="계정 연결 해제"):
                        profiles_list.pop(i)
                        config.save_profiles(profiles_list)
                        config.remove_managed_profile(p_path)
                        st.session_state.profiles_list = profiles_list
                        st.rerun()

                if i < len(profiles_list) - 1:
                    st.markdown(
                        '<hr class="profile-item-divider">',
                        unsafe_allow_html=True,
                    )

        st.markdown('<hr class="profile-item-divider">', unsafe_allow_html=True)

        _google_login_button("popover")


if browser_automation.google_login_status():
    _google_login_watcher()

if st.session_state.login_notice:
    _notice_kind, _notice_message = st.session_state.login_notice
    st.session_state.login_notice = None
    getattr(st, _notice_kind)(_notice_message)


# ---------------------------------------------------------------------------
# Step indicator bar
# ---------------------------------------------------------------------------
current = st.session_state.current_step
step_labels = ["영상 선택", "댓글 생성", "댓글 게시"]

step_html_parts = []
for i, label in enumerate(step_labels, start=1):
    if i < current:
        cls = "completed"
        num_inner = "&#10003;"  # checkmark
    elif i == current:
        cls = "active"
        num_inner = str(i)
    else:
        cls = ""
        num_inner = str(i)

    step_html_parts.append(
        f'<div class="step-item {cls}">'
        f'<span class="step-num">{num_inner}</span>'
        f'<span class="step-label">{label}</span></div>'
    )
    if i < len(step_labels):
        step_html_parts.append('<span class="step-connector"></span>')

st.markdown(
    '<div class="step-bar">' + "".join(step_html_parts) + "</div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helper: reset pagination state for a fresh search
# ---------------------------------------------------------------------------
def _reset_pagination():
    st.session_state.search_current_page = 1
    st.session_state.search_page_tokens = {}
    st.session_state.search_pages_cache = {}
    st.session_state.search_total_results = 0
    st.session_state.search_has_more = False
    st.session_state.search_mode = ""


def _scroll_to_top():
    # The nonce changes the iframe's content so the script runs again on every page turn.
    st.session_state.scroll_nonce = st.session_state.get("scroll_nonce", 0) + 1
    components.html(
        f"""<script>
        // nonce {st.session_state.scroll_nonce}
        const doc = window.parent.document;
        doc.querySelectorAll('[data-testid="stMain"], [data-testid="stAppViewContainer"], section.main')
            .forEach(el => el.scrollTo({{top: 0, behavior: "smooth"}}));
        window.parent.scrollTo({{top: 0, behavior: "smooth"}});
        </script>""",
        height=0,
    )


def _select_video(video: dict):
    with st.spinner("상세 정보 로딩 중..."):
        try:
            st.session_state.selected_video = youtube_api.get_video_details(video["videoId"]) or video
        except Exception as e:
            config.log_error("get_video_details", e, f"videoId={video.get('videoId')}")
            st.session_state.selected_video = video
    # A new video invalidates anything generated for the previous one.
    st.session_state.ai_result = None
    st.session_state.confirmed_comment = None
    st.session_state.edited_comment = ""
    go_to_step(2)


# ===========================================================================
# Step 1: 영상 불러오기
# ===========================================================================
if current == 1:
    st.subheader("영상 불러오기")

    # --- Keyword search ---
    keyword = st.text_input(
        "검색 키워드",
        value=st.session_state.search_keyword,
        placeholder="예: 연애, 결혼, 소개팅 ...",
        key="keyword_input",
    )

    search_clicked = st.button(
        "🔍 영상 불러오기", use_container_width=True, type="primary"
    )

    if search_clicked:
        if not config.YOUTUBE_API_KEY:
            st.error("YouTube API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        elif not keyword.strip():
            st.warning("검색 키워드를 입력해주세요.")
        else:
            st.session_state.search_keyword = keyword.strip()
            _reset_pagination()
            with st.spinner("영상을 검색하고 있습니다..."):
                try:
                    result = youtube_api.search_videos(
                        keyword=keyword.strip(), max_results=10
                    )
                    videos_page = result.get("videos", [])
                    next_token = result.get("nextPageToken")

                    if videos_page:
                        st.session_state.videos = videos_page
                        st.session_state.search_pages_cache[1] = videos_page
                        st.session_state.search_current_page = 1
                        st.session_state.search_mode = "search"
                        st.session_state.search_total_results = result.get("totalResults", 0)
                        if next_token:
                            st.session_state.search_page_tokens[2] = next_token
                            st.session_state.search_has_more = True
                        st.session_state.last_search = keyword.strip()
                        st.toast(
                            f"'{keyword.strip()}' 검색 결과 {len(videos_page)}개를 불러왔습니다."
                        )
                    else:
                        st.session_state.videos = []
                        st.warning("검색 결과가 없습니다. 다른 키워드를 시도해주세요.")
                except Exception as e:
                    config.log_error("search_videos", e, f"keyword={keyword.strip()}")
                    st.error("검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

    # --- URL direct input ---
    st.markdown("")
    with st.expander("URL로 직접 불러오기", expanded=False):
        url_input = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            key="url_input",
        )
        if st.button("URL로 불러오기", use_container_width=True, key="btn_url"):
            if not config.YOUTUBE_API_KEY:
                st.error("YouTube API 키가 설정되지 않았습니다.")
            elif not url_input.strip():
                st.warning("URL을 입력해주세요.")
            else:
                vid = youtube_api.extract_video_id(url_input.strip())
                if not vid:
                    st.error("유효한 YouTube URL이 아닙니다.")
                elif vid in database.get_posted_video_ids():
                    st.error("이미 댓글을 게시한 영상이라 선택할 수 없습니다.")
                elif not st.session_state.profiles_list:
                    show_login_required_dialog()
                else:
                    with st.spinner("영상 정보를 불러오는 중..."):
                        try:
                            details = youtube_api.get_video_details(vid)
                            if details:
                                st.session_state.selected_video = details
                                st.session_state.ai_result = None
                                st.session_state.confirmed_comment = None
                                st.session_state.edited_comment = ""
                                go_to_step(2)
                            else:
                                st.error(
                                    "영상 정보를 불러올 수 없습니다. URL을 확인해주세요."
                                )
                        except Exception as e:
                            config.log_error("get_video_details", e, f"url={url_input}")
                            st.error("영상 정보를 불러오는 중 오류가 발생했습니다.")

    # --- Video list with pagination ---
    st.markdown("")
    cur_page = st.session_state.search_current_page
    videos = st.session_state.search_pages_cache.get(cur_page, st.session_state.videos)

    if videos:
        posted_ids = database.get_posted_video_ids()
        total_cached = len(st.session_state.search_pages_cache)
        has_more = st.session_state.search_has_more
        if st.session_state.last_search:
            page_label = f" (페이지 {cur_page})" if total_cached > 1 or has_more else ""
            st.caption(
                f"{_plain_md(st.session_state.last_search)} 검색 결과 ({len(videos)}개){page_label}"
            )

        for idx, video in enumerate(videos):
            published = youtube_api.format_publish_date(video.get("publishedAt", ""))
            channel = _clean(video.get("channelTitle"))
            title = _clean(video.get("title")) or "제목 없음"
            thumb = video.get("thumbnail", "")

            is_selected = (
                st.session_state.selected_video
                and st.session_state.selected_video.get("videoId")
                == video.get("videoId")
            )

            with st.container():
                c_img, c_info = st.columns([1, 3])
                with c_img:
                    st.markdown(_thumb_html(thumb), unsafe_allow_html=True)
                with c_info:
                    views_text = (
                        f"조회수 {youtube_api.format_view_count(video.get('viewCount', '0'))}"
                        if video.get("viewCount")
                        else ""
                    )
                    meta = _video_meta(f"<bdi>{channel}</bdi>" if channel else "", published, views_text)
                    st.markdown(
                        f'<div class="video-title" title="{title}"><bdi>{title}</bdi></div>'
                        f'<div class="video-meta">{meta}</div>',
                        unsafe_allow_html=True,
                    )

                    already_posted = video.get("videoId") in posted_ids
                    if already_posted:
                        st.markdown(
                            '<div class="video-posted">✅ 댓글 게시 완료</div>',
                            unsafe_allow_html=True,
                        )
                    elif is_selected:
                        if st.button(
                            "선택됨 · 이어서 진행",
                            key=f"resume_{cur_page}_{idx}",
                            type="primary",
                            icon=":material/arrow_forward:",
                        ):
                            go_to_step(2)
                    else:
                        if st.button(
                            "선택",
                            key=f"select_{cur_page}_{idx}",
                            type="primary",
                        ):
                            if st.session_state.profiles_list:
                                _select_video(video)
                            else:
                                show_login_required_dialog()

                st.divider()

        if st.session_state.pop("scroll_to_top", False):
            _scroll_to_top()

        # --- Pagination controls ---
        can_prev = cur_page > 1
        can_next = (
            st.session_state.search_has_more
            and cur_page < 10  # Max 10 pages (100 results)
        )
        if can_prev or can_next:
            pag_prev, pag_info, pag_next = st.columns([1, 2, 1])
            with pag_prev:
                if st.button(
                    "← 이전",
                    disabled=not can_prev,
                    use_container_width=True,
                    key="page_prev",
                ):
                    st.session_state.search_current_page = cur_page - 1
                    prev_cached = st.session_state.search_pages_cache.get(cur_page - 1)
                    if prev_cached:
                        st.session_state.videos = prev_cached
                    st.session_state.scroll_to_top = True
                    st.rerun()
            with pag_info:
                # totalResults is YouTube's estimate; the count corrects once the last page loads.
                estimated_pages = min(10, math.ceil(st.session_state.search_total_results / 10))
                max_page = max(estimated_pages, cur_page + 1) if has_more else total_cached
                st.markdown(
                    f'<div class="pagination-info">{cur_page} / {max_page}</div>',
                    unsafe_allow_html=True,
                )
            with pag_next:
                if st.button(
                    "다음 →",
                    disabled=not can_next,
                    use_container_width=True,
                    key="page_next",
                ):
                    next_page = cur_page + 1
                    st.session_state.scroll_to_top = True
                    # Check cache first
                    if next_page in st.session_state.search_pages_cache:
                        st.session_state.search_current_page = next_page
                        st.session_state.videos = st.session_state.search_pages_cache[next_page]
                        st.rerun()
                    else:
                        # Fetch next page from YouTube API
                        token = st.session_state.search_page_tokens.get(next_page)
                        if token:
                            with st.spinner("다음 페이지를 불러오는 중..."):
                                try:
                                    result = youtube_api.search_videos(
                                        keyword=st.session_state.search_keyword,
                                        max_results=10,
                                        page_token=token,
                                    )
                                    new_videos = result.get("videos", [])
                                    new_next_token = result.get("nextPageToken")
                                    if new_videos:
                                        st.session_state.search_pages_cache[next_page] = new_videos
                                        st.session_state.search_current_page = next_page
                                        st.session_state.videos = new_videos
                                        if new_next_token and next_page < 10:
                                            st.session_state.search_page_tokens[next_page + 1] = new_next_token
                                            st.session_state.search_has_more = True
                                        else:
                                            st.session_state.search_has_more = False
                                    else:
                                        st.session_state.search_has_more = False
                                        st.toast("더 이상 검색 결과가 없습니다.")
                                except Exception as e:
                                    config.log_error("search_videos_page", e, f"page={next_page}")
                                    st.error("다음 페이지를 불러오는 중 오류가 발생했습니다.")
                            st.rerun()
                        else:
                            st.session_state.search_has_more = False
                            st.toast("더 이상 검색 결과가 없습니다.")
    elif not search_clicked:
        st.info("키워드를 입력하고 '영상 불러오기' 버튼을 눌러주세요.")


# ===========================================================================
# Step 2: 영상 분석 + 댓글 초안
# ===========================================================================
elif current == 2:
    # Guard: need a selected video
    if not st.session_state.selected_video:
        st.warning("선택된 영상이 없습니다. 영상을 먼저 선택해주세요.")
        go_to_step(1)

    sv = st.session_state.selected_video
    video_id = sv.get("videoId", "")

    # Back button
    if st.button("← 영상 다시 선택", key="back_to_step1"):
        go_to_step(1)

    st.subheader("영상 분석 + 댓글 초안")

    # -- Selected video info (prominent) --
    thumb = sv.get("thumbnail", "")
    v_title = _clean(sv.get("title")) or "제목 없음"
    v_channel = _clean(sv.get("channelTitle"))
    v_views = youtube_api.format_view_count(sv.get("viewCount") or "0")
    v_comments = youtube_api.format_view_count(sv.get("commentCount") or "0")

    col_thumb, col_info = st.columns([1, 3])
    with col_thumb:
        st.markdown(_thumb_html(thumb), unsafe_allow_html=True)
    with col_info:
        v_meta = _video_meta(
            f"<bdi>{v_channel}</bdi>" if v_channel else "",
            f"조회수 {v_views}",
            f"댓글 {v_comments}",
        )
        st.markdown(
            f'<div class="video-title full"><bdi>{v_title}</bdi></div>'
            f'<div class="video-meta">{v_meta}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # -- Generate / Regenerate buttons --
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        generate_clicked = st.button(
            "✨ 댓글 생성" if not st.session_state.ai_result else "🔄 다시 생성",
            use_container_width=True,
            type="primary",
        )
    with btn_col2:
        confirm_clicked = st.button(
            "✅ 댓글 확정",
            use_container_width=True,
            disabled=st.session_state.ai_result is None,
        )

    # -- AI generation logic --
    if generate_clicked:
        with st.spinner("영상을 분석하고 댓글을 생성하는 중..."):
            try:
                captions = youtube_api.get_video_captions(video_id)
                popular_comments = youtube_api.get_popular_comments(video_id)
                result = ai_comment.generate_comment(
                    title=sv.get("title", ""),
                    description=sv.get("description", ""),
                    captions=captions,
                    popular_comments=popular_comments,
                )
                st.session_state.ai_result = result
                st.session_state.ai_result["_popular_comments"] = popular_comments
                st.session_state.edited_comment = result.get("comment", "")
                st.session_state.confirmed_comment = None
                st.rerun()
            except Exception as e:
                config.log_error(
                    "generate_comment", e,
                    f"videoId={video_id}",
                )
                st.error("댓글 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

    # -- Display AI results --
    if st.session_state.ai_result:
        ai = st.session_state.ai_result

        st.markdown("#### 🔍 영상 속 고민")
        st.info(_plain_md(ai.get("concern", "")))

        if ai.get("warning"):
            st.warning(_plain_md(ai["warning"]))

        st.markdown("#### 💬 댓글 초안")
        edited = st.text_area(
            "댓글을 수정할 수 있습니다",
            value=st.session_state.edited_comment,
            height=120,
            key="comment_edit_area",
            label_visibility="collapsed",
        )
        st.session_state.edited_comment = edited

        char_count = len(edited)
        is_valid = config.COMMENT_MIN_CHARS <= char_count <= config.COMMENT_MAX_CHARS
        if is_valid:
            st.markdown(
                f"<span style='color: #28a745; font-size: 0.85rem;'>"
                f"✅ {char_count}자 ({config.COMMENT_MIN_CHARS}~{config.COMMENT_MAX_CHARS}자 이내)"
                f"</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<span style='color: #dc3545; font-size: 0.85rem;'>"
                f"⚠️ {char_count}자 (기준: {config.COMMENT_MIN_CHARS}~{config.COMMENT_MAX_CHARS}자)"
                f"</span>",
                unsafe_allow_html=True,
            )

        with st.expander("🧠 AI 분석 근거", expanded=False):
            st.markdown(f"**분석 이유:** {_plain_md(ai.get('reasoning', ''))}")
            pop_comments = ai.get("_popular_comments", [])
            if pop_comments:
                st.markdown("**참고한 인기 댓글:**")
                for pc in pop_comments[:5]:
                    likes = pc.get("likeCount", 0)
                    st.markdown(f"- 👍 {likes:,} | {_plain_md(pc.get('text', '')[:80])}")

    # -- Confirm logic --
    if confirm_clicked and st.session_state.ai_result:
        current_text = st.session_state.edited_comment
        char_count = len(current_text)
        if char_count < config.COMMENT_MIN_CHARS or char_count > config.COMMENT_MAX_CHARS:
            st.error(
                f"댓글은 {config.COMMENT_MIN_CHARS}~{config.COMMENT_MAX_CHARS}자여야 합니다. "
                f"현재 {char_count}자입니다."
            )
        else:
            st.session_state.confirmed_comment = current_text
            st.toast("댓글이 확정되었습니다!")
            go_to_step(3)


# ===========================================================================
# Step 3: 댓글 게시
# ===========================================================================
elif current == 3:
    # Guard: need confirmed comment and selected video
    if not st.session_state.confirmed_comment or not st.session_state.selected_video:
        st.warning("확정된 댓글이 없습니다. 이전 단계를 완료해주세요.")
        go_to_step(2)

    sv = st.session_state.selected_video
    video_id = sv.get("videoId", "")
    video_title = sv.get("title", "제목 없음")

    # Back button
    if st.button("← 댓글 수정하기", key="back_to_step2"):
        go_to_step(2)

    st.subheader("댓글 게시")

    # -- Show confirmed comment --
    st.markdown("#### 확정된 댓글")
    st.info(_plain_md(st.session_state.confirmed_comment))
    st.markdown(
        f'<div class="video-meta">대상 영상: <bdi>{_clean(video_title)}</bdi></div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # -- Profile selector --
    st.markdown("#### 프로필 선택")
    profiles = browser_automation.get_available_profiles()
    if not profiles:
        st.warning("사용 가능한 Chrome 프로필이 없습니다. 설정을 확인해주세요.")
        profile_names = []
        selected_profile_index = None
    else:
        profile_names = [p["name"] for p in profiles]
        selected_name = st.selectbox(
            "Chrome 프로필",
            options=profile_names,
            key="profile_selector",
            label_visibility="collapsed",
        )
        selected_profile_index = profiles[profile_names.index(selected_name)]["index"]

    st.markdown("---")

    # -- Pre-posting checks --
    st.markdown("#### 게시 전 확인")

    can_post, can_post_msg = database.can_post(video_id)
    today_posted = database.today_count()
    daily_limit = config.DAILY_MAX_COMMENTS
    posts_remaining = max(0, daily_limit - today_posted)
    quota_ok = posts_remaining > 0

    if can_post:
        st.markdown("✅ 이 영상에 댓글 가능")
    else:
        st.markdown(f"❌ {can_post_msg}")

    if quota_ok:
        st.markdown(
            f"✅ 오늘 잔여 댓글 {posts_remaining}개 (사용 {today_posted}/{daily_limit})"
        )
    else:
        st.markdown(f"❌ 오늘 댓글 한도 초과 ({today_posted}/{daily_limit})")

    all_checks_pass = can_post and quota_ok and profiles

    st.markdown("---")

    # -- Post button --
    if st.button(
        "🚀 댓글 달기",
        use_container_width=True,
        type="primary",
        disabled=not all_checks_pass,
    ):
        comment_text = st.session_state.confirmed_comment
        with st.status("댓글 게시 중...", expanded=True) as status_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def status_callback(msg: str):
                """Update status display during posting."""
                st.session_state.posting_status = msg
                progress_map = {
                    "프로필 여는 중": 0.1,
                    "영상 페이지 이동 중": 0.3,
                    "댓글 창 찾는 중": 0.5,
                    "입력 중": 0.7,
                    "게시 중": 0.9,
                }
                pval = progress_map.get(msg, 0.5)
                progress_bar.progress(pval)
                status_text.markdown(f"**{msg}**")

            try:
                result = browser_automation.post_comment(
                    video_id=video_id,
                    comment=comment_text,
                    profile_index=selected_profile_index,
                    status_callback=status_callback,
                )
                st.session_state.post_result = result

                if result.get("success"):
                    progress_bar.progress(1.0)
                    status_text.markdown("**게시 완료!**")
                    status_container.update(label="게시 완료!", state="complete")
                    database.log_comment(
                        video_id=video_id,
                        video_title=video_title,
                        profile_index=selected_profile_index,
                        comment=comment_text,
                        success=True,
                    )
                    st.session_state.confirmed_comment = None
                    st.session_state.posting_status = None
                else:
                    error_msg = result.get("error", "알 수 없는 오류")
                    status_container.update(label="게시 실패", state="error")
                    database.log_comment(
                        video_id=video_id,
                        video_title=video_title,
                        profile_index=selected_profile_index,
                        comment=comment_text,
                        success=False,
                        error=error_msg,
                    )
                    st.error(f"게시 실패: {_plain_md(error_msg)}")

            except Exception as e:
                status_container.update(label="게시 실패", state="error")
                config.log_error("post_comment", e, f"videoId={video_id}")
                database.log_comment(
                    video_id=video_id,
                    video_title=video_title,
                    profile_index=selected_profile_index,
                    comment=comment_text,
                    success=False,
                    error=str(e),
                )
                st.error("게시 중 오류가 발생했습니다. 오류 로그를 확인해주세요.")

    # -- Show previous result / success state --
    if st.session_state.post_result and not st.session_state.confirmed_comment:
        if st.session_state.post_result.get("success"):
            st.success("댓글이 성공적으로 게시되었습니다!")
            st.markdown("")
            if st.button(
                "🔄 처음으로 돌아가기 (새 영상 선택)",
                use_container_width=True,
                key="back_to_start",
            ):
                # Reset for a fresh run
                st.session_state.selected_video = None
                st.session_state.ai_result = None
                st.session_state.confirmed_comment = None
                st.session_state.edited_comment = ""
                st.session_state.post_result = None
                st.session_state.posting_status = None
                go_to_step(1)
        else:
            st.error(
                f"마지막 게시: 실패 - {_plain_md(st.session_state.post_result.get('error', ''))}"
            )


# ===========================================================================
# Posting history & error log (dialog modals with date navigation)
# ===========================================================================

def _shift_date(date_key: str, days: int):
    st.session_state[date_key] += timedelta(days=days)


def _date_navigator(prefix: str) -> date:
    """◀ date ▶ row. Callbacks keep the dialog open; st.rerun() here would close it."""
    date_key = f"{prefix}_date"
    today = date.today()
    nav_prev, nav_date, nav_next = st.columns([1, 4, 1])
    with nav_prev:
        st.button(
            "◀", key=f"{prefix}_prev", use_container_width=True, help="이전 날짜",
            on_click=_shift_date, args=(date_key, -1),
        )
    with nav_date:
        selected = st.date_input(
            "날짜", key=date_key, max_value=today, label_visibility="collapsed"
        )
    with nav_next:
        st.button(
            "▶", key=f"{prefix}_next", use_container_width=True, help="다음 날짜",
            disabled=selected >= today,
            on_click=_shift_date, args=(date_key, 1),
        )
    return selected


def _record_html(record: dict, profiles: list[dict]) -> str:
    index = record.get("profile_index", 0)
    profile_name = (
        profiles[index].get("name", "") if 0 <= index < len(profiles) else ""
    ).strip() or f"프로필 {index + 1}"
    mark = "✅" if record.get("success") else "❌"
    title = _clean(record.get("video_title")) or "제목 없음"
    comment = _clean(record.get("comment"))
    error = _clean(record.get("error"))
    comment_html = f'<div class="record-comment" title="{comment}"><bdi>{comment}</bdi></div>' if comment else ""
    error_html = f'<div class="record-error">오류: {error}</div>' if error else ""
    return (
        f'<div class="record"><div class="record-title"><span>{mark}</span><bdi>{title}</bdi></div>'
        f'<div class="record-meta"><bdi>{_clean(profile_name)}</bdi> &middot; '
        f'{_clean(record.get("created_at"))}</div>{comment_html}{error_html}</div>'
    )


def _dialog_rows(rows_html: list[str], unit: str, empty_message: str):
    if not rows_html:
        st.markdown(f'<div class="profile-empty-state">{empty_message}</div>', unsafe_allow_html=True)
        return
    st.markdown(f'<div class="dialog-count">{len(rows_html):,}{unit}</div>', unsafe_allow_html=True)
    # Only the rows scroll, so the date row stays reachable.
    with st.container(height=min(440, 90 + 110 * len(rows_html)), border=False):
        st.markdown("".join(rows_html), unsafe_allow_html=True)


@st.dialog("📋 게시 기록", width="large")
def show_history_dialog():
    selected = _date_navigator("hist")
    profiles = config.load_profiles()
    rows = [_record_html(r, profiles) for r in database.get_history_by_date(selected)]
    _dialog_rows(rows, "건", "해당 날짜에 게시 기록이 없습니다.")


@st.dialog("🔧 오류 로그", width="large")
def show_error_log_dialog():
    selected = _date_navigator("log")
    lines = reversed(config.read_error_log_by_date(selected))
    rows = [f'<div class="log-line"><bdi>{html.escape(line)}</bdi></div>' for line in lines]
    _dialog_rows(rows, "건", "해당 날짜에 기록된 오류가 없습니다.")


st.markdown("---")
_hist_col, _log_col = st.columns(2)
with _hist_col:
    if st.button("📋 게시 기록", use_container_width=True, key="open_hist"):
        st.session_state.hist_date = date.today()
        show_history_dialog()
with _log_col:
    if st.button("🔧 오류 로그", use_container_width=True, key="open_log"):
        st.session_state.log_date = date.today()
        show_error_log_dialog()
