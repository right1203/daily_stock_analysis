<div align="center">

# KR+US Stock AI Analysis

AI 기반 한국(KOSPI/KOSDAQ) + 미국 주식 분석 자동화 프로젝트입니다.

[**빠른 시작**](#빠른-시작) · [**핵심 기능**](#핵심-기능) · [**상세 가이드**](docs/full-guide.md) · [**영문 문서**](docs/README_EN.md) · [**FAQ**](docs/FAQ.md)

</div>

## 핵심 기능

- 한국 + 미국 시장 동시 분석
- 일일 자동 분석 및 시장 복기
- Agent 전략 대화(Web/Bot/API)
- 백테스트 기반 성능 점검
- 다중 채널 알림: Telegram, Discord, Email, Pushover, Custom Webhook

## 데이터 및 검색 정책

- 시세 데이터: `pykrx`(KR), `yfinance`(US)
- 뉴스 검색:
- 한국 시장: 네이버 검색 API
- 미국 시장: 글로벌 검색(Tavily, SerpAPI, Brave)
- 중국 시장/중국 전용 검색/중국 전용 데이터 공급자는 지원하지 않습니다.

## 빠른 시작

### 1) GitHub Actions (권장)

1. 저장소를 Fork합니다.
2. `Settings -> Secrets and variables -> Actions`에서 필수 값을 설정합니다.

필수 항목:
- LLM API Key(`GEMINI_API_KEY` 또는 `OPENAI_API_KEY` 등)
- `STOCK_LIST` (예: `005930,000660,AAPL,MSFT`)
- 알림 채널 최소 1개

권장 검색 키:
- 한국 검색: 네이버 검색 API 인증 정보
- 미국 검색: `TAVILY_API_KEYS` 또는 `BRAVE_API_KEYS` 또는 `SERPAPI_API_KEYS`

3. `Actions` 탭에서 워크플로를 실행합니다.

### 2) 로컬 실행

```bash
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git
cd daily_stock_analysis
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## 알림 채널

지원 채널:
- Telegram
- Discord(Webhook 또는 Bot)
- Email
- Pushover
- Custom Webhook

제거된 채널:
- WeChat
- Feishu
- DingTalk
- PushPlus
- ServerChan

## 시장 코드 예시

- 한국: `005930`, `000660`, `035420`
- 미국: `AAPL`, `TSLA`, `NVDA`

## 문서

- 한국어 상세 가이드: [docs/full-guide.md](docs/full-guide.md)
- 영문 상세 가이드: [docs/full-guide_EN.md](docs/full-guide_EN.md)
- 한국어 FAQ: [docs/FAQ.md](docs/FAQ.md)
- 영문 FAQ: [docs/FAQ_EN.md](docs/FAQ_EN.md)
- 배포 가이드: [docs/DEPLOY.md](docs/DEPLOY.md), [docs/DEPLOY_EN.md](docs/DEPLOY_EN.md)
