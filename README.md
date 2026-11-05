# YouTube Comment Agent Dashboard

(주)제이지그룹 AI PM 선발 과제 - Track 2: 마케팅 AI 에이전트 개발

## 개요

유튜브 연애 관련 영상에 맥락에 맞는 댓글을 자동으로 작성·게시하는 대시보드입니다.
영상을 불러오고, 선택하면 AI가 영상 내용을 분석해 댓글 초안을 생성하고,
크롬 프로필을 통해 실제로 댓글을 게시합니다.

## 핵심 기능

| 패널 | 기능 |
|------|------|
| 1. 영상 불러오기 | 연애 키워드 기반 최신 유튜브 영상 목록 로드 (썸네일·제목·채널·날짜) |
| 2. 영상 선택 | 영상 선택 시 AI가 영상 속 고민 요약 + 댓글 초안 생성 |
| 3. 댓글 달기 | 크롬 프로필로 자동 타이핑·게시·확인 |

## 기술 스택

- **UI**: Python Streamlit (로컬 대시보드)
- **Browser Automation**: Playwright (launchPersistentContext)
- **AI**: Claude API (Anthropic)
- **YouTube Data**: YouTube Data API v3 + youtube-transcript-api
- **DB**: SQLite (기록 저장)

## 설치 및 실행

### 1. 사전 요구사항

- Python 3.12+
- Chrome 브라우저
- YouTube Data API Key ([Google Cloud Console](https://console.cloud.google.com/)에서 발급)
- Anthropic API Key ([Anthropic Console](https://console.anthropic.com/)에서 발급)

### 2. 설치

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. 설정 (`settings.yaml`)

모든 설정은 프로젝트 폴더의 `settings.yaml` 한 파일에 저장됩니다. API 키와 계정이 들어 있어
**git에 올라가지 않으며**(.gitignore), 코드에는 어떤 값도 하드코딩되어 있지 않습니다.

- 앱을 처음 실행하면 `settings.example.yaml`(견본)로 자동 생성됩니다.
  예전 `.env` · `data/profiles.json` 값이 있으면 그대로 옮겨집니다.
- 앱 상단 **설정** 버튼에서 브랜드 이름·글자 수·하루 댓글 상한, YouTube API 키,
  AI 서비스(OpenRouter · Gemini · Claude · OpenAI)와 키·모델을 바꿀 수 있습니다.
- 파일을 직접 고쳐도 다음 동작 때 바로 반영됩니다.

```yaml
profiles: [...]            # 앱에서 Google 로그인으로 연결한 계정 (최대 3개)
comment: { min_chars: 40, max_chars: 120, brand: 운명원 }
limits:  { daily_max_comments: 10, max_accounts: 3 }
api:
  youtube_api_key: ...
  ai_provider: openrouter   # openrouter | gemini | anthropic | openai
  ai_keys:   { openrouter: ..., gemini: ..., anthropic: ..., openai: ... }
  ai_models: { openrouter: ..., gemini: ..., anthropic: ..., openai: ... }
```

키 없이 **영상 불러오기**를 누르면 YouTube 키 입력 창이, AI 키 없이 영상을 **선택**하면
AI 키 입력 창이 열립니다.

### 4. 크롬 프로필 설정

1. 앱 상단의 프로필 버튼 → **Google 계정으로 로그인** 클릭
2. 새로 열린 Chrome 창에서 Google 계정에 로그인
3. 로그인 후 그 Chrome 창을 닫으면 계정이 자동으로 연결됩니다
4. 계정마다 반복 (앱 전용 Chrome 프로필은 `%LOCALAPPDATA%/MarketingAIAgent/chrome_profiles`에 저장)

> 연결한 계정은 `settings.yaml`의 `profiles`에 저장되며, 최대 3개까지 연결할 수 있습니다.

### 5. 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 자동 접속

## 프로젝트 구조

```
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── app.py                    # Streamlit 메인 대시보드
├── config.py                 # 환경 변수 로드
├── youtube_api.py            # YouTube Data API 연동
├── ai_comment.py             # Claude AI 댓글 생성
├── browser_automation.py     # Playwright 크롬 자동화
├── database.py               # SQLite 댓글 기록
├── docs/
│   ├── TASK_ANALYSIS.md      # 과제 분석 문서
│   └── DESIGN_INTENT.md      # 제작 의도
└── data/
    └── comments.db           # SQLite DB (자동 생성)
```

## 운영 규칙

- 영상당 댓글 1개
- 하루 게시 상한: 10개
- 댓글 길이: 40~120자
- 금지: 링크, 해시태그, 거짓 후기

## 라이선스

이 프로젝트는 과제 제출용으로 제작되었습니다. 저작권은 지원자에게 있습니다.
