# 운명원 마케팅 AI 에이전트

유튜브 연애 영상에 맥락에 맞는 댓글을 자동으로 작성·게시하는 AI 에이전트 대시보드입니다.

## 핵심 기능

| 단계 | 기능 |
|------|------|
| 1. 영상 선택 | 키워드 검색 또는 URL 직접 입력으로 유튜브 영상 로드 (썸네일·제목·채널·날짜), 페이지네이션 |
| 2. 댓글 생성 | AI가 영상 자막·인기 댓글을 분석하여 시청자 페르소나 기반 댓글 초안 생성, 자동 심사·윤문 |
| 3. 댓글 게시 | 연결된 Google 계정으로 자동 게시, 프로필 랜덤 선택 |

## 댓글 생성 흐름

1. **영상 분석**: 제목·설명·자막·인기 댓글로 영상 속 연애 고민 한 줄, 구체적인 장면·말 3개, 댓글을 달 법한 시청자 한 명을 뽑음
2. **후보 3개 작성**: 그 시청자가 되어 쓰고, 운명원으로 이어지는 주제는 후보마다 다르게 배정. 운명원 이름이 없거나 실제 댓글을 베낀 후보는 버림
3. **심사·윤문**: im-not-ai 룰북으로 가장 나은 후보를 고르고 어색한 문장만 고침. 고친 문장이 원본보다 나을 때만 채택
4. **길이 맞춤**: 40~120자를 벗어나면 줄여 쓰기 요청

AI 서비스는 설정에서 고른 것부터 쓰고, 한도·오류가 나면 키가 있는 다음 서비스로 바로 넘어갑니다. 댓글을 쓰는 단계는 Gemini를 먼저 씁니다. 자세한 설계는 [docs/TASK_ANALYSIS.md](docs/TASK_ANALYSIS.md)에 있습니다.

## 사용한 오픈소스

| 오픈소스 | 버전 | 라이선스 | 용도 |
|----------|------|----------|------|
| [Python](https://www.python.org/) | 3.12 | PSF License | 런타임 |
| [Streamlit](https://github.com/streamlit/streamlit) | 1.40.2 | Apache 2.0 | 대시보드 UI |
| [Playwright for Python](https://github.com/microsoft/playwright-python) | 1.49.1 | Apache 2.0 | Chrome 자동화 (Google 로그인 · 댓글 게시) |
| [google-api-python-client](https://github.com/googleapis/google-api-python-client) | 2.154.0 | Apache 2.0 | YouTube Data API 호출 |
| [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) | 1.2.4 | MIT | 영상 자막 가져오기 |
| [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) | 0.39.0 | MIT | Claude API 호출 |
| [PyYAML](https://github.com/yaml/pyyaml) | 6.0.2 | MIT | `settings.yaml` 읽기·쓰기 |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.0.1 | BSD-3-Clause | 예전 `.env` 설정을 `settings.yaml`로 옮길 때 사용 |
| [SQLite](https://www.sqlite.org/) | Python 내장 | Public Domain | 게시 기록 저장 |
| [im-not-ai](https://github.com/epoko77-ai/im-not-ai) (© 2026 epoko77-ai) | `vendor/im_not_ai/` 에 포함 | MIT | 댓글 심사·윤문 단계의 AI 말투 탐지 룰북(`quick-rules.md`)과 변경률 기준 |

im-not-ai는 원본 라이선스 전문을 [vendor/im_not_ai/LICENSE](vendor/im_not_ai/LICENSE)에 함께 두었습니다.

## 외부 서비스 (API)

오픈소스가 아니라 키를 발급받아 호출하는 서비스입니다.

| 서비스 | 용도 |
|--------|------|
| [YouTube Data API v3](https://developers.google.com/youtube/v3) | 영상 검색 · 상세 정보 · 인기 댓글 |
| [Google Gemini API](https://ai.google.dev/) | 영상 분석 · 심사 · 댓글 작성 (작성 단계는 Gemini 먼저) |
| [Anthropic Claude API](https://docs.anthropic.com/) | 영상 분석 · 심사 · 댓글 작성 |
| [OpenRouter](https://openrouter.ai/) (무료 모델만) | 영상 분석 · 심사 · 댓글 작성 |
| [OpenAI API](https://platform.openai.com/) | 영상 분석 · 심사 · 댓글 작성 |

키가 있는 서비스 하나만 있어도 동작합니다.

### MCP (Model Context Protocol)

앱 자체는 MCP를 사용하지 않습니다. 개발 과정에서 [Claude Code](https://claude.com/claude-code)의 MCP 도구를 썼습니다.

| MCP 서버 | 용도 |
|----------|------|
| Claude Browser (Claude Code 내장 브라우저) | 개발 서버 화면 확인·클릭 테스트 |

## 설치 및 실행

### 1. 사전 요구사항

- Python 3.12+
- Chrome 브라우저
- YouTube Data API Key ([Google Cloud Console](https://console.cloud.google.com/)에서 발급)
- AI API Key (Gemini / Claude / OpenRouter / OpenAI 중 하나 이상)

### 2. 설치

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. 설정 (`settings.yaml`)

모든 설정은 프로젝트 폴더의 `settings.yaml` 한 파일에 저장됩니다. API 키와 계정이 들어 있어
**git에 올라가지 않으며**(.gitignore), 코드에는 어떤 값도 하드코딩되어 있지 않습니다.

- 앱을 처음 실행하면 `settings.example.yaml`(견본)로 자동 생성됩니다.
- 앱 상단 **설정** 버튼에서 브랜드 이름·글자 수·하루 댓글 상한, YouTube API 키,
  AI 서비스와 키·모델을 바꿀 수 있습니다.

```yaml
profiles: [...]            # 앱에서 Google 로그인으로 연결한 계정 (최대 3개)
comment: { min_chars: 40, max_chars: 120, brand: 운명원 }
limits:  { daily_max_comments: 10, max_accounts: 3 }
api:
  youtube_api_key: ...
  ai_provider: gemini      # gemini | anthropic | openrouter | openai
  ai_keys:   { gemini: ..., anthropic: ..., openrouter: ..., openai: ... }
  ai_models: { gemini: ..., anthropic: ..., openrouter: ..., openai: ... }
```

### 4. 크롬 프로필 설정

1. 앱 상단의 프로필 버튼 → **Google 계정으로 로그인** 클릭
2. 새로 열린 Chrome 창에서 Google 계정에 로그인
3. 로그인 후 Chrome 창을 닫으면 계정이 자동으로 연결됩니다
4. 최대 3개 계정까지 연결 가능 (앱 전용 프로필은 `%LOCALAPPDATA%/MarketingAIAgent/chrome_profiles`에 저장)

### 5. 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 자동 접속

## 프로젝트 구조

```
├── app.py                    # Streamlit 메인 대시보드 (3단계 위저드)
├── styles.css                # 대시보드 스타일 (app.py가 불러옴)
├── ai_comment.py             # AI 댓글 생성 파이프라인 (분석→작성→심사→윤문)
├── browser_automation.py     # Playwright 크롬 자동화 (로그인·게시)
├── youtube_api.py            # YouTube Data API v3 연동
├── database.py               # SQLite 댓글 기록
├── config.py                 # settings.yaml 기반 설정 관리
├── dev_fixtures.py           # 개발용 테스트 픽스처
├── requirements.txt
├── settings.example.yaml     # 설정 견본 (API 키 제외)
├── vendor/
│   └── im_not_ai/            # im-not-ai 룰북 + 라이선스 (MIT)
└── data/
    └── comments.db           # SQLite DB (자동 생성)
```

## 운영 규칙

- 영상당 댓글 1개
- 하루 게시 상한: 10개 (설정 가능)
- 댓글 길이: 40~120자 (설정 가능)
- 금지: 링크, 해시태그, 거짓 후기

## 라이선스

이 프로젝트는 과제 제출용으로 제작되었습니다. 저작권은 지원자에게 있습니다.
