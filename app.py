"""YouTube Comment Agent Dashboard - Main Streamlit application."""

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
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS for a clean, professional look
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

    /* Column dividers */
    [data-testid="stHorizontalBlock"] > div:not(:last-child) {
        border-right: 1px solid #e0e0e0;
        padding-right: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "videos" not in st.session_state:
    st.session_state.videos = []
if "selected_video" not in st.session_state:
    st.session_state.selected_video = None
if "search_keyword" not in st.session_state:
    st.session_state.search_keyword = "연애"
if "last_search" not in st.session_state:
    st.session_state.last_search = ""


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

st.markdown("---")


# ---------------------------------------------------------------------------
# Three-column layout
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns([1, 1, 1])


# ===========================================================================
# Panel 1: 영상 불러오기
# ===========================================================================
with col1:
    st.subheader("1. 영상 불러오기")

    # --- Keyword search ---
    keyword = st.text_input(
        "검색 키워드",
        value=st.session_state.search_keyword,
        placeholder="예: 연애, 결혼, 소개팅 ...",
        key="keyword_input",
    )

    if st.button("🔍 영상 불러오기", use_container_width=True, type="primary"):
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
                    st.toast(f"'{keyword.strip()}' 검색 결과 {len(results)}개를 불러왔습니다.")
                else:
                    st.session_state.videos = []
                    st.warning("검색 결과가 없습니다. 다른 키워드를 시도해주세요.")

    # --- URL direct input ---
    st.markdown("")  # spacer
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
                            st.toast(f"'{details['title'][:30]}...' 영상을 선택했습니다.")
                            st.rerun()
                        else:
                            st.error("영상 정보를 불러올 수 없습니다. URL을 확인해주세요.")

    # --- Video list ---
    st.markdown("")  # spacer
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

            # Check if this video is currently selected
            is_selected = (
                st.session_state.selected_video
                and st.session_state.selected_video.get("videoId")
                == video.get("videoId")
            )

            with st.container():
                # Thumbnail + info side by side
                c_img, c_info = st.columns([1, 2])
                with c_img:
                    if thumb:
                        st.image(thumb, use_container_width=True)
                with c_info:
                    st.markdown(
                        f'<div class="video-title">{title}</div>'
                        f'<p class="video-meta">{channel} &middot; {published}</p>',
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
                                    # Use search result data as fallback
                                    st.session_state.selected_video = video
                                st.rerun()

                st.divider()
    else:
        st.info("키워드를 입력하고 '영상 불러오기' 버튼을 눌러주세요.")


# ===========================================================================
# Panel 2: 영상 분석 + 댓글 초안
# ===========================================================================
with col2:
    st.subheader("2. 영상 분석 + 댓글 초안")

    # Initialize panel-2 session state
    if "ai_result" not in st.session_state:
        st.session_state.ai_result = None
    if "confirmed_comment" not in st.session_state:
        st.session_state.confirmed_comment = None
    if "edited_comment" not in st.session_state:
        st.session_state.edited_comment = ""

    if st.session_state.selected_video:
        sv = st.session_state.selected_video
        video_id = sv.get("videoId", "")

        # -- Selected video info --
        thumb = sv.get("thumbnail", "")
        if thumb:
            st.image(thumb, use_container_width=True)
        st.markdown(f"**{sv.get('title', '제목 없음')}**")
        st.caption(
            f"{sv.get('channelTitle', '알 수 없음')} · "
            f"조회수 {youtube_api.format_view_count(sv.get('viewCount') or '0')} · "
            f"댓글 {youtube_api.format_view_count(sv.get('commentCount') or '0')}"
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
                    st.error(f"댓글 생성 중 오류가 발생했습니다: {e}")

        # -- Display AI results --
        if st.session_state.ai_result:
            ai = st.session_state.ai_result

            # Concern section
            st.markdown("#### 🔍 영상 속 고민")
            st.info(ai.get("concern", ""))

            # Warning if present
            if ai.get("warning"):
                st.warning(ai["warning"])

            # Editable comment section
            st.markdown("#### 💬 댓글 초안")
            edited = st.text_area(
                "댓글을 수정할 수 있습니다",
                value=st.session_state.edited_comment,
                height=120,
                key="comment_edit_area",
                label_visibility="collapsed",
            )
            st.session_state.edited_comment = edited

            # Character count indicator
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

            # AI reasoning expandable
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
                st.success("댓글이 확정되었습니다!")
                st.rerun()

        # Show confirmed state
        if st.session_state.confirmed_comment:
            st.success(f"확정된 댓글: {st.session_state.confirmed_comment[:50]}...")
    else:
        st.info("👈 왼쪽에서 영상을 선택해주세요")


# ===========================================================================
# Panel 3: 댓글 게시
# ===========================================================================
with col3:
    st.subheader("3. 댓글 게시")

    # Initialize panel-3 session state
    if "posting_status" not in st.session_state:
        st.session_state.posting_status = None
    if "post_result" not in st.session_state:
        st.session_state.post_result = None

    if st.session_state.confirmed_comment and st.session_state.selected_video:
        sv = st.session_state.selected_video
        video_id = sv.get("videoId", "")
        video_title = sv.get("title", "제목 없음")

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

        # Check 1: video eligibility
        if can_post:
            st.markdown("✅ 이 영상에 댓글 가능")
        else:
            st.markdown(f"❌ {can_post_msg}")

        # Check 2: daily quota
        if quota_ok:
            st.markdown(f"✅ 오늘 잔여 댓글 {posts_remaining}개 (사용 {today_posted}/{daily_limit})")
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
                status_messages = [
                    "프로필 여는 중",
                    "영상 페이지 이동 중",
                    "댓글 창 찾는 중",
                    "입력 중",
                    "게시 중",
                ]

                # Progress display
                progress_bar = st.progress(0)
                status_text = st.empty()

                def status_callback(msg: str):
                    """Update status display during posting."""
                    st.session_state.posting_status = msg
                    # Map known messages to progress values
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
                        status_text.markdown("**게시 완료 · 댓글 보기**")
                        status_container.update(label="게시 완료!", state="complete")
                        database.log_comment(
                            video_id=video_id,
                            video_title=video_title,
                            profile_index=selected_profile_index,
                            comment=comment_text,
                            success=True,
                        )
                        st.success("댓글이 성공적으로 게시되었습니다!")
                        # Clear confirmed comment after successful posting
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

        # -- Show previous result if exists --
        if st.session_state.post_result and not st.session_state.confirmed_comment:
            if st.session_state.post_result.get("success"):
                st.success("마지막 게시: 성공")
            else:
                st.error(
                    f"마지막 게시: 실패 - {st.session_state.post_result.get('error', '')}"
                )

    else:
        st.info("👈 패널 2에서 댓글을 확정해주세요")

    # -- History section (always visible) --
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
