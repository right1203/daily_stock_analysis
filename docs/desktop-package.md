# 데스크톱 패키지 가이드

이 문서는 데스크톱 패키징 작업에서 유지해야 할 현재 기준을 정리합니다. 앱의 분석 대상은 한국 및 미국 주식이며,
예시는 `005930`, `000660`, `035420`, `AAPL`, `TSLA`, `NVDA`, `SPY`, `KOSPI`, `NASDAQ`을 사용합니다.

## 패키징 전 확인

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --stocks 005930,AAPL
```

데스크톱 빌드에 포함되는 기본 설정은 `.env.example`과 동기화합니다. 민감한 키는 패키지에 포함하지 않습니다.

## 필수 런타임 설정

```env
STOCK_LIST=005930,AAPL,NVDA
TZ=Asia/Seoul
DISCORD_WEBHOOK_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

사용자는 Telegram, Discord, Email, Pushover, Custom Webhook, AstrBot 중 하나 이상을 설정해야 합니다.

## 데이터 공급자

- 한국 시장: `pykrx`
- 미국 시장: `yfinance`
- 한국 검색: Naver
- 글로벌 검색: Tavily, Brave, SerpAPI

패키지 설명, 화면 문구, 예시 설정은 위 범위만 언급합니다.

## 릴리스 전 점검

```bash
python -m py_compile main.py
git diff --check
```

문서와 앱 내 도움말이 동일한 종목 예시와 알림 채널을 안내하는지 확인합니다.
