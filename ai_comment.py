import config
import json
import re
import urllib.request
import urllib.error


def _build_prompt(title, description, captions, popular_comments):
    comments_text = "\n".join(f"- {c['text']}" for c in popular_comments) if popular_comments else "(인기 댓글 없음)"
    caption_text = captions or "(자막 없음 - 제목과 설명으로 분석)"
    brand = config.BRAND_NAME
    min_c = config.COMMENT_MIN_CHARS
    max_c = config.COMMENT_MAX_CHARS

    return f"""당신은 유튜브 연애 관련 영상을 보고 댓글을 다는 일반 시청자입니다.

아래 영상 정보를 분석하고 두 가지를 작성하세요:

1. **영상 속 고민 한 줄**: 이 영상이 다루는 연애 고민을 한 문장으로 요약
2. **댓글 초안**: 아래 규칙을 지켜 작성

## 영상 정보
- 제목: {title}
- 설명: {description}
- 자막: {caption_text}
- 인기 댓글:
{comments_text}

## 댓글 작성 규칙 (반드시 준수)
- 글자 수: 반드시 {min_c}~{max_c}자 (초과 시 실패 처리됨, {max_c}자 절대 넘기지 마세요)
- 이 영상을 실제로 본 시청자의 말투로 자연스럽게
- 영상 속 구체적인 장면이나 말을 하나 이상 언급
- 공감 → 개인 경험 → "{brand}" 연애 사주에 대한 호기심으로 자연스럽게 이어지도록
- 절대 금지: 링크, 해시태그, {brand}을 직접 이용해 본 것처럼 지어낸 후기
- "{brand}"은 연애 사주를 잘 봐주는 곳으로 유명한 곳이라는 뉘앙스만

## 출력 형식 (JSON)
{{"concern": "영상 속 고민 한 줄 요약", "comment": "댓글 초안", "reasoning": "이 댓글이 왜 이 영상에 맞는지 한 줄 설명"}}

JSON만 출력하세요."""


def _call_openrouter(prompt: str) -> str:
    body = json.dumps({
        "model": config.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")[:500]
        raise ValueError(f"OpenRouter API 오류 ({e.code}): {err_body}")

    msg = data["choices"][0]["message"]
    content = msg.get("content") or msg.get("reasoning_content") or msg.get("reasoning") or ""
    if not content:
        raise ValueError(f"AI 응답이 비어있습니다: {json.dumps(msg, ensure_ascii=False)[:300]}")
    return content.strip()


def _call_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_comment(title: str, description: str, captions: str | None, popular_comments: list[dict]) -> dict:
    prompt = _build_prompt(title, description, captions, popular_comments)

    if config.AI_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        text = _call_anthropic(prompt)
    elif config.OPENROUTER_API_KEY:
        text = _call_openrouter(prompt)
    else:
        raise ValueError("API 키가 설정되지 않았습니다. .env에 OPENROUTER_API_KEY 또는 ANTHROPIC_API_KEY를 입력하세요.")

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"AI 응답 파싱 실패: {text[:200]}")

    result = json.loads(match.group(0))

    comment_len = len(result["comment"])
    if comment_len < config.COMMENT_MIN_CHARS or comment_len > config.COMMENT_MAX_CHARS:
        result["warning"] = f"댓글 길이 {comment_len}자 (기준: {config.COMMENT_MIN_CHARS}~{config.COMMENT_MAX_CHARS}자)"

    return result
