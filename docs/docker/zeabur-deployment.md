# Zeabur 배포 가이드

이 문서는 Zeabur에서 한국 및 미국 주식 분석 서비스를 배포하는 절차를 정리합니다.

## 준비 사항

- Git 저장소 연결 권한
- `.env`에 사용할 환경 변수
- 최소 하나의 알림 채널
- 분석 종목 예시: `005930`, `000660`, `035420`, `AAPL`, `TSLA`, `NVDA`, `SPY`
- 지수 예시: `KOSPI`, `NASDAQ`

## 서비스 생성

1. Zeabur 프로젝트를 생성합니다.
2. Git 저장소를 연결합니다.
3. Dockerfile 기반 서비스를 선택합니다.
4. 환경 변수를 등록합니다.
5. 배포 후 로그에서 첫 실행 결과를 확인합니다.

## 환경 변수 예시

```env
STOCK_LIST=005930,AAPL,NVDA,SPY
TZ=Asia/Seoul

DISCORD_WEBHOOK_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

EMAIL_SENDER=
EMAIL_PASSWORD=
EMAIL_RECEIVERS=

PUSHOVER_USER_KEY=
PUSHOVER_API_TOKEN=
CUSTOM_WEBHOOK_URLS=
ASTRBOT_URL=
ASTRBOT_TOKEN=

NAVER_API_KEYS=
TAVILY_API_KEYS=
BRAVE_API_KEYS=
SERPAPI_API_KEYS=
```

## 데이터 및 검색

한국 시장 데이터는 `pykrx`, 미국 시장 데이터는 `yfinance`를 사용합니다. 한국 검색은 Naver, 글로벌 검색은 Tavily,
Brave, SerpAPI 설정을 사용합니다.

## WebUI 포트

WebUI를 사용할 경우 서비스 포트를 `8000`으로 노출합니다.

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

## 배포 후 점검

```bash
python main.py --stocks 005930,AAPL
curl http://127.0.0.1:8000/api/health
```

Zeabur 로그에서 알림 전송 성공 여부와 데이터 조회 오류를 확인합니다.

## 롤백

문제가 발생하면 이전 배포로 되돌리고 최근 변경된 환경 변수를 확인합니다. 알림 키와 검색 API 키는 재배포 전에 다시
검증합니다.
