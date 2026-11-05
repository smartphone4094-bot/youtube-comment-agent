# 운명원 마케팅 AI 에이전트

유튜브 연애 영상에 맥락에 맞는 댓글을 자동으로 작성·게시하는 AI 에이전트 대시보드입니다.

## 핵심 기능

| 단계 | 기능 |
|------|------|
| 1. 영상 선택 | 키워드 검색 또는 URL 직접 입력으로 유튜브 영상 로드 (썸네일·제목·채널·날짜), 페이지네이션 |
| 2. 댓글 생성 | AI가 영상 자막·인기 댓글을 분석하여 시청자 페르소나 기반 댓글 초안 생성, 자동 심사·윤문 |
| 3. 댓글 게시 | 연결된 Google 계정으로 자동 게시, 프로필 랜덤 선택 |

## 기술 스택

### 프레임워크 & 런타임

| 기술 | 용도 | 라이선스 |
|------|------|----------|
| [Python](https://www.python.org/) 3.12+ | 런타임 | PSF License |
| [Streamlit](https://streamlit.io/) 1.40 | 웹 대시보드 UI | Apache 2.0 |

### AI / LLM

| 기술 | 용도 | 비고 |
|------|------|------|
| [Google Gemini API](https://ai.google.dev/) | 댓글 작성 (기본) | API 키 필요 |
| [Anthropic Claude API](https://docs.anthropic.com/) | 댓글 작성 (대체) | API 키 필요 |
| [OpenRouter](https://openrouter.ai/) | 댓글 작성 (대체) | API 키 필요 |
| [OpenAI API](https://platform.openai.com/) | 댓글 작성 (대체) | API 키 필요 |

댓글 생성 파이프라인: 영상 분석 → 후보 생성 (3개) → 자동 심사·윤문 → 길이 맞춤

### 브라우저 자동화

| 기술 | 용도 | 라이선스 |
|------|------|----------|
| [Playwright](https://playwright.dev/) 1.49 | Chrome 프로필 기반 자동 로그인·댓글 게시 | Apache 2.0 |

### 데이터 & API

| 기술 | 용도 | 라이선스 |
|------|------|----------|
| [YouTube Data API v3](https://developers.google.com/youtube/v3) | 영상 검색·상세 정보·인기 댓글 조회 | Google ToS |
| [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) 1.2 | 영상 자막 추출 | MIT |
| [SQLite](https://www.sqlite.org/) | 댓글 게시 기록 저장 | Public Domain |

### 설정 & 유틸리티

| 기술 | 용도 | 라이선스 |
|------|------|----------|
| [PyYAML](https://pyyaml.org/) 6.0 | `settings.yaml` 설정 파일 관리 | MIT |
| [python-dotenv](https://github.com/theskumar/python-dotenv) 1.0 | 환경 변수 로드 (레거시 호환) | BSD-3-Clause |
| [google-api-python-client](https://github.com/googleapis/google-api-python-client) 2.154 | YouTube Data API 클라이언트 | Apache 2.0 |

### 오픈소스 사용

| 패키지 | 출처 | 라이선스 | 용도 |
|--------|------|----------|------|
| im_not_ai (© 2026 epoko77-ai) | `vendor/im_not_ai/` | MIT | 댓글 윤문 단계에서 AI 말투 탐지 룰북(`quick-rules.md`) 참조 |

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
├── ai_comment.py             # AI 댓글 생성 파이프라인 (분석→작성→심사→윤문)
├── browser_automation.py     # Playwright 크롬 자동화 (로그인·게시)
├── youtube_api.py            # YouTube Data API v3 연동
├── database.py               # SQLite 댓글 기록
├── config.py                 # settings.yaml 기반 설정 관리
├── dev_fixtures.py           # 개발용 테스트 픽스처
├── requirements.txt
├── settings.example.yaml     # 설정 견본 (API 키 제외)
├── vendor/
│   └── im_not_ai/            # AI 텍스트 자연스러움 룰북 (MIT)
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
