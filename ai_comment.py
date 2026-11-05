import anthropic
from config import ANTHROPIC_API_KEY, BRAND_NAME, COMMENT_MIN_CHARS, COMMENT_MAX_CHARS
import json
import re


client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_comment(title: str, description: str, captions: str | None, popular_comments: list[dict]) -> dict:
    comments_text = "\n".join(f"- {c['text']}" for c in popular_comments) if popular_comments else "(인기 댓글 없음)"
    caption_text = captions or "(자막 없음 - 제목과 설명으로 분석)"

    prompt = f"""당신은 유튜브 연애 관련 영상을 보고 댓글을 다는 일반 시청자입니다.

아래 영상 정보를 분석하고 두 가지를 작성하세요:

1. **영상 속 고민 한 줄**: 이 영상이 다루는 연애 고민을 한 문장으로 요약
2. **댓글 초안**: 아래 규칙을 지켜 작성

## 영상 정보
- 제목: {title}
- 설명: {description}
- 자막: {caption_text}
- 인기 댓글:
{comments_text}

## 댓글 작성 규칙
- {COMMENT_MIN_CHARS}~{COMMENT_MAX_CHARS}자
- 이 영상을 실제로 본 시청자의 말투로 자연스럽게
- 영상 속 구체적인 장면이나 말을 하나 이상 언급
- 공감 → 개인 경험 → "{BRAND_NAME}" 연애 사주에 대한 호기심으로 자연스럽게 이어지도록
- 절대 금지: 링크, 해시태그, {BRAND_NAME}을 직접 이용해 본 것처럼 지어낸 후기
- "{BRAND_NAME}"은 연애 사주를 잘 봐주는 곳으로 유명한 곳이라는 뉘앙스만

## 출력 형식 (JSON)
{{"concern": "영상 속 고민 한 줄 요약", "comment": "댓글 초안", "reasoning": "이 댓글이 왜 이 영상에 맞는지 한 줄 설명"}}

JSON만 출력하세요."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("AI 응답 파싱 실패")

    result = json.loads(match.group(0))

    comment_len = len(result["comment"])
    if comment_len < COMMENT_MIN_CHARS or comment_len > COMMENT_MAX_CHARS:
        result["warning"] = f"댓글 길이 {comment_len}자 (기준: {COMMENT_MIN_CHARS}~{COMMENT_MAX_CHARS}자)"

    return result
