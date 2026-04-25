# 전체 사용 가이드

이 문서는 한국 및 미국 주식 분석 기준의 현재 설정과 운영 방법을 정리합니다. 예시는 한국 종목 `005930`,
`000660`, `035420`과 미국 종목 `AAPL`, `TSLA`, `NVDA`, `SPY`, 지수 `KOSPI`, `NASDAQ`을 사용합니다.

## 지원 범위

- 한국 시장 데이터: `pykrx`
- 미국 시장 데이터: `yfinance`
- 한국 뉴스 검색: Naver
- 미국 및 글로벌 뉴스 검색: Tavily, Brave, SerpAPI
- 알림 채널: Telegram, Discord, Email, Pushover, Custom Webhook, AstrBot
- 기본 시간대 예시: `Asia/Seoul`

## 빠른 시작

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --stocks 005930,AAPL,NVDA
```

`.env`에는 최소 한 개의 종목과 최소 한 개의 알림 채널을 설정합니다.

```env
STOCK_LIST=005930,000660,AAPL,TSLA,NVDA,SPY
TZ=Asia/Seoul

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DISCORD_WEBHOOK_URL=

EMAIL_SENDER=
EMAIL_PASSWORD=
EMAIL_RECEIVERS=

PUSHOVER_USER_KEY=
PUSHOVER_API_TOKEN=

CUSTOM_WEBHOOK_URLS=
ASTRBOT_URL=
```

## 주요 환경 변수

| 변수 | 설명 | 필수 |
| --- | --- | --- |
| `STOCK_LIST` | 분석할 종목 또는 지수 목록 | 예 |
| `TZ` | 스케줄 기준 시간대 | 권장 |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Telegram 알림 | 선택 |
| `DISCORD_WEBHOOK_URL` | Discord 알림 | 선택 |
| `EMAIL_SENDER` / `EMAIL_PASSWORD` / `EMAIL_RECEIVERS` | Email 알림 | 선택 |
| `PUSHOVER_USER_KEY` / `PUSHOVER_API_TOKEN` | Pushover 알림 | 선택 |
| `CUSTOM_WEBHOOK_URLS` | 쉼표로 구분한 Webhook URL | 선택 |
| `ASTRBOT_URL` / `ASTRBOT_TOKEN` | AstrBot 알림 | 선택 |
| `NAVER_API_KEYS` | 한국 뉴스 검색. `client_id:client_secret` 형식 | 선택 |
| `TAVILY_API_KEYS` | 글로벌 뉴스 검색 | 선택 |
| `BRAVE_API_KEYS` | 글로벌 뉴스 검색 | 선택 |
| `SERPAPI_API_KEYS` | 글로벌 뉴스 검색 | 선택 |
| `OPENAI_API_KEY` | OpenAI 호환 모델 사용 시 | 선택 |
| `GEMINI_API_KEY` | Gemini 모델 사용 시 | 선택 |

알림 채널은 하나 이상 설정해야 합니다. 검색 키가 없으면 가격 및 기본 분석 중심으로 동작하며, 뉴스 요약 품질은 낮아질 수 있습니다.

## 종목 코드 예시

| 대상 | 예시 |
| --- | --- |
| 한국 주식 | `005930`, `000660`, `035420` |
| 미국 주식 | `AAPL`, `TSLA`, `NVDA`, `SPY` |
| 지수 키워드 | `KOSPI`, `NASDAQ` |

```bash
python main.py --stocks 005930,000660,035420
python main.py --stocks AAPL,TSLA,NVDA,SPY
python main.py --stocks 005930,AAPL,NASDAQ
```

## 데이터 및 검색 흐름

1. 종목 코드 형식으로 한국 또는 미국 시장을 판정합니다.
2. 한국 시장은 `pykrx`, 미국 시장은 `yfinance`에서 가격과 시세 데이터를 가져옵니다.
3. 한국 관련 검색은 Naver를 우선 사용합니다.
4. 미국 및 글로벌 검색은 Tavily, Brave, SerpAPI 설정을 사용합니다.
5. 분석 결과는 설정된 알림 채널로 전송합니다.

## 알림 채널

### Telegram

```env
TELEGRAM_BOT_TOKEN=123456:token
TELEGRAM_CHAT_ID=123456789
```

### Discord

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/example
```

### Email

```env
EMAIL_SENDER=sender@example.com
EMAIL_PASSWORD=app-password
EMAIL_RECEIVERS=receiver@example.com
```

### Pushover

```env
PUSHOVER_USER_KEY=user-key
PUSHOVER_API_TOKEN=app-token
```

### Custom Webhook

```env
CUSTOM_WEBHOOK_URLS=https://example.com/webhook/one,https://example.com/webhook/two
```

### AstrBot

```env
ASTRBOT_URL=https://example.com/astrbot
ASTRBOT_TOKEN=
```

## 실행 모드

```bash
# 전체 기본 실행
python main.py

# 종목을 직접 지정
python main.py --stocks 005930,AAPL,NVDA

# WebUI 실행
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Docker 예시

```bash
docker build -f docker/Dockerfile -t daily-stock-analysis .
docker compose -f docker/docker-compose.yml up -d --build server
```

## API 예시

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "005930"}'

curl -X POST http://127.0.0.1:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "AAPL"}'
```

## 운영 점검

```bash
./test.sh syntax
python -m py_compile main.py
flake8 main.py src/ --max-line-length=120
```

## 문서 동기화

사용자에게 보이는 기능, 설정, 배포 방법이 바뀌면 `README.md`, `docs/CHANGELOG.md`, 관련 사용 문서를 함께 갱신합니다.
새 버전 항목을 추가할 때는 `[Unreleased]` 아래 내용을 새 버전 섹션으로 이동하고, 검증 명령과 영향 범위를 남깁니다.
