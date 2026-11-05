import config
import difflib
import os
import json
import random
import re
import time
import urllib.request
import urllib.error


class RateLimitError(ValueError):
    """The AI service refused for quota/rate reasons (HTTP 429)."""


class ModelNotFoundError(ValueError):
    """The service does not offer the requested model (retired, renamed, or no access)."""


_MODEL_GONE = re.compile(r"model_not_found|does not exist|not found|not supported|no access|invalid model|not a valid model", re.I)
# Listed by the services but cannot write a chat reply
_NOT_CHAT_MODEL = re.compile(
    r"whisper|tts|orpheus|guard|safety|transcribe|embed|image|banana|lyria|robotics|computer-use|"
    r"deep-research|antigravity|rerank|ocr|moderation|audio|realtime|customtools|allam|code", re.I)


# Chosen by simulation on real videos (V1): analyze first, then write as that viewer.
# One-call prompts mixed analysis into the comment and sometimes dropped the brand.
_EXAMPLE = ("근데 진짜 남자심리는 알다가도 모르겠다...ㅠㅠ 맨날 연애하면 차이기만 했던 1인. 결국 심리 알기는 개뿔 "
            "그냥 인연이면 만나는 것 같아요. {brand} 연애사주가 그렇게 잘 본다던데 나도 언제 짝 만나는지 한번 보고 싶다.")

# With one fixed formula every comment repeated the same brand sentence, so the way in is
# drawn in code per comment, not left to the model.
_ANGLES = (
    "지금 마음 가는 그 사람이 내 인연이 맞는지 물어보고 싶다는 마음",
    "그래서 나는 언제쯤 제대로 된 사람을 만나는지, 시기가 궁금한 마음",
    "친구가 {brand} 얘기를 꺼냈던 게 떠오름 (이름을 들은 것까지만. 친구의 결과나 후기는 지어내지 말 것)",
    "이쯤 되면 {brand}에 물어봐야 하나 싶다는 반농담",
    "내가 문제인 건지 내 사주가 문제인 건지 {brand}에서 확인해 보고 싶다는 자조",
)


def _analysis_prompt(title, description, captions, popular_comments):
    comments_text = "\n".join(f"- {c['text'][:120]}" for c in popular_comments[:5]) or "(인기 댓글 없음)"
    source = (captions or "")[:3500] or "(자막 없음 - 제목과 설명으로 분석)"
    return f"""유튜브 연애 영상을 분석하세요. JSON만 출력.

제목: {title}
설명: {(description or '')[:300]}
자막(앞부분): {source}
인기 댓글:
{comments_text}

출력 형식:
{{"concern": "이 영상이 다루는 연애 고민 한 줄",
  "scenes": ["영상 속 구체적인 말이나 장면 3개 (자막에 실제로 나온 표현을 짧게, 자동 자막 오타는 바로잡고 뜻이 불분명한 말은 고르지 말 것)"],
  "viewer": "이 영상을 보고 댓글을 달 법한 시청자 한 명 (상황 한 줄, 예: 썸 타다 연락 끊긴 20대 직장인)"}}"""


def _comment_prompt(title, analysis, angle):
    brand, min_c, max_c = config.brand_name(), config.comment_min_chars(), config.comment_max_chars()
    scenes = " / ".join(str(s) for s in (analysis.get("scenes") or [])[:3])
    return f"""당신은 아래 시청자입니다. 방금 본 유튜브 영상에 댓글 하나를 답니다.

시청자: {analysis.get('viewer', '연애 고민이 있는 시청자')}
영상 제목: {title}
영상이 다루는 고민: {analysis.get('concern', '')}
영상 속 장면·말: {scenes}

## 쓰는 법
- 실제로 영상을 끝까지 본 그 시청자가 폰으로 대충 쓰는 말투 (반말·존댓말 섞여도 됨, ㅠㅠ·ㅋㅋ 한두 개 정도 OK)
- 영상 속 장면·말 중 하나를 꼭 집어서 언급 (제목을 그대로 따라 쓰지 말 것)
- 목표: 이 댓글을 읽은 사람이 "{brand}"에서 사주를 보고 싶어지게 만들기. 내 경험이나 처지 한 마디에서 자연스럽게 이어갈 것
- 이번 댓글에서 "{brand}"을 꺼내는 방향: {angle} (이 시청자의 상황에 맞는 내 말로 쓸 것)
- 공백 포함 {min_c}~{max_c}자, 2~3문장
- "영상 보면서", "도움이 됐어요" 같은 뻔한 첫마디로 시작하지 말 것. "공감"이라는 단어와 "주변 개입" 같은 분석투 표현은 아예 쓰지 말 것
- 영상 속 말을 따올 때는 짧은 구절을 "이렇게" 양쪽 따옴표로 감싸고, 아니면 따옴표 없이 쓸 것

## 절대 금지
- 링크, 해시태그
- {brand}을 직접 이용해 본 것처럼 지어낸 후기 ("받아봤는데", "다녀왔는데", "상담해보니" 등)
- 광고 문구처럼 들리는 칭찬

## 말투 참고용 (남자심리 영상의 댓글. 말투만 참고하고 이 문장들은 절대 재사용하지 말 것)
{_EXAMPLE.format(brand=brand)}

댓글만 한 줄로 출력하세요."""


def _post_json(url: str, body: dict, headers: dict, service: str) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers}
    )
    # HTTPS connections here occasionally fail certificate checks for a short while;
    # a short retry rides out the bad window.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="replace")[:500]
            if e.code == 429:
                error = RateLimitError
            elif e.code in (400, 403, 404) and "model" in err_body.lower() and _MODEL_GONE.search(err_body):
                error = ModelNotFoundError
            else:
                error = ValueError
            exc = error(f"{service} API 오류 ({e.code}): {err_body}")
            exc.retry_after = e.headers.get("Retry-After") if e.headers else None
            raise exc
        except urllib.error.URLError:
            if attempt == 2:
                raise
            time.sleep(1.0 * (attempt + 1))


def _empty(service: str, reason) -> ValueError:
    return ValueError(f"{service} 응답이 비어있습니다 (finish_reason={reason})")


def _call_openrouter(prompt: str, key: str, model: str) -> str:
    data = _post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500,
            # Reasoning models spent the whole token budget thinking and returned no answer
            # (finish_reason "length", empty content). The task needs no long thinking.
            "reasoning": {"enabled": False},
        },
        {"Authorization": f"Bearer {key}"},
        "OpenRouter",
    )
    choice = data["choices"][0]
    content = (choice["message"].get("content") or "").strip()
    if not content:
        # The reasoning text is never the answer, so it is not used as a fallback.
        raise _empty("OpenRouter", choice.get("finish_reason"))
    return content


def _call_gemini(prompt: str, key: str, model: str) -> str:
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 4096},
        },
        {"x-goog-api-key": key},
        "Gemini",
    )
    candidate = (data.get("candidates") or [{}])[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    content = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    if not content:
        raise _empty("Gemini", candidate.get("finishReason"))
    return content


def _call_openai(prompt: str, key: str, model: str) -> str:
    data = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            # Reasoning models count their thinking against this, so leave room
            "max_completion_tokens": 4096,
        },
        {"Authorization": f"Bearer {key}"},
        "OpenAI",
    )
    choice = data["choices"][0]
    content = (choice["message"].get("content") or "").strip()
    if not content:
        raise _empty("OpenAI", choice.get("finish_reason"))
    return content


def _extract_json(text: str, required: str = "concern") -> dict:
    """The first JSON object in the reply that has the required field, even if the model
    wrapped it in prose or a code fence."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text, match.start())
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get(required):
            return obj
    raise ValueError(f"AI 응답 파싱 실패: {text[:200]}")


def _call_anthropic(prompt: str, key: str, model: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    # Current Claude models always think; low effort keeps a short comment quick and cheap.
    # The installed SDK predates output_config / fallbacks, so they go through extra_body.
    # fallbacks="default" re-runs a declined request on another model inside the same call.
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"output_config": {"effort": "low"}, "fallbacks": "default"},
        )
    except anthropic.RateLimitError as e:
        # The SDK raises its own 429 type; map it so provider fallback sees it.
        raise RateLimitError(f"Claude API 오류 (429): {e}") from e
    except anthropic.NotFoundError as e:
        raise ModelNotFoundError(f"Claude API 오류 (404): {e}") from e
    if response.stop_reason == "refusal":
        raise ValueError("Claude가 요청을 거절했습니다 (refusal)")
    content = "".join(
        getattr(block, "text", "") for block in response.content if getattr(block, "type", "") == "text"
    ).strip()
    if not content:
        raise _empty("Claude", response.stop_reason)
    return content


def _compatible_caller(provider: str):
    def call(prompt: str, key: str, model: str) -> str:
        data = _post_json(
            f"{config.ai_base_url(provider).rstrip('/')}/chat/completions",
            {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 4096},
            # Cloudflare-fronted APIs such as Groq reject urllib's default User-Agent
            {"Authorization": f"Bearer {key}", "User-Agent": "marketing-ai-agent/1.0"},
            config.AI_PROVIDERS[provider]["label"],
        )
        choice = data["choices"][0]
        content = (choice["message"].get("content") or "").strip()
        if not content:
            raise _empty(config.AI_PROVIDERS[provider]["label"], choice.get("finish_reason"))
        return content
    return call


_CALLERS = {
    "openrouter": _call_openrouter,
    "gemini": _call_gemini,
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    **{p: _compatible_caller(p) for p, info in config.AI_PROVIDERS.items() if info.get("base_url")},
}


def _list_model_ids(provider: str, key: str) -> list[str]:
    if provider == "gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200"
        headers = {"x-goog-api-key": key}
    elif provider == "anthropic":
        url, headers = "https://api.anthropic.com/v1/models?limit=100", {"x-api-key": key, "anthropic-version": "2023-06-01"}
    elif provider == "openrouter":
        url, headers = "https://openrouter.ai/api/v1/models", {"Authorization": f"Bearer {key}"}
    elif provider == "openai":
        url, headers = "https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"}
    else:
        url, headers = f"{config.ai_base_url(provider).rstrip('/')}/models", {"Authorization": f"Bearer {key}"}
    req = urllib.request.Request(url, headers={"User-Agent": "marketing-ai-agent/1.0", **headers})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())
    if provider == "gemini":
        return [m["name"].removeprefix("models/") for m in data.get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])]
    return [m.get("id") or m.get("name") for m in data.get("data", data.get("models", []))]


_ranked_models = {}


def _rank_models(provider: str, key: str) -> list[str]:
    """The service's own chat models, best guess first. Kept for the process once listed."""
    if provider not in _ranked_models:
        ids = [m for m in _list_model_ids(provider, key) if m and not _NOT_CHAT_MODEL.search(m)]
        if provider == "openrouter":  # the paid models bill the user's account
            ids = [m for m in ids if m.endswith(":free")]
        prefer = config.AI_PROVIDERS[provider].get("prefer", ())
        rank = lambda m: next((i for i, part in enumerate(prefer) if part in m), len(prefer))
        _ranked_models[provider] = sorted(ids, key=rank)  # stable: keeps the service's order within a rank
    return _ranked_models[provider]


def _call_provider(provider: str, prompt: str, key: str) -> str:
    """Use the model from settings if there is one; otherwise, or if the service no longer
    offers it, pick from the service's current list."""
    saved = config.ai_model(provider)
    last = None
    if saved:
        try:
            return _CALLERS[provider](prompt, key, saved)
        except ModelNotFoundError as e:
            config.log_error("ai_model_missing", e, f"{provider}:{saved}")
            last = e
    label = config.AI_PROVIDERS[provider]["label"]
    try:
        candidates = _rank_models(provider, key)
    except (OSError, ValueError, KeyError) as e:
        raise ValueError(f"{label} 모델 목록을 가져오지 못했습니다. 설정에서 모델 ID를 직접 입력해 주세요. ({e})") from e
    for model in [m for m in candidates if m != saved][:5]:
        try:
            content = _CALLERS[provider](prompt, key, model)
        except ModelNotFoundError as e:
            last = e
            continue
        candidates.remove(model)
        candidates.insert(0, model)  # later calls start from the one that worked
        return content
    raise last or ValueError(f"{label}에서 쓸 수 있는 모델을 찾지 못했습니다. 설정에서 모델 ID를 직접 입력해 주세요.")


def _call_model(prompt: str) -> str:
    provider = config.ai_provider()
    key = config.ai_key(provider)
    if not key:
        label = config.AI_PROVIDERS[provider]["label"]
        raise ValueError(f"{label} API 키가 설정되지 않았습니다. 상단 설정에서 키를 입력하세요.")
    try:
        return _call_provider(provider, prompt, key)
    except RateLimitError as e:
        try:
            delay = min(float(getattr(e, "retry_after", None) or 2), 5)
        except ValueError:  # Retry-After may be an HTTP date
            delay = 2
        time.sleep(delay)
        try:
            return _call_provider(provider, prompt, key)
        except RateLimitError as e2:
            last = e2
    tried = provider
    for other in config.AI_PROVIDERS:
        other_key = config.ai_key(other)
        if other == provider or not other_key:
            continue
        config.log_error("ai_fallback", last, f"{tried}->{other}")
        try:
            return _call_provider(other, prompt, other_key)
        except RateLimitError as e:
            last, tried = e, other
        except Exception as e:  # a backup that is down must not hide the next one
            config.log_error("ai_fallback_failed", e, other)
            tried = other
    raise last


def _fit_length(comment: str) -> str:
    """Models overshoot a character range they cannot count, so ask for a concrete shape
    (two short sentences around a target length) up to twice, and keep the first rewrite
    that fits. Keeps the original if none fits or the calls fail."""
    min_c, max_c = config.comment_min_chars(), config.comment_max_chars()
    brand = config.brand_name()
    low, high = max(min_c, max_c - 40), max_c - 10  # aim for the top of the range, not the floor
    for _ in range(2):
        prompt = f"""아래 유튜브 댓글을 짧게 줄여주세요.
- 한 줄, 두 문장, 공백 포함 {low}~{high}자 (절대 {max_c}자를 넘기지 말 것)
- 원래 댓글의 뜻과 말투 유지: 영상 속 구체적인 내용과 "{brand}"이라는 이름은 꼭 남길 것
- 링크·해시태그·직접 이용한 척하는 후기 금지
- 따옴표나 설명 없이 댓글만 출력

댓글: {comment}"""
        try:
            shorter = _one_line(_call_model(prompt).strip('"“”'))
        except Exception:
            return comment
        # A rewrite only counts if it fits and still carries the brand
        if min_c <= len(shorter) <= max_c and brand in shorter:
            return shorter
    return comment


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _fix_quotes(text: str) -> str:
    """Quotes must wrap a phrase on both sides. Models sometimes drop the opening mark
    ('…심심했어요" 이 말'), so keep only marks that pair up and remove the strays
    instead of guessing where a quote should have opened."""
    chars, stack, drop, pairs = list(text), [], set(), {}
    for i, ch in enumerate(chars):
        if ch == '"':
            before = chars[i - 1] if i else " "
            after = chars[i + 1] if i + 1 < len(chars) else " "
            # Glued to the word before and followed by a break: a closing mark
            closes = not before.isspace() and (after.isspace() or after in ".,!?~")
            if stack and (closes or chars[stack[-1]] == '"'):
                ch = "”"
            elif closes:
                drop.add(i)  # closes something that never opened
                continue
            else:
                ch = "“"
        if ch == "“":
            stack.append(i)
        elif ch == "”":
            if stack:
                opener = stack.pop()
                chars[i] = "”" if chars[opener] == "“" else '"'
                pairs[opener] = i
            else:
                drop.add(i)
    drop.update(stack)  # openers that never closed
    kept = [(i, c) for i, c in enumerate(chars) if i not in drop]
    # A pair wrapping the whole comment is not a quote of anything
    if len(kept) >= 2 and pairs.get(kept[0][0]) == kept[-1][0]:
        kept = kept[1:-1]
    return _one_line("".join(c for _, c in kept))


_QUICK_RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor", "im_not_ai", "quick-rules.md")


def _change_rate(before: str, after: str) -> float:
    """im-not-ai's change rate (metrics_v2.change_rate): 1 - character-level similarity."""
    return 1.0 - difflib.SequenceMatcher(None, before, after, autojunk=False).ratio()


def _humanize(comment: str) -> str:
    """Final pass with im-not-ai (MIT, github.com/epoko77-ai/im-not-ai): its quick-rules
    rulebook as an L1 post-edit, then its gates in code. A rewrite that changes too much
    (>=50%), breaks the length rule, drops the brand, or adds numbers is discarded."""
    try:
        with open(_QUICK_RULES_PATH, encoding="utf-8") as f:
            rules = f.read()
    except OSError:
        return comment
    brand, min_c, max_c = config.brand_name(), config.comment_min_chars(), config.comment_max_chars()
    prompt = f"""{rules}

---
## 이번 작업
장르: 유튜브 댓글(구어체, 2~3문장). 위 룰북으로 AI 티가 나는 표현만 고치세요.
- 구어 감탄(ㅠㅠ, ㅋㅋ, ...)과 반말·존댓말 섞임은 사람 댓글의 특징이므로 보존
- "{brand}"이라는 이름, 영상 장면 언급, 댓글의 뜻은 그대로 유지
- 내용 추가 금지, 고칠 게 없으면 원문 그대로
- 공백 포함 {min_c}~{max_c}자 유지
- 고친 댓글 한 줄만 출력

댓글: {comment}"""
    try:
        edited = _one_line(_call_model(prompt).strip('"“”'))
    except RateLimitError:
        raise
    except Exception:
        return comment
    new_numbers = set(re.findall(r"\d+", edited)) - set(re.findall(r"\d+", comment))
    if (_change_rate(comment, edited) < 0.5 and min_c <= len(edited) <= max_c
            and brand in edited and not new_numbers):
        return edited
    return comment


def _copies_example(comment: str) -> bool:
    """True if a sentence of the comment is the example's brand sentence or close to it."""
    if "그렇게 잘 본다던데" in comment:
        return True
    target = next(s for s in re.split(r"(?<=[.!?])\s+", _EXAMPLE) if "{brand}" in s).format(brand=config.brand_name())
    return any(difflib.SequenceMatcher(None, s, target, autojunk=False).ratio() >= 0.7
               for s in re.split(r"(?<=[.!?])\s+", comment))


def _write_comment(title: str, analysis: dict) -> str:
    brand = config.brand_name()
    angles = random.sample(_ANGLES, 2)  # the second is only for the one retry
    comment = _fix_quotes(_call_model(_comment_prompt(title, analysis, angles[0].format(brand=brand))))
    if _copies_example(comment):
        comment = _fix_quotes(_call_model(_comment_prompt(title, analysis, angles[1].format(brand=brand))))
    return comment


def generate_comment(title: str, description: str, captions: str | None, popular_comments: list[dict]) -> dict:
    # 1. Analyze: the concern, concrete scenes, and a viewer who would comment
    analysis = _extract_json(_call_model(_analysis_prompt(title, description, captions, popular_comments)))
    # 2. Write as that viewer
    comment = _write_comment(title, analysis)
    # 3. Fit the length rule when the model overshoots
    if not config.comment_min_chars() <= len(comment) <= config.comment_max_chars():
        comment = _fix_quotes(_fit_length(comment))
    # 4. Naturalness pass (im-not-ai), only within the rules
    if config.comment_min_chars() <= len(comment) <= config.comment_max_chars():
        comment = _fix_quotes(_humanize(comment))

    result = {"concern": analysis.get("concern", ""), "comment": comment,
              "reasoning": " / ".join(str(s) for s in (analysis.get("scenes") or [])[:3])}
    comment_len = len(result["comment"])
    if comment_len < config.comment_min_chars() or comment_len > config.comment_max_chars():
        result["warning"] = f"댓글 길이 {comment_len}자 (기준: {config.comment_min_chars()}~{config.comment_max_chars()}자)"

    return result
