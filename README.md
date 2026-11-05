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
| [Playwright for Python](https://github.com/microsoft/playwright-python) | 1.64.1 | Apache 2.0 | Chrome 자동화 (Google 로그인 · 댓글 게시) |
| [PyInstaller](https://github.com/pyinstaller/pyinstaller) | 6.22.3 | GPL 2.0 (bootloader 예외 조항) | 실행 파일 빌드 (빌드할 때만 사용) |
| [google-api-python-client](https://github.com/googleapis/google-api-python-client) | 2.154.0 | Apache 2.0 | YouTube Data API 호출 |
| [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) | 1.2.4 | MIT | 영상 자막 가져오기 |
| [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) | 0.39.0 | MIT | Claude API 호출 |
| [PyYAML](https://github.com/yaml/pyyaml) | 6.0.2 | MIT | `settings.yaml` 읽기·쓰기 |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.0.1 | BSD-3-Clause | 예전 `.env` 설정을 `settings.yaml`로 옮길 때 사용 |
| [SQLite](https://www.sqlite.org/) | Python 내장 | Public Domain | 게시 기록 저장 |
| [im-not-ai](https://github.com/epoko77-ai/im-not-ai) (© 2026 epoko77-ai) | `vendor/im_not_ai/` 에 포함 | MIT | 댓글 심사·윤문 단계의 AI 말투 탐지 룰북(`quick-rules.md`)과 변경률 기준 |

im-not-ai는 원본 라이선스 전문을 [vendor/im_not_ai/LICENSE](vendor/im_not_ai/LICENSE)에 함께 두었습니다.

실행 파일에는 위 패키지가 쓰는 하위 오픈소스(Streamlit이 쓰는 pandas · numpy · pyarrow · altair · tornado, Playwright 드라이버에 포함된 Node.js 등)도 함께 들어갑니다. PyInstaller의 bootloader 예외 조항에 따라 PyInstaller로 만든 실행 파일에는 GPL이 적용되지 않습니다.

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

## 실행 방법 (PC 프로그램)

Python 설치도, 프로그램 설치도 필요 없습니다. 필요한 패키지는 모두 프로그램 폴더 안에 들어 있습니다.

**필요한 것**
- Windows 10 이상 + Chrome 브라우저 (계정 로그인과 댓글 게시에 사용)
- YouTube Data API 키 ([Google Cloud Console](https://console.cloud.google.com/)에서 발급)
- AI API 키 (Gemini / Claude / OpenRouter / OpenAI 중 하나 이상)

**다운로드**: [Releases](https://github.com/smartphone4094-bot/youtube-comment-agent/releases/latest)에서 `MarketingAI.zip`

**쓰는 법**
1. `MarketingAI.zip`을 원하는 곳에 풀기 (바탕화면, USB, 한글 폴더 모두 가능)
2. `MarketingAI\MarketingAI.exe` 더블클릭
3. 검은 콘솔 창과 함께 프로그램 창(Chrome 앱 창)이 열림
4. 상단 **설정**에서 YouTube 키와 AI 키 입력, 프로필 버튼에서 Google 계정 연결
5. 끝낼 때는 프로그램 창을 닫으면 콘솔도 함께 종료

처음 실행할 때 Windows가 "PC 보호" 경고를 띄우면 **추가 정보 → 실행**을 누르세요. 코드 서명이 없는 프로그램이라 나오는 경고입니다.

**자동으로 생기는 파일** (모두 `MarketingAI.exe`와 같은 폴더)

```
MarketingAI\
├── MarketingAI.exe
├── _internal\              # 프로그램 본체 (Python과 패키지 포함, 건드리지 말 것)
├── settings.yaml           # 설정 (API 키·계정 포함, 처음 실행 시 생성)
└── data\
    ├── comments.db         # 게시 기록
    ├── error.log           # 오류 로그
    ├── activity.log        # 활동 로그
    ├── chrome_profiles\    # 연결한 Google 계정의 Chrome 프로필
    └── app_window\         # 프로그램 창용 Chrome 프로필
```

폴더를 통째로 옮기면 설정과 연결한 계정도 그대로 따라갑니다. 다른 사람에게 줄 때는 `settings.yaml`과 `data\`를 빼고 주세요(API 키와 로그인 정보가 들어 있습니다).

## 실행 파일 만들기 (개발자용)

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

- `.venv-build` 가상환경을 새로 만들어 `requirements-build.txt`(앱 패키지 + PyInstaller)만 설치하고 빌드하므로, 앱이 쓰지 않는 패키지는 들어가지 않습니다.
- 결과물: `dist\MarketingAI\MarketingAI.exe`와 전달용 `dist\MarketingAI.zip`
- 빌드 설정은 `MarketingAI.spec`, 프로그램 시작 코드는 `launcher.py`

## 소스에서 실행 (개발자용)

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 `http://localhost:8501`이 열립니다. 이때 설정·기록 파일은 프로젝트 폴더에 생깁니다.

## 설정 (`settings.yaml`)

모든 설정은 `settings.yaml` 한 파일에 저장됩니다. API 키와 계정이 들어 있어
**git에 올라가지 않으며**(.gitignore), 코드에는 어떤 값도 하드코딩되어 있지 않습니다.

- 처음 실행하면 `settings.example.yaml`(견본)로 자동 생성됩니다.
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

## Google 계정 연결

1. 상단의 프로필 버튼 → **Google 계정으로 로그인** 클릭
2. 새로 열린 Chrome 창에서 Google 계정에 로그인
3. 로그인 후 Chrome 창을 닫으면 계정이 자동으로 연결됩니다
4. 최대 3개 계정까지 연결 가능. 게시할 때는 연결된 계정 중 하나가 무작위로 쓰입니다
   (프로필 저장 위치: 실행 파일은 `data\chrome_profiles`, 소스 실행은 `%LOCALAPPDATA%/MarketingAIAgent/chrome_profiles`)

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
├── launcher.py               # 실행 파일 시작 코드 (서버 실행 + 프로그램 창 열기)
├── MarketingAI.spec          # PyInstaller 빌드 설정
├── build.ps1                 # 실행 파일 빌드 스크립트
├── requirements.txt
├── requirements-build.txt    # 빌드용 (requirements.txt + PyInstaller)
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
