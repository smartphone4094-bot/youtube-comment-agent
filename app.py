"""YouTube Comment Agent Dashboard - Main Streamlit application (step-based wizard)."""

import html
import json
import math
import os
import re
import statistics
import sys
import time
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
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css");

    /* Palette: soft lavender (sazasaju.com colors), tuned for text contrast.
       The toolbar is hidden, so Streamlit's theme always follows the system scheme. */
    :root {
        --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
        --bg: #FDFBF7;
        --bg-glow: #EFE9FF;
        --card: #FFFFFF;
        --surface: #F5F2FF;
        --surface-strong: #ECE7FF;
        --text: #2D2B3D;
        --text-secondary: #6B6978;
        --hairline: #E8E6EF;
        --fill: #F5F2FF;
        --border-strong: #DCD6FF;
        /* One accent, reserved for the main action on each screen */
        --accent: #7B6FDF;
        --accent-hover: #6B5FCF;
        --accent-text: #6B5FCF;
        --accent-ring: rgba(155, 143, 255, 0.38);
        --accent-shadow: rgba(123, 111, 223, 0.5);
        --card-shadow: 0 6px 20px -8px rgba(60, 40, 120, 0.18);
        --soft-shadow: 0 4px 20px rgba(155, 143, 255, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04);
        --font-system: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont,
            "Apple SD Gothic Neo", "Segoe UI", "Malgun Gothic", "Noto Sans KR", system-ui, sans-serif;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --bg: #1A1625;
            --bg-glow: #2D2550;
            --card: #241F35;
            --surface: #2A2438;
            --surface-strong: #352D4D;
            --text: #F5F0FF;
            --text-secondary: #A7A3B5;
            --hairline: #3D3555;
            --fill: #2A2438;
            --border-strong: #4D4470;
            --accent-text: #B8AFFF;
            --accent-shadow: rgba(0, 0, 0, 0.5);
            --card-shadow: 0 6px 20px -8px rgba(0, 0, 0, 0.5);
        }
    }

    /* ── Surfaces ── */
    .stApp {
        background: linear-gradient(180deg, var(--bg-glow) 0, var(--bg) 440px) var(--bg) !important;
        color: var(--text);
    }
    .stApp [data-testid="stMarkdownContainer"],
    .stApp h1, .stApp h2, .stApp h3,
    [data-testid="stWidgetLabel"] {
        color: var(--text);
    }
    /* Button labels are markdown too; they take the button's own color (white on primary) */
    .stApp button [data-testid="stMarkdownContainer"],
    .stApp button [data-testid="stMarkdownContainer"] p {
        color: inherit !important;
    }
    /* ── Header: ink wordmark, only the brand name in purple; account button on the same row ── */
    .app-header {
        display: flex;
        align-items: center;
        min-height: 44px;
    }
    .stApp h1.app-title {
        margin: 0 !important;
        padding: 0 !important;
        font-size: clamp(1.5rem, 4.2vw, 1.9rem) !important;
        font-weight: 800 !important;
        letter-spacing: -0.035em;
        color: var(--text) !important;
    }
    .app-title .brand-name {
        color: var(--accent);
    }
    .app-title a {
        display: none !important;
    }
    @media (prefers-color-scheme: dark) {
        .app-title .brand-name { color: #B8AFFF; }
    }
    [data-testid="stHorizontalBlock"]:has(.app-header) {
        flex-wrap: nowrap !important;
        align-items: center;
    }
    [data-testid="stHorizontalBlock"]:has(.app-header) > [data-testid="stColumn"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0 !important;
    }
    [data-testid="stHorizontalBlock"]:has(.app-header) > [data-testid="stColumn"]:last-child {
        flex: 0 0 6.5rem !important;
    }
    [data-testid="stHorizontalBlock"]:has(.app-header) > [data-testid="stColumn"]:nth-child(2) {
        flex: 0 0 6.5rem !important;
    }
    /* The settings button is the account button's twin: same pill, size, ink and shadow
       (selector outranks the generic secondary-button rule, which made it purple and taller) */
    .st-key-open_settings .stButton button[kind="secondary"] {
        min-height: 40px;
        height: 40px;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        background: var(--card) !important;
        border: 1px solid var(--border-strong) !important;
        color: var(--text) !important;
        box-shadow: 0 3px 12px rgba(138, 124, 240, 0.12);
        white-space: nowrap;
    }
    .st-key-open_settings .stButton button p {
        font-size: 1rem !important;
        font-weight: 600 !important;
    }
    @media (max-width: 480px) {
        /* Icon only on phones, so the title keeps its room */
        [data-testid="stHorizontalBlock"]:has(.app-header) > [data-testid="stColumn"]:nth-child(2) {
            flex: 0 0 2.9rem !important;
        }
        .st-key-open_settings button p { display: none; }
        .st-key-open_settings button { padding-inline: 0 !important; }
    }
    /* ── Settings popup: same flat look as before; only the rhythm is set ──
       field-to-field 16px, a 28px break before each new section title, 6px under it */
    [role="dialog"] [data-testid="stVerticalBlock"] {
        gap: 16px;
    }
    .settings-section {
        margin: 12px 0 -10px;
        font-size: 0.8rem;
        font-weight: 800;
        letter-spacing: 0.02em;
        color: var(--accent-text);
    }
    [role="dialog"] [data-testid="stElementContainer"]:first-child .settings-section,
    [role="dialog"] [data-testid="stAlert"] + * .settings-section {
        margin-top: 0;
    }
    /* Number fields: the global input style rounded only the text part and left the −/+
       on a grey slab; make the whole thing one control like the other fields */
    [data-testid="stNumberInputContainer"] {
        border: 1px solid var(--border-strong);
        border-radius: 12px;
        background: var(--card);
        overflow: hidden;
        transition: border-color 150ms ease, box-shadow 150ms ease;
    }
    [data-testid="stNumberInputContainer"]:focus-within {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px var(--accent-ring);
    }
    [data-testid="stNumberInputContainer"] [data-baseweb="input"] {
        border: none !important;
        border-radius: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
    }
    [data-testid="stNumberInputContainer"] button {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        color: var(--text-secondary) !important;
    }
    @media (hover: hover) and (pointer: fine) {
        [data-testid="stNumberInputContainer"] button:hover:not(:disabled) {
            background: var(--surface) !important;
            color: var(--accent-text) !important;
        }
    }

    /* ── Search box: pill with a label, a divider, and a search icon ──
       All three sit in the box's own flex row, centered together, instead of being
       pinned with top:50% + translate, which rounds to a different pixel than the text
       under display scaling. */
    .st-key-keyword_input [data-baseweb="input"] {
        min-height: 52px;
        align-items: center;
        border-radius: 9999px !important;
        padding-inline: 1.25rem 1.1rem;
        box-shadow: 0 3px 12px rgba(138, 124, 240, 0.1);
    }
    .st-key-keyword_input [data-baseweb="input"]::before {
        content: "키워드";
        flex: none;
        padding-right: 0.85rem;
        font-size: 0.92rem;
        font-weight: 700;
        line-height: 22px;
        letter-spacing: -0.01em;
        color: var(--accent-text);
        pointer-events: none;
    }
    .st-key-keyword_input [data-baseweb="input"]::after {
        content: "";
        flex: none;
        width: 20px;
        height: 20px;
        margin-left: 0.6rem;
        background: var(--accent-text);
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E") center / contain no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E") center / contain no-repeat;
        pointer-events: none;
    }
    /* The divider between the mark and the text */
    .st-key-keyword_input [data-baseweb="input"] > div:first-child {
        align-self: center;
        height: 22px;
        border-left: 1.5px solid var(--border-strong) !important;
        border-radius: 0 !important;
    }
    .st-key-keyword_input input {
        height: 22px;
        padding-block: 0 !important;
        padding-left: 0.85rem !important;
        font-size: 1rem !important;
        font-weight: 500;
        line-height: 22px !important;
    }
    .st-key-keyword_input input::placeholder {
        color: var(--text-secondary);
        opacity: 1;
    }

    [data-testid="stDecoration"] {
        background-image: linear-gradient(90deg, #9B8FFF, #FFB8D0) !important;
    }
    /* Only the bordered row container itself: its own block directly holds the thumbnail/info columns */
    [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] .video-title:not(.full)) {
        background: var(--card);
        border: 1px solid var(--hairline) !important;
        border-radius: 16px !important;
        box-shadow: var(--card-shadow);
        padding: 20px !important;
        transition: border-color 150ms ease, box-shadow 200ms var(--ease-out);
    }
    @media (hover: hover) and (pointer: fine) {
        [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] .video-title:not(.full)):hover {
            border-color: var(--border-strong) !important;
            box-shadow: 0 10px 28px -10px rgba(60, 40, 120, 0.26);
        }
    }
    /* Alerts take the palette: info is lavender, the rest stay semantic but soft */
    [data-testid="stAlertContainer"] {
        border-radius: 14px !important;
    }
    [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {
        background: var(--surface) !important;
        border: 1px solid var(--border-strong);
    }
    [data-testid="stAlertContentInfo"],
    [data-testid="stAlertContentInfo"] [data-testid="stMarkdownContainer"] {
        color: var(--text) !important;
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
        padding-top: 2.25rem !important;
        padding-bottom: 6rem !important;
    }
    /* Breathing room between stacked elements */
    [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {
        gap: 1.25rem;
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
    /* Streamlit's -1rem cancels a closing paragraph's margin. Our HTML blocks (cards, tags)
       have no closing paragraph, so the -1rem pulled the next card up to 2px away. */
    .stApp [data-testid="stMarkdownContainer"]:not(:has(> p:last-child, > ul:last-child, > ol:last-child)) {
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
        border-radius: 12px !important;
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
        font-weight: 700 !important;
    }
    /* Primary: solid accent with a soft lift */
    .stButton button[kind="primary"] {
        background: var(--accent) !important;
        border: 1px solid var(--accent) !important;
        color: #fff !important;
        box-shadow: 0 8px 20px -8px var(--accent-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.18);
    }
    @media (hover: hover) and (pointer: fine) {
        .stButton button[kind="primary"]:hover:not(:disabled) {
            background: var(--accent-hover) !important;
            border-color: var(--accent-hover) !important;
            box-shadow: 0 10px 24px -8px var(--accent-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.18);
        }
    }
    /* Secondary: lavender outline on a card surface, fills on hover */
    .stButton button[kind="secondary"] {
        background: var(--card) !important;
        border: 1px solid var(--border-strong) !important;
        color: var(--accent-text) !important;
    }
    @media (hover: hover) and (pointer: fine) {
        .stButton button[kind="secondary"]:hover:not(:disabled) {
            background: var(--surface) !important;
            border-color: var(--accent) !important;
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
        border-radius: 12px !important;
        background: var(--card) !important;
        border: 1px solid var(--border-strong) !important;
        transition: border-color 150ms ease, box-shadow 150ms ease;
    }
    [data-baseweb="input"] > div,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] > div,
    [data-baseweb="textarea"] textarea {
        background: transparent !important;
        color: var(--text) !important;
    }
    [data-baseweb="input"]:focus-within,
    [data-baseweb="textarea"]:focus-within,
    [data-baseweb="select"] > div:focus-within {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-ring);
    }
    .stExpander details {
        background: var(--card);
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
    /* A clickable thumbnail: an invisible button laid over it opens the video popup;
       hover dims the image and shows a play badge */
    [data-testid="stVerticalBlock"]:has(> [class*="st-key-play_"]) {
        position: relative;
    }
    [class*="st-key-play_"] {
        position: absolute !important;
        inset: 0;
        z-index: 2;
    }
    [class*="st-key-play_"].stElementContainer .stButton {
        position: absolute !important;
        inset: 0 !important;
    }
    [class*="st-key-play_"].stElementContainer .stButton,
    [class*="st-key-play_"].stElementContainer .stButton div,
    [class*="st-key-play_"].stElementContainer .stButton button[kind] {
        width: 100% !important;
        height: 100% !important;
    }
    [class*="st-key-play_"].stElementContainer .stButton button[kind] {
        min-height: 0 !important;
        padding: 0 !important;
        border: none !important;
        border-radius: 12px !important;
        background: transparent !important;
        box-shadow: none !important;
        color: transparent !important;
        cursor: pointer;
    }
    [class*="st-key-play_"].stElementContainer .stButton button[kind] p { opacity: 0; }
    [data-testid="stVerticalBlock"]:has(> [class*="st-key-play_"]) .bg-image {
        transition: transform 200ms var(--ease-out);
    }
    [data-testid="stVerticalBlock"]:has(> [class*="st-key-play_"]) .thumb::after {
        content: "";
        position: absolute;
        inset: 0;
        background:
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Ccircle cx='24' cy='24' r='22' fill='white' fill-opacity='0.92'/%3E%3Cpath d='M20 16.5v15l12-7.5z' fill='%237B6FDF'/%3E%3C/svg%3E")
            center / 44px no-repeat,
            rgba(26, 22, 37, 0.28);
        opacity: 0;
        transition: opacity 160ms ease;
    }
    @media (hover: hover) and (pointer: fine) {
        [data-testid="stVerticalBlock"]:has(> [class*="st-key-play_"]:hover) .thumb::after { opacity: 1; }
        [data-testid="stVerticalBlock"]:has(> [class*="st-key-play_"]:hover) .bg-image { transform: scale(1.03); }
    }
    [data-testid="stVerticalBlock"]:has(> [class*="st-key-play_"] button:focus-visible) .thumb {
        box-shadow: 0 0 0 3px var(--accent-ring);
    }
    @media (prefers-reduced-motion: reduce) {
        [data-testid="stVerticalBlock"]:has(> [class*="st-key-play_"]) .bg-image,
        [data-testid="stVerticalBlock"]:has(> [class*="st-key-play_"]) .thumb::after { transition: none; }
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

    /* ── Step 2 loading popup ── */
    .loading-overlay {
        position: fixed;
        inset: 0;
        z-index: 999990;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px;
        background: rgba(26, 22, 37, 0.28);
        -webkit-backdrop-filter: blur(6px) saturate(140%);
        backdrop-filter: blur(6px) saturate(140%);
        animation: surface-fade 160ms ease;
    }
    .loading-modal {
        width: min(340px, 100%);
        padding: 28px 28px 24px;
        border-radius: 20px;
        background: var(--card);
        border: 1px solid var(--hairline);
        box-shadow: 0 24px 70px rgba(60, 40, 120, 0.22), 0 6px 18px rgba(0, 0, 0, 0.08);
        text-align: center;
        animation: surface-in 220ms var(--ease-out);
    }
    .loading-spinner {
        width: 40px;
        height: 40px;
        margin: 0 auto 16px;
        border-radius: 50%;
        border: 3px solid var(--surface-strong);
        border-top-color: var(--accent);
        animation: loading-spin 800ms linear infinite;
    }
    .loading-title {
        font-size: 1.02rem;
        font-weight: 700;
        letter-spacing: -0.015em;
        color: var(--text);
        word-break: keep-all;
    }
    .loading-steps {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        margin-top: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        color: var(--text-secondary);
        font-variant-numeric: tabular-nums;
    }
    .loading-steps span:last-child {
        margin-left: 4px;
    }
    .loading-dot {
        width: 18px;
        height: 4px;
        border-radius: 999px;
        background: var(--surface-strong);
        transition: background-color 200ms ease;
    }
    .loading-dot.on {
        background: var(--accent);
    }
    .loading-hint {
        margin: 10px 0 0 !important;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }
    .loading-hint strong {
        margin-right: 6px;
        font-weight: 700;
        color: var(--text);
    }
    /* Live elapsed counter (CSS only: the overlay is markdown, no JS). Browsers without
       @property leave --eta-on unset, so the var() fallback 0 collapses the span and
       only the static estimate shows. */
    @property --eta-sec { syntax: '<integer>'; inherits: false; initial-value: 0; }
    @property --eta-on { syntax: '<integer>'; inherits: false; initial-value: 1; }
    .loading-eta-count {
        display: inline-block;
        overflow: hidden;
        white-space: nowrap;
        vertical-align: bottom;
        max-width: calc(var(--eta-on, 0) * 12em);
        counter-reset: eta var(--eta-sec);
        animation: eta-tick 120s steps(120, end) forwards;
    }
    .loading-eta-count::after {
        content: "· " counter(eta) "초 경과";
        padding-right: 6px;
    }
    @keyframes eta-tick {
        from { --eta-sec: 0; }
        to { --eta-sec: 120; }
    }
    @keyframes loading-spin {
        to { transform: rotate(360deg); }
    }
    /* The previous screen's leftovers stay hidden while the popup is up */
    .stApp:has(.loading-overlay) [data-stale="true"],
    .stApp:has(.loading-overlay) [data-testid="stVerticalBlockBorderWrapper"]:has([data-stale="true"]):not(:has([data-stale="false"])),
    .stApp:has(.loading-overlay) [data-testid="stHorizontalBlock"]:has([data-stale="true"]):not(:has([data-stale="false"])) {
        visibility: hidden;
    }
    @media (prefers-reduced-motion: reduce) {
        .loading-spinner { animation-duration: 2400ms; }
        .loading-overlay, .loading-modal { animation: none; }
        .loading-eta-count { display: none; }
    }

    /* ── Step 2 cards (section / featured), after sazasaju.com/fortune ── */
    .section-card,
    [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .comment-card-head) {
        background: var(--card);
        border: 1px solid var(--hairline) !important;
        border-radius: 20px !important;
        padding: 24px !important;
        box-shadow: var(--soft-shadow);
    }
    /* Inside the comment card: a tighter rhythm than between cards */
    [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .comment-card-head) [data-testid="stVerticalBlock"] {
        gap: 14px;
    }
    .section-head h4 {
        margin: 0 !important;
        padding: 0 !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        line-height: 1.4 !important;
        color: var(--text);
    }
    .section-head p {
        margin: 2px 0 0 !important;
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--text-secondary);
    }
    .section-card .section-head {
        margin-bottom: 12px;
    }
    /* Video content: a plain white card, title then up to 7 lines that scroll */
    .content-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
    }
    .content-head h4 {
        margin: 0 !important;
        padding: 0 !important;
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
        line-height: 1.4 !important;
        color: var(--text);
    }
    .content-tag {
        padding: 2px 8px;
        border-radius: 999px;
        background: var(--surface-strong);
        color: var(--accent-text);
        font-size: 0.72rem;
        font-weight: 700;
        white-space: nowrap;
    }
    .content-text {
        --line: 1.85em;
        max-height: calc(var(--line) * 7);
        overflow-y: auto;
        padding-right: 6px;
        font-size: 0.95rem;
        line-height: var(--line);
        color: var(--text-secondary);
        white-space: pre-wrap;
        overscroll-behavior: contain;
        scrollbar-width: thin;
        scrollbar-color: var(--border-strong) transparent;
    }
    .content-text::-webkit-scrollbar { width: 6px; }
    .content-text::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 999px; }
    .content-text:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px var(--accent-ring);
        border-radius: 8px;
    }
    .section-empty {
        font-size: 0.9rem;
        color: var(--text-secondary);
    }
    /* The concern: a solid purple card, small light label over the quoted line, centered */
    .feature-card {
        padding: 22px 24px 24px;
        border-radius: 20px;
        background: var(--accent);
        box-shadow: 0 10px 24px -12px var(--accent-shadow);
        text-align: center;
    }
    .feature-label {
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.01em;
        color: rgba(255, 255, 255, 0.78);
        margin-bottom: 8px;
    }
    .feature-text {
        font-size: 1.25rem;
        font-weight: 800;
        line-height: 1.5;
        letter-spacing: -0.02em;
        color: #fff;
        word-break: keep-all;
        overflow-wrap: anywhere;
        text-wrap: balance;
    }
    .count-row {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.82rem;
        color: var(--text-secondary);
        font-variant-numeric: tabular-nums;
    }
    .count-chip {
        display: inline-flex;
        align-items: center;
        padding: 3px 10px;
        border-radius: 9999px;
        font-weight: 700;
    }
    .count-chip.ok { background: var(--surface-strong); color: var(--accent-text); }
    .count-chip.bad { background: rgba(232, 72, 76, 0.14); color: #C0282D; }
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
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
    }
    /* White tag like the account button beside it; only the count carries color.
       Running low / used up turn the count and the tail orange / red. */
    .status-badge {
        background: var(--card);
        border: 1px solid var(--hairline);
        box-shadow: var(--soft-shadow);
        color: var(--text-secondary);
    }
    .status-ok b { color: var(--accent-text); }
    .status-warn b, .status-warn .status-tail { color: #9A5B00; }
    .status-full b, .status-full .status-tail { color: #C0282D; }
    @media (prefers-color-scheme: dark) {
        .status-warn b, .status-warn .status-tail { color: #FFC56B; }
        .status-full b, .status-full .status-tail { color: #FF8A8D; }
    }
    .status-badge b {
        font-weight: 800;
        margin-left: 0.25em;
    }
    .status-dot {
        margin: 0 0.4em;
        opacity: 0.55;
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
    /* A soft lavender tint for "you are here"; the solid accent stays on the action buttons */
    .step-item.active {
        background: var(--surface-strong);
        color: var(--accent-text);
        font-weight: 700;
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
        background: var(--accent);
        color: #fff;
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
        background: var(--card) !important;
        border: 1px solid var(--border-strong) !important;
        color: var(--text) !important;
        box-shadow: 0 3px 12px rgba(138, 124, 240, 0.12);
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
    .profile-count {
        margin-left: 4px;
        font-size: 0.78rem;
        font-weight: 700;
        color: var(--accent-text);
        font-variant-numeric: tabular-nums;
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
    "analysis": None,              # {"video_id", "transcript", "popular_comments"} for step 2
    "analysis_error": False,       # generation failed; wait for a retry instead of looping
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
    st.session_state.scroll_to_top = "jump"  # a new step starts at its top, not where the last one was scrolled
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


def _valid_video_id(video_id: str) -> bool:
    return bool(video_id) and re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id) is not None


@st.dialog("영상 보기", width="large")
def show_video_dialog(video_id: str, title: str):
    """Plays the video inside the app; a new-tab link is unreliable (the desktop app's
    browser pane, for one, doesn't open page links in new tabs)."""
    st.video(f"https://www.youtube.com/watch?v={video_id}", autoplay=True)
    if title:
        st.markdown(f'<div class="video-title full"><bdi>{title}</bdi></div>', unsafe_allow_html=True)
    st.link_button(
        "YouTube에서 열기",
        f"https://www.youtube.com/watch?v={video_id}",
        icon=":material/open_in_new:",
        use_container_width=True,
    )


def _thumbnail(url, video_id: str, title: str, key: str):
    """The thumbnail; with a valid video id it is clickable and plays the video in a popup."""
    st.markdown(_thumb_html(url), unsafe_allow_html=True)
    if _valid_video_id(video_id):
        if st.button("영상 보기", key=f"play_{key}", help="영상 보기"):
            show_video_dialog(video_id, title)


def _video_meta(*parts) -> str:
    return " &middot; ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Google login
# ---------------------------------------------------------------------------


def _google_login_button(location: str):
    if browser_automation.google_login_status():
        st.button("로그인 진행 중…", key=f"google_login_{location}", use_container_width=True, disabled=True)
        return
    if len(st.session_state.profiles_list) >= config.max_accounts():
        st.button(
            f"계정은 최대 {config.max_accounts()}개까지 연결할 수 있어요",
            key=f"google_login_{location}", use_container_width=True, disabled=True,
        )
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


def _save_google_account(account: dict) -> bool:
    """Add or refresh an account. False when it is new and the limit is already reached."""
    profiles = st.session_state.profiles_list
    for i, profile in enumerate(profiles):
        if account["email"] and profile.get("email", "").lower() == account["email"].lower():
            config.remove_managed_profile(profile.get("path", ""))
            profiles[i] = account
            break
    else:
        if len(profiles) >= config.max_accounts():
            config.remove_managed_profile(account.get("path", ""))
            return False
        profiles.append(account)
    config.save_profiles(profiles)
    return True


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
    label = _plain_md(account["name"] or account["email"])
    if not _save_google_account(account):
        st.session_state.login_notice = (
            "warning", f"계정은 최대 {config.max_accounts()}개까지 연결할 수 있어 {label} 계정은 연결하지 않았습니다."
        )
        return
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


@st.dialog("설정")
def show_api_settings_dialog(reason: str | None = None):
    """Comment rules, daily limit, and the YouTube/AI keys — all saved to settings.yaml (git-ignored)."""
    if reason:
        st.info(reason)

    st.markdown('<div class="settings-section">댓글 규칙</div>', unsafe_allow_html=True)
    brand = st.text_input(
        "브랜드 이름", value=config.brand_name(), key="set_brand",
        help="댓글에서 호기심을 유도할 곳의 이름",
    )
    min_col, max_col, daily_col = st.columns(3)
    with min_col:
        min_chars = st.number_input("최소 글자 수", min_value=1, max_value=500,
                                    value=config.comment_min_chars() or 40, step=5, key="set_min_chars")
    with max_col:
        max_chars = st.number_input("최대 글자 수", min_value=1, max_value=500,
                                    value=config.comment_max_chars() or 120, step=5, key="set_max_chars")
    with daily_col:
        daily_max = st.number_input("하루 댓글 상한", min_value=1, max_value=100,
                                    value=config.daily_max_comments() or 10, step=1, key="set_daily_max")

    st.markdown('<div class="settings-section">YouTube</div>', unsafe_allow_html=True)
    youtube_key = st.text_input(
        "YouTube Data API 키",
        value=config.youtube_api_key(),
        type="password",
        key="set_youtube_key",
        help="Google Cloud Console에서 YouTube Data API v3를 켠 뒤 만든 API 키",
    )
    st.caption("[Google Cloud Console에서 키 만들기](https://console.cloud.google.com/apis/credentials)")

    st.markdown('<div class="settings-section">댓글을 쓸 AI</div>', unsafe_allow_html=True)
    providers = list(config.AI_PROVIDERS)
    current = config.ai_provider()
    provider = st.selectbox(
        "AI 서비스",
        providers,
        index=providers.index(current),
        format_func=lambda p: config.AI_PROVIDERS[p]["label"],
        key="set_ai_provider",
    )
    info = config.AI_PROVIDERS[provider]
    ai_key = st.text_input(
        f"{info['label']} API 키",
        value=config.ai_key(provider),
        type="password",
        key=f"set_ai_key_{provider}",
    )
    model = st.text_input(
        "모델",
        value=config.ai_model(provider),
        key=f"set_ai_model_{provider}",
        placeholder="비워두면 자동 선택",
        help="비워두면 이 서비스의 현재 모델 목록에서 자동으로 고릅니다. 특정 모델을 쓰려면 모델 ID를 입력하세요.",
    )
    base_url = ""
    if info.get("base_url_editable"):
        base_url = st.text_input(
            "서버 주소",
            value=config.ai_base_url(provider),
            key=f"set_ai_base_url_{provider}",
            help="OpenAI 호환 API의 /v1 주소",
        )
    if info.get("note"):
        st.caption(info["note"])
    st.caption(f"[{info['label']} 키 발급 페이지]({info['key_url']})")

    if st.button("저장", type="primary", use_container_width=True, icon=":material/check:", key="save_settings"):
        if not brand.strip():
            st.error("브랜드 이름을 입력해주세요.")
            return
        if min_chars > max_chars:
            st.error("최소 글자 수가 최대 글자 수보다 클 수 없습니다.")
            return
        settings = config.load_settings()
        settings["comment"] = {**(settings.get("comment") or {}),
                               "min_chars": int(min_chars), "max_chars": int(max_chars), "brand": brand.strip()}
        settings["limits"] = {**(settings.get("limits") or {}), "daily_max_comments": int(daily_max)}
        api = settings.setdefault("api", {})
        api["youtube_api_key"] = youtube_key.strip()
        api["ai_provider"] = provider
        api.setdefault("ai_keys", {})[provider] = ai_key.strip()
        api.setdefault("ai_models", {})[provider] = model.strip()
        if info.get("base_url_editable"):
            api.setdefault("ai_base_urls", {})[provider] = base_url.strip()
        config.save_settings(settings)
        st.session_state.login_notice = ("toast", "설정을 저장했습니다.")
        st.rerun()


def _require_youtube_key() -> bool:
    if config.youtube_api_key():
        return True
    show_api_settings_dialog("YouTube API 키를 등록해야 영상을 불러올 수 있어요.")
    return False


def _require_ai_key() -> bool:
    if config.ai_ready():
        return True
    show_api_settings_dialog("AI API 키를 등록해야 영상 속 고민을 분석하고 댓글을 만들 수 있어요.")
    return False


@st.dialog("로그인이 필요합니다")
def show_login_required_dialog():
    st.markdown("댓글을 게시하려면 Google 계정을 먼저 연결해야 합니다.")
    _google_login_button("dialog")


# ---------------------------------------------------------------------------
# Initialize Chrome profiles & Header with profile popover
# ---------------------------------------------------------------------------
if "profiles_list" not in st.session_state:
    st.session_state.profiles_list = config.load_profiles()

# Title row: the account button sits at the title's right end
_profiles_list = st.session_state.profiles_list
_profile_count = len(_profiles_list)

_title_col, _settings_col, _profile_col = st.columns([6, 1, 1])
with _settings_col:
    if st.button("설정", key="open_settings", icon=":material/settings:", use_container_width=True,
                 help="YouTube·AI API 키와 사용할 AI를 설정합니다"):
        show_api_settings_dialog()
with _title_col:
    st.markdown(
        '<div class="app-header">'
        '<h1 class="app-title"><span class="brand-name">운명원</span> 마케팅 AI에이전트</h1>'
        '</div>',
        unsafe_allow_html=True,
    )
with _profile_col:
    profiles_list = _profiles_list
    with st.popover(f"👤 {_profile_count}", use_container_width=True):
        st.markdown(
            f'<div class="profile-popover-header">Google 계정 관리 '
            f'<span class="profile-count">{_profile_count} / {config.max_accounts()}</span></div>'
            '<div class="profile-popover-hint">'
            f'댓글 게시에 사용할 Google 계정을 최대 {config.max_accounts()}개까지 연결하세요.<br>'
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

# Today's comment count / daily limit
posted_today = database.today_count()
daily_max = config.daily_max_comments()
remaining = max(0, daily_max - posted_today)

if remaining == 0:
    badge_class, badge_tail = "status-full", "한도 도달"
elif remaining <= 3:
    badge_class, badge_tail = "status-warn", f"{remaining}개 남음"
else:
    badge_class, badge_tail = "status-ok", f"{remaining}개 남음"
st.markdown(
    f'<span class="status-badge {badge_class}">오늘 <b>{posted_today}</b>/{daily_max}'
    f'<span class="status-dot">·</span><span class="status-tail">{badge_tail}</span></span>',
    unsafe_allow_html=True,
)


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


def _render_scroll_anchor():
    """Scroll to the top when a page turn asked for it.

    Always rendered as the page's last element: inserting it only on some runs shifts the
    elements after it, and Streamlit briefly shows the stale copies (a doubled pagination row).
    Unchanged content keeps the iframe as is; a new nonce reloads it and runs the scroll.
    """
    request = st.session_state.pop("scroll_to_top", False)
    if request:
        st.session_state.scroll_nonce = st.session_state.get("scroll_nonce", 0) + 1
        # A page turn glides up; a new step jumps, since its page is still being laid out.
        st.session_state.scroll_behavior = "auto" if request == "jump" else "smooth"
    nonce = st.session_state.get("scroll_nonce", 0)
    behavior = st.session_state.get("scroll_behavior", "smooth")
    components.html(
        f"""<script>
        // nonce {nonce}
        if ({nonce} > 0) {{
            const up = () => {{
                const doc = window.parent.document;
                doc.querySelectorAll('[data-testid="stMain"], [data-testid="stAppViewContainer"], section.main')
                    .forEach(el => el.scrollTo({{top: 0, behavior: "{behavior}"}}));
                window.parent.scrollTo({{top: 0, behavior: "{behavior}"}});
            }};
            // Wait for Streamlit to finish placing this run's elements, which would cancel the scroll.
            setTimeout(up, 80);
            if ("{behavior}" === "auto") setTimeout(up, 400);
        }}
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
    _reset_generation()
    go_to_step(2)


_GEN_TIMES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "gen_times.json")


def _load_gen_times() -> list:
    """Recorded step-2 load durations (seconds); best effort, empty on any error."""
    try:
        with open(_GEN_TIMES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return [float(x) for x in data if isinstance(x, (int, float)) and x > 0][-10:]
    except Exception:
        return []


def _record_gen_time(seconds: float):
    """Keep the last 10 successful step-2 load durations in data/gen_times.json."""
    try:
        times = (_load_gen_times() + [round(seconds)])[-10:]
        os.makedirs(os.path.dirname(_GEN_TIMES_PATH), exist_ok=True)
        with open(_GEN_TIMES_PATH, "w", encoding="utf-8") as f:
            json.dump(times, f)
    except Exception:
        pass


def _estimate_seconds(times: list) -> int:
    """Median of past durations clamped to 5..60 s; 20 s with no history."""
    if not times:
        return 20
    return int(min(60, max(5, round(statistics.median(times)))))


def _loading_overlay(
    placeholder, message: str, stage: int, stages: int = 2, estimate: int | None = None, elapsed: float = 0.0
):
    """A centered popup over the page while step 2 loads. While it is up, the previous
    screen's leftover (stale) elements are hidden instead of showing through, faded.
    The elapsed counter ticks in CSS; `elapsed` (seconds since the load began) becomes a
    negative animation-delay so a re-render continues the count instead of restarting it."""
    if estimate is None:
        estimate = _estimate_seconds(_load_gen_times())
    estimate = int(estimate)
    elapsed = max(0.0, float(elapsed))
    eta = f'<span class="loading-eta-count" aria-hidden="true" style="animation-delay: {-elapsed:.2f}s"></span>'
    dots = "".join(
        f'<span class="loading-dot{" on" if i <= stage else ""}"></span>' for i in range(1, stages + 1)
    )
    placeholder.markdown(
        f'<div class="loading-overlay" role="status" aria-live="polite">'
        f'<div class="loading-modal">'
        f'<div class="loading-spinner" aria-hidden="true"></div>'
        f'<div class="loading-title">{html.escape(message)}</div>'
        f'<div class="loading-steps">{dots}<span>{stage} / {stages}</span></div>'
        f'<p class="loading-hint"><strong>예상시간 약 {estimate}초</strong>{eta}<span>(보통 10~30초 걸려요)</span></p>'
        f"</div></div>",
        unsafe_allow_html=True,
    )


def _reset_generation():
    """A new video invalidates anything loaded or generated for the previous one."""
    st.session_state.ai_result = None
    st.session_state.analysis = None
    st.session_state.analysis_error = False
    st.session_state.confirmed_comment = None
    st.session_state.edited_comment = ""
    st.session_state.pop("comment_edit_area", None)


# ===========================================================================
# Step 1: 영상 불러오기
# ===========================================================================
if current == 1:
    st.subheader("영상 불러오기")

    # --- Keyword search ---
    keyword = st.text_input(
        "검색 키워드",
        value=st.session_state.search_keyword,
        placeholder="연애, 결혼, 소개팅 검색",
        key="keyword_input",
        label_visibility="collapsed",
    )

    search_clicked = st.button(
        "🔍 영상 불러오기", use_container_width=True, type="primary"
    )

    if search_clicked:
        if not _require_youtube_key():
            pass
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
            if not _require_youtube_key():
                pass
            elif not url_input.strip():
                st.warning("URL을 입력해주세요.")
            else:
                vid = youtube_api.extract_video_id(url_input.strip())
                if not vid:
                    st.error("유효한 YouTube URL이 아닙니다.")
                elif vid in database.get_posted_video_ids():
                    st.error("이미 댓글을 게시한 영상이라 선택할 수 없습니다.")
                elif not _require_ai_key():
                    pass
                elif not st.session_state.profiles_list:
                    show_login_required_dialog()
                else:
                    with st.spinner("영상 정보를 불러오는 중..."):
                        try:
                            details = youtube_api.get_video_details(vid)
                            if details:
                                st.session_state.selected_video = details
                                _reset_generation()
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

            with st.container(border=True):
                c_img, c_info = st.columns([1, 3])
                with c_img:
                    _thumbnail(thumb, video.get("videoId", ""), title, f"{cur_page}_{idx}")
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
                            if not _require_ai_key():
                                pass
                            elif st.session_state.profiles_list:
                                _select_video(video)
                            else:
                                show_login_required_dialog()

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
        _thumbnail(thumb, video_id, v_title, "selected")
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

    # -- Loading happens in a popup over the new page, once per video; then the page reruns
    #    with everything in place. A failed generation waits for a retry instead of looping. --
    analysis = st.session_state.analysis
    need_content = not analysis or analysis.get("video_id") != video_id
    need_comment = st.session_state.ai_result is None and not st.session_state.analysis_error
    if need_content or need_comment:
        overlay = st.empty()
        # The start time lives in session_state so an interrupted run that restarts the same
        # video's load keeps counting from the original start rather than from zero.
        started = st.session_state.get("_load_started")
        if not started or started[0] != video_id:
            started = (video_id, time.monotonic())
            st.session_state["_load_started"] = started
        load_started = started[1]
        estimate = _estimate_seconds(_load_gen_times())
        if need_content:
            _loading_overlay(
                overlay, "영상 자막을 불러오는 중", 1,
                estimate=estimate, elapsed=time.monotonic() - load_started,
            )
            transcript = None
            try:
                transcript = youtube_api.get_transcript(video_id)
            except Exception as e:
                config.log_error("get_transcript", e, f"videoId={video_id}")
            try:
                popular_comments = youtube_api.get_popular_comments(video_id)
            except Exception as e:
                config.log_error("get_popular_comments", e, f"videoId={video_id}")
                popular_comments = []
            analysis = {
                "video_id": video_id,
                "transcript": transcript,
                "popular_comments": popular_comments,
            }
            st.session_state.analysis = analysis

        _loading_overlay(
            overlay, "영상 속 고민을 분석하고 댓글을 쓰는 중", 2,
            estimate=estimate, elapsed=time.monotonic() - load_started,
        )
        try:
            result = ai_comment.generate_comment(
                title=sv.get("title", ""),
                description=sv.get("description", ""),
                captions=analysis["transcript"],
                popular_comments=analysis["popular_comments"],
            )
        except Exception as e:
            config.log_error("generate_comment", e, f"videoId={video_id}")
            st.session_state.analysis_error_kind = (
                "quota" if isinstance(e, ai_comment.RateLimitError) else "other"
            )
            result = None
        if result and need_content:
            # Only full loads (both stages) are recorded, so retries don't skew the estimate.
            _record_gen_time(time.monotonic() - load_started)
        st.session_state.pop("_load_started", None)
        if result:
            st.session_state.ai_result = result
            st.session_state.edited_comment = result.get("comment", "")
            st.session_state.confirmed_comment = None
            st.session_state.pop("comment_edit_area", None)
        else:
            st.session_state.analysis_error = True
        st.rerun()

    # -- 1. Video content: the captions, or the description when there are none --
    transcript = analysis["transcript"]
    description = (sv.get("description") or "").strip()
    if transcript:
        content_tag, content_text = "", transcript
    elif description:
        # Only the fallback is labeled; captions are the normal case
        content_tag, content_text = '<span class="content-tag">자막 없음 · 영상 설명</span>', description
    else:
        content_tag, content_text = "", ""
    content_body = (
        f'<div class="content-text" tabindex="0"><bdi>{html.escape(content_text[:6000])}</bdi></div>'
        if content_text
        else '<div class="section-empty">표시할 영상 내용이 없어 제목으로 분석했어요.</div>'
    )
    st.markdown(
        f'<section class="section-card content-card">'
        f'<div class="content-head"><h4>영상 내용</h4>{content_tag}</div>'
        f"{content_body}</section>",
        unsafe_allow_html=True,
    )

    if st.session_state.analysis_error:
        if st.session_state.get("analysis_error_kind") == "quota":
            label = config.AI_PROVIDERS[config.ai_provider()]["label"]
            st.error(
                f"{label}의 사용 한도에 도달했어요. 한도가 풀린 뒤 다시 시도하거나, "
                "설정에서 다른 AI 서비스·키로 바꿔주세요."
            )
        else:
            st.error("댓글을 만드는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        retry_col, settings_col = st.columns(2)
        with retry_col:
            if st.button("다시 시도", type="primary", icon=":material/refresh:", key="retry_analysis",
                         use_container_width=True):
                st.session_state.analysis_error = False
                st.rerun()
        with settings_col:
            if st.button("설정 열기", icon=":material/settings:", key="error_open_settings",
                         use_container_width=True):
                show_api_settings_dialog()

    if st.session_state.ai_result:
        ai = st.session_state.ai_result

        # -- 3. The concern, as the page's featured card --
        st.markdown(
            f'<section class="feature-card">'
            f'<div class="feature-label">영상 속 고민 한 줄</div>'
            f'<div class="feature-text">“<bdi>{html.escape(ai.get("concern", "").strip().strip(chr(34)))}</bdi>”</div>'
            f"</section>",
            unsafe_allow_html=True,
        )

        # -- 4. The generated comment, editable in place --
        with st.container(border=True):
            st.markdown(
                '<div class="section-head comment-card-head"><h4>생성된 댓글</h4>'
                "<p>필요하면 직접 고쳐 쓸 수 있어요</p></div>",
                unsafe_allow_html=True,
            )
            edited = st.text_area(
                "생성된 댓글",
                value=st.session_state.edited_comment,
                height=130,
                key="comment_edit_area",
                label_visibility="collapsed",
            )
            st.session_state.edited_comment = edited

            char_count = len(edited)
            is_valid = config.comment_min_chars() <= char_count <= config.comment_max_chars()
            limits = f"{config.comment_min_chars()}~{config.comment_max_chars()}자"
            st.markdown(
                f'<div class="count-row"><span class="count-chip {"ok" if is_valid else "bad"}">'
                f"{char_count}자</span><span>{limits} 사이로 맞춰주세요</span></div>",
                unsafe_allow_html=True,
            )

            regen_col, confirm_col = st.columns(2)
            with regen_col:
                regenerate_clicked = st.button(
                    "다시 생성", use_container_width=True,
                    icon=":material/refresh:", key="regenerate_comment",
                )
            with confirm_col:
                confirm_clicked = st.button(
                    "댓글 확정", use_container_width=True, type="primary",
                    icon=":material/check:", key="confirm_comment",
                )
            # The error belongs next to the button that caused it
            if confirm_clicked and not is_valid:
                st.error(f"댓글은 {limits}여야 합니다. 현재 {char_count}자입니다.")


        if regenerate_clicked:
            st.session_state.ai_result = None
            st.session_state.analysis_error = False
            st.rerun()

        if confirm_clicked and is_valid:
            st.session_state.confirmed_comment = edited
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
    daily_limit = config.daily_max_comments()
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
                _reset_generation()
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


DIALOG_PAGE_SIZE = 10
DIALOG_MAX_ROWS = 1000


def _shift_dialog_page(page_key: str, delta: int):
    st.session_state[page_key] += delta


def _dialog_rows(prefix: str, selected: date, rows_html: list[str], unit: str, empty_message: str):
    if not rows_html:
        st.markdown(f'<div class="profile-empty-state">{empty_message}</div>', unsafe_allow_html=True)
        return

    page_key, page_date_key = f"{prefix}_page", f"{prefix}_page_date"
    if st.session_state.get(page_date_key) != selected:
        st.session_state[page_date_key] = selected
        st.session_state[page_key] = 1
    total_pages = (len(rows_html) - 1) // DIALOG_PAGE_SIZE + 1
    page = st.session_state[page_key] = min(st.session_state[page_key], total_pages)
    start = (page - 1) * DIALOG_PAGE_SIZE
    page_rows = rows_html[start:start + DIALOG_PAGE_SIZE]

    st.markdown(f'<div class="dialog-count">{len(rows_html):,}{unit}</div>', unsafe_allow_html=True)
    # Only the rows scroll, so the date row and page buttons stay reachable.
    with st.container(height=min(440, 90 + 110 * len(page_rows)), border=False):
        st.markdown("".join(page_rows), unsafe_allow_html=True)

    if total_pages > 1:
        pag_prev, pag_info, pag_next = st.columns([1, 2, 1])
        with pag_prev:
            st.button(
                "← 이전", key=f"{prefix}_page_prev", use_container_width=True, disabled=page <= 1,
                on_click=_shift_dialog_page, args=(page_key, -1),
            )
        with pag_info:
            st.markdown(f'<div class="pagination-info">{page} / {total_pages}</div>', unsafe_allow_html=True)
        with pag_next:
            st.button(
                "다음 →", key=f"{prefix}_page_next", use_container_width=True, disabled=page >= total_pages,
                on_click=_shift_dialog_page, args=(page_key, 1),
            )


@st.dialog("📋 게시 기록", width="large")
def show_history_dialog():
    selected = _date_navigator("hist")
    profiles = config.load_profiles()
    rows = [_record_html(r, profiles) for r in database.get_history_by_date(selected, limit=DIALOG_MAX_ROWS)]
    _dialog_rows("hist", selected, rows, "건", "해당 날짜에 게시 기록이 없습니다.")


@st.dialog("🔧 오류 로그", width="large")
def show_error_log_dialog():
    selected = _date_navigator("log")
    lines = reversed(config.read_error_log_by_date(selected, limit=DIALOG_MAX_ROWS))
    rows = [f'<div class="log-line"><bdi>{html.escape(line)}</bdi></div>' for line in lines]
    _dialog_rows("log", selected, rows, "건", "해당 날짜에 기록된 오류가 없습니다.")


st.markdown("---")
_hist_col, _log_col = st.columns(2)
with _hist_col:
    if st.button("📋 게시 기록", use_container_width=True, key="open_hist"):
        st.session_state.hist_date = date.today()
        st.session_state.pop("hist_page_date", None)
        show_history_dialog()
with _log_col:
    if st.button("🔧 오류 로그", use_container_width=True, key="open_log"):
        st.session_state.log_date = date.today()
        st.session_state.pop("log_page_date", None)
        show_error_log_dialog()

_render_scroll_anchor()
