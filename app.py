"""YouTube Comment Agent Dashboard - Main Streamlit application (step-based wizard)."""

import streamlit as st

import ai_comment
import browser_automation
import config
import database
import youtube_api


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="YouTube Comment Agent",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Tighten top padding */
    .block-container {
        padding-top: 1.5rem;
    }

    /* Video card styling */
    .video-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 8px;
        background-color: #fafafa;
        transition: box-shadow 0.2s;
    }
    .video-card:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }
    [data-testid="stAppViewContainer"][data-theme="dark"] .video-card,
    .stApp[data-theme="dark"] .video-card {
        border-color: #444;
        background-color: #262730;
    }

    .video-title {
        font-size: 0.9rem;
        font-weight: 600;
        line-height: 1.3;
        margin-bottom: 2px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .video-meta {
        font-size: 0.78rem;
        color: #666;
        margin-bottom: 0;
    }

    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .status-ok {
        background-color: #d4edda;
        color: #155724;
    }
    .status-warn {
        background-color: #fff3cd;
        color: #856404;
    }
    .status-full {
        background-color: #f8d7da;
        color: #721c24;
    }

    /* Step indicator */
    .step-bar {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0;
        margin: 0.5rem 0 1.2rem 0;
        padding: 0.8rem 1rem;
        background: #f8f9fa;
        border-radius: 12px;
        border: 1px solid #e9ecef;
    }
    .stApp[data-theme="dark"] .step-bar,
    [data-testid="stAppViewContainer"][data-theme="dark"] .step-bar {
        background: #1e1e2e;
        border-color: #333;
    }
    .step-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 18px;
        border-radius: 8px;
        font-size: 0.95rem;
        font-weight: 500;
        color: #999;
        transition: all 0.2s;
        white-space: nowrap;
    }
    .step-item.active {
        background: #4A90D9;
        color: #fff;
        box-shadow: 0 2px 8px rgba(74,144,217,0.3);
    }
    .step-item.completed {
        color: #28a745;
        font-weight: 600;
    }
    .step-arrow {
        font-size: 1.1rem;
        color: #ccc;
        margin: 0 6px;
    }
    .stApp[data-theme="dark"] .step-arrow {
        color: #555;
    }
    .step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        font-size: 0.82rem;
        font-weight: 700;
        border: 2px solid #ccc;
        color: #999;
        flex-shrink: 0;
    }
    .step-item.active .step-num {
        background: #fff;
        color: #4A90D9;
        border-color: #fff;
    }
    .step-item.completed .step-num {
        background: #28a745;
        color: #fff;
        border-color: #28a745;
    }

    /* Selected video summary card */
    .selected-video-card {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 12px 16px;
        background: #f0f7ff;
        border: 1px solid #b8d4f0;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .stApp[data-theme="dark"] .selected-video-card,
    [data-testid="stAppViewContainer"][data-theme="dark"] .selected-video-card {
        background: #1a2a3d;
        border-color: #2a4a6d;
    }
    .selected-video-card img {
        width: 120px;
        border-radius: 6px;
    }
    .selected-video-info {
        flex: 1;
    }
    .selected-video-info .title {
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 2px;
    }
    .selected-video-info .meta {
        font-size: 0.82rem;
        color: #888;
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
# Sidebar: Chrome profile management
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Chrome 프로필 관리")
    st.caption("댓글 게시에 사용할 Chrome 프로필 경로를 등록하세요.")
    st.markdown("**chrome://version** 에서 '프로필 경로'를 확인할 수 있습니다.")
    st.markdown("---")

    if "profiles_list" not in st.session_state:
        st.session_state.profiles_list = config.load_profiles()

    profiles_list = st.session_state.profiles_list

    # Display existing profiles
    for i, profile in enumerate(profiles_list):
        col_name, col_del = st.columns([4, 1])
        with col_name:
            st.text_input(
                f"프로필 {i + 1} 이름",
                value=profile.get("name", ""),
                key=f"pname_{i}",
                label_visibility="collapsed",
                placeholder="프로필 이름",
                on_change=lambda idx=i: profiles_list.__setitem__(
                    idx,
                    {
                        **profiles_list[idx],
                        "name": st.session_state[f"pname_{idx}"],
                    },
                ),
            )
        with col_del:
            if st.button("🗑", key=f"pdel_{i}", help="프로필 삭제"):
                profiles_list.pop(i)
                config.save_profiles(profiles_list)
                st.session_state.profiles_list = profiles_list
                st.rerun()

        st.text_input(
            f"프로필 {i + 1} 경로",
            value=profile.get("path", ""),
            key=f"ppath_{i}",
            label_visibility="collapsed",
            placeholder="C:/Users/.../Chrome/User Data/Profile 1",
            on_change=lambda idx=i: profiles_list.__setitem__(
                idx,
                {
                    **profiles_list[idx],
                    "path": st.session_state[f"ppath_{idx}"],
                },
            ),
        )
        if i < len(profiles_list) - 1:
            st.markdown("---")

    st.markdown("")

    # Add new profile
    if st.button("+ 프로필 추가", use_container_width=True):
        n = len(profiles_list) + 1
        profiles_list.append({"name": f"유튜브{n}", "path": ""})
        st.session_state.profiles_list = profiles_list
        st.rerun()

    # Save button
    if st.button("💾 프로필 저장", use_container_width=True, type="primary"):
        valid = [p for p in profiles_list if p.get("path", "").strip()]
        config.save_profiles(valid)
        st.session_state.profiles_list = valid
        config.CHROME_PROFILES = [p["path"] for p in valid]
        st.toast(f"{len(valid)}개 프로필이 저장되었습니다.")
        st.rerun()

    if not profiles_list:
        st.info("등록된 프로필이 없습니다. 프로필을 추가해주세요.")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("YouTube Comment Agent Dashboard")

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

st.markdown(
    f'<span class="status-badge {badge_class}">{badge_text}</span>',
    unsafe_allow_html=True,
)


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
        f'<span class="step-num">{num_inner}</span>{label}</div>'
    )
    if i < len(step_labels):
        step_html_parts.append('<span class="step-arrow">&#x279C;</span>')

st.markdown(
    '<div class="step-bar">' + "".join(step_html_parts) + "</div>",
    unsafe_allow_html=True,
)


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

    btn_search_col, btn_trending_col = st.columns(2)
    with btn_search_col:
        search_clicked = st.button(
            "🔍 영상 불러오기", use_container_width=True, type="primary"
        )
    with btn_trending_col:
        trending_clicked = st.button("🔥 뜨는 영상", use_container_width=True)

    if search_clicked:
        if not config.YOUTUBE_API_KEY:
            st.error("YouTube API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        elif not keyword.strip():
            st.warning("검색 키워드를 입력해주세요.")
        else:
            st.session_state.search_keyword = keyword.strip()
            with st.spinner("영상을 검색하고 있습니다..."):
                results = youtube_api.search_videos(
                    keyword=keyword.strip(), max_results=20
                )
                if results:
                    st.session_state.videos = results
                    st.session_state.last_search = keyword.strip()
                    st.toast(
                        f"'{keyword.strip()}' 검색 결과 {len(results)}개를 불러왔습니다."
                    )
                else:
                    st.session_state.videos = []
                    st.warning("검색 결과가 없습니다. 다른 키워드를 시도해주세요.")

    if trending_clicked:
        if not config.YOUTUBE_API_KEY:
            st.error("YouTube API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        else:
            kw = keyword.strip() or "연애"
            with st.spinner("뜨기 직전 영상을 찾고 있습니다..."):
                results = youtube_api.search_trending_videos(
                    keyword=kw, max_results=20
                )
                if results:
                    st.session_state.videos = results
                    st.session_state.last_search = f"🔥 {kw} (뜨는 영상)"
                    st.toast(f"뜨기 직전 영상 {len(results)}개를 찾았습니다!")
                else:
                    st.session_state.videos = []
                    st.warning(
                        "조건에 맞는 뜨기 직전 영상이 없습니다. 일반 검색을 이용해주세요."
                    )

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
                else:
                    with st.spinner("영상 정보를 불러오는 중..."):
                        details = youtube_api.get_video_details(vid)
                        if details:
                            st.session_state.selected_video = details
                            st.session_state.ai_result = None
                            st.session_state.confirmed_comment = None
                            st.session_state.edited_comment = ""
                            st.toast(
                                f"'{details['title'][:30]}...' 영상을 선택했습니다."
                            )
                            go_to_step(2)
                        else:
                            st.error(
                                "영상 정보를 불러올 수 없습니다. URL을 확인해주세요."
                            )

    # --- Video list ---
    st.markdown("")
    videos = st.session_state.videos

    if videos:
        if st.session_state.last_search:
            st.caption(
                f"'{st.session_state.last_search}' 검색 결과 ({len(videos)}개)"
            )

        for idx, video in enumerate(videos):
            published = youtube_api.format_publish_date(video.get("publishedAt", ""))
            channel = video.get("channelTitle", "알 수 없음")
            title = video.get("title", "제목 없음")
            thumb = video.get("thumbnail", "")

            is_selected = (
                st.session_state.selected_video
                and st.session_state.selected_video.get("videoId")
                == video.get("videoId")
            )

            with st.container():
                c_img, c_info = st.columns([1, 3])
                with c_img:
                    if thumb:
                        st.image(thumb, use_container_width=True)
                with c_info:
                    vph = video.get("viewsPerHour")
                    vph_badge = (
                        f' <span style="background:#ff4444;color:#fff;padding:1px 6px;'
                        f'border-radius:8px;font-size:0.72rem;">🔥 {vph}회/h</span>'
                        if vph
                        else ""
                    )
                    views_text = (
                        f" · 조회수 {youtube_api.format_view_count(video.get('viewCount', '0'))}"
                        if video.get("viewCount")
                        else ""
                    )
                    st.markdown(
                        f'<div class="video-title">{title}{vph_badge}</div>'
                        f'<p class="video-meta">{channel} &middot; {published}{views_text}</p>',
                        unsafe_allow_html=True,
                    )

                    if is_selected:
                        st.success("선택됨", icon="✅")
                    else:
                        if st.button(
                            "선택",
                            key=f"select_{idx}",
                            use_container_width=True,
                        ):
                            with st.spinner("상세 정보 로딩 중..."):
                                details = youtube_api.get_video_details(
                                    video["videoId"]
                                )
                                if details:
                                    st.session_state.selected_video = details
                                else:
                                    st.session_state.selected_video = video
                                # Reset downstream state when selecting a new video
                                st.session_state.ai_result = None
                                st.session_state.confirmed_comment = None
                                st.session_state.edited_comment = ""
                                go_to_step(2)

                st.divider()
    else:
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
    v_title = sv.get("title", "제목 없음")
    v_channel = sv.get("channelTitle", "알 수 없음")
    v_views = youtube_api.format_view_count(sv.get("viewCount") or "0")
    v_comments = youtube_api.format_view_count(sv.get("commentCount") or "0")

    col_thumb, col_info = st.columns([1, 3])
    with col_thumb:
        if thumb:
            st.image(thumb, use_container_width=True)
    with col_info:
        st.markdown(f"**{v_title}**")
        st.caption(f"{v_channel} · 조회수 {v_views} · 댓글 {v_comments}")

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
                st.error(f"댓글 생성 중 오류가 발생했습니다: {e}")

    # -- Display AI results --
    if st.session_state.ai_result:
        ai = st.session_state.ai_result

        st.markdown("#### 🔍 영상 속 고민")
        st.info(ai.get("concern", ""))

        if ai.get("warning"):
            st.warning(ai["warning"])

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
            st.markdown(f"**분석 이유:** {ai.get('reasoning', '')}")
            pop_comments = ai.get("_popular_comments", [])
            if pop_comments:
                st.markdown("**참고한 인기 댓글:**")
                for pc in pop_comments[:5]:
                    likes = pc.get("likeCount", 0)
                    st.markdown(f"- 👍 {likes} | {pc.get('text', '')[:80]}")

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
    st.info(st.session_state.confirmed_comment)
    st.caption(f"대상 영상: {video_title}")

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
                    st.error(f"게시 실패: {error_msg}")

            except Exception as e:
                status_container.update(label="게시 실패", state="error")
                database.log_comment(
                    video_id=video_id,
                    video_title=video_title,
                    profile_index=selected_profile_index,
                    comment=comment_text,
                    success=False,
                    error=str(e),
                )
                st.error(f"게시 중 오류 발생: {e}")

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
                f"마지막 게시: 실패 - {st.session_state.post_result.get('error', '')}"
            )


# ===========================================================================
# Posting history (always accessible at the bottom)
# ===========================================================================
st.markdown("---")
with st.expander("📋 게시 기록", expanded=False):
    history = database.get_history(limit=100)
    if history:
        for record in history:
            r_title = record.get("video_title", "")[:25]
            r_profile = f"유튜브{record.get('profile_index', 0) + 1}"
            r_comment = record.get("comment", "")[:40]
            r_success = "✅" if record.get("success") else "❌"
            r_time = record.get("created_at", "")
            r_error = record.get("error", "")

            cols = st.columns([1, 4])
            with cols[0]:
                st.markdown(r_success)
            with cols[1]:
                st.markdown(
                    f"**{r_title}{'...' if len(record.get('video_title', '')) > 25 else ''}**  \n"
                    f"<span style='font-size:0.82rem; color:#888;'>"
                    f"{r_profile} · {r_time}</span>  \n"
                    f"<span style='font-size:0.85rem;'>"
                    f"{r_comment}{'...' if len(record.get('comment', '')) > 40 else ''}</span>",
                    unsafe_allow_html=True,
                )
                if r_error:
                    st.caption(f"오류: {r_error}")
            st.divider()
    else:
        st.caption("아직 게시 기록이 없습니다.")
