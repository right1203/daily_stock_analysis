# KR+US Stock AI Analysis

AI 기반 한국(KOSPI/KOSDAQ) 및 미국 주식 분석 자동화 프로젝트입니다.

## 핵심 기능

- 한국 및 미국 주식 일일 분석
- 시장 복기와 개별 종목 리포트 생성
- Web, Bot, API 기반 Agent 전략 대화
- 분석 기록 저장과 백테스트 점검
- Telegram, Discord, Email, Pushover, Custom Webhook, AstrBot 알림

## 지원 범위

- 주가 데이터: `pykrx`(한국), `yfinance`(미국)
- 뉴스 검색: Naver Search, Tavily, Brave Search, SerpAPI
- 기본 종목 예시: `005930`, `000660`, `035420`, `AAPL`, `TSLA`, `NVDA`

## 빠른 시작

### 1. 로컬 실행

```bash
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git
cd daily_stock_analysis
uv sync
cp .env.example .env
uv run python main.py
```

### 2. GitHub Actions 실행

1. 저장소를 Fork합니다.
2. `Settings -> Secrets and variables -> Actions`에서 환경 변수를 설정합니다.
3. `Actions` 탭에서 워크플로를 실행합니다.

필수 설정:

- LLM API Key: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` 등
- 분석 종목: `STOCK_LIST=005930,000660,035420,AAPL,TSLA,NVDA`
- 알림 채널: 지원 알림 중 최소 1개

권장 검색 설정:

- 한국 뉴스: `NAVER_API_KEYS` (`client_id:client_secret` 형식)
- 미국 뉴스: `TAVILY_API_KEYS`, `BRAVE_API_KEYS`, `SERPAPI_API_KEYS` 중 하나 이상

## 주요 설정 파일

- 환경 변수 예시: [.env.example](.env.example)
- LLM 설정 가이드: [docs/LLM_CONFIG_GUIDE.md](docs/LLM_CONFIG_GUIDE.md)
- 변경 기록: [docs/CHANGELOG.md](docs/CHANGELOG.md)

## 실행 예시

```bash
uv run python main.py
```

WebUI를 사용할 때는 `.env`에서 다음 값을 설정합니다.

```bash
WEBUI_ENABLED=true
WEBUI_HOST=127.0.0.1
WEBUI_PORT=8000
```

## 문서

- 전체 가이드: [docs/full-guide.md](docs/full-guide.md)
- FAQ: [docs/FAQ.md](docs/FAQ.md)
- 배포 가이드: [docs/DEPLOY.md](docs/DEPLOY.md)
