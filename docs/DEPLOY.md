# 배포 가이드

이 문서는 한국 및 미국 주식 분석 기준의 서버 배포 절차를 정리합니다. 예시는 `005930`, `000660`, `035420`,
`AAPL`, `TSLA`, `NVDA`, `SPY`, `KOSPI`, `NASDAQ`을 사용합니다.

## 사전 준비

- Python 3.10 이상
- Git
- `.env` 설정 파일
- 최소 하나의 알림 채널
- 서버 시간대: `Asia/Seoul` 권장

## 기본 서버 배포

```bash
git clone <repo-url>
cd daily_stock_analysis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` 예시:

```env
STOCK_LIST=005930,AAPL,NVDA,SPY
TZ=Asia/Seoul
DISCORD_WEBHOOK_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
EMAIL_SENDER=
EMAIL_PASSWORD=
EMAIL_RECEIVERS=
```

실행:

```bash
python main.py
```

## WebUI 실행

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

방화벽 또는 보안 그룹에서 `8000` 포트를 열어야 외부 접속이 가능합니다.

## systemd 예시

```ini
[Unit]
Description=Daily Stock Analysis
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/daily_stock_analysis
EnvironmentFile=/opt/daily_stock_analysis/.env
ExecStart=/opt/daily_stock_analysis/.venv/bin/python main.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable daily-stock-analysis
sudo systemctl start daily-stock-analysis
sudo systemctl status daily-stock-analysis
```

## Docker 배포

```bash
docker build -f docker/Dockerfile -t daily-stock-analysis .
docker run --env-file .env -e TZ=Asia/Seoul daily-stock-analysis
```

WebUI를 함께 노출할 때:

```bash
docker run --env-file .env -e TZ=Asia/Seoul -p 8000:8000 daily-stock-analysis \
  uv run python main.py --serve-only --host 0.0.0.0 --port 8000
```

## Docker Compose 예시

저장소의 Compose 파일은 `docker/docker-compose.yml`에 있습니다.

```bash
docker compose -f docker/docker-compose.yml up -d --build server
docker compose -f docker/docker-compose.yml logs -f server
```

## 알림 설정

지원 채널은 Telegram, Discord, Email, Pushover, Custom Webhook, AstrBot입니다. 배포 전에 하나 이상을 설정하고 테스트
실행으로 메시지가 도착하는지 확인합니다.

```env
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
ASTRBOT_TOKEN=
```

## 데이터 및 검색 설정

```env
NAVER_API_KEYS=
TAVILY_API_KEYS=
BRAVE_API_KEYS=
SERPAPI_API_KEYS=
```

한국 시장은 `pykrx`, 미국 시장은 `yfinance`를 사용합니다. 검색 키가 없으면 뉴스 요약 범위가 제한될 수 있습니다.

## 배포 후 점검

```bash
python main.py --stocks 005930,AAPL
curl http://127.0.0.1:8000/api/health
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs --tail=100 server
```

## 롤백

문제가 발생하면 이전 이미지 또는 이전 Git ref로 되돌리고 서비스를 재시작합니다. `.env` 변경이 원인일 수 있으므로 배포
전 설정 파일 백업을 남깁니다.
