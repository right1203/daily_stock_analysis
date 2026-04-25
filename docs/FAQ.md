# 자주 묻는 질문

## 어떤 시장을 지원하나요?

현재 문서는 한국 및 미국 주식 분석 기준입니다. 한국 종목은 `005930`, `000660`, `035420` 같은 숫자 코드를 사용하고,
미국 종목은 `AAPL`, `TSLA`, `NVDA`, `SPY` 같은 티커를 사용합니다. 지수 키워드는 `KOSPI`, `NASDAQ` 예시를 사용합니다.

## 데이터 공급자는 무엇인가요?

한국 시장 데이터는 `pykrx`, 미국 시장 데이터는 `yfinance`를 사용합니다. 한국 뉴스 검색은 Naver, 미국 및 글로벌 검색은
Tavily, Brave, SerpAPI 설정을 사용합니다.

## 알림 채널은 무엇을 지원하나요?

지원 채널은 Telegram, Discord, Email, Pushover, Custom Webhook, AstrBot입니다. 하나 이상을 `.env`에 설정해야 분석
결과를 받을 수 있습니다.

## 최소 설정 예시는 무엇인가요?

```env
STOCK_LIST=005930,AAPL,NVDA
TZ=Asia/Seoul
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Telegram 대신 Discord, Email, Pushover, Custom Webhook, AstrBot 중 하나를 설정해도 됩니다.

## 한국 종목 가격이 비어 있으면 어떻게 하나요?

1. 종목 코드가 여섯 자리인지 확인합니다.
2. 장 휴장일 또는 비거래 시간인지 확인합니다.
3. `pykrx` 관련 의존성이 설치되어 있는지 확인합니다.
4. 네트워크 제한이 있으면 재시도 간격을 늘립니다.

## 미국 종목 가격이 비어 있으면 어떻게 하나요?

1. 티커가 올바른지 확인합니다.
2. `yfinance`가 설치되어 있는지 확인합니다.
3. 일시적인 요청 제한일 수 있으므로 잠시 후 다시 실행합니다.
4. 프록시 또는 방화벽이 외부 요청을 막고 있는지 확인합니다.

## 뉴스 검색 결과가 부족한 이유는 무엇인가요?

검색 API 키가 없거나 요청 제한에 걸렸을 수 있습니다. 한국 뉴스는 `NAVER_API_KEYS`
(`client_id:client_secret` 형식), 글로벌 검색은 `TAVILY_API_KEYS`, `BRAVE_API_KEYS`,
`SERPAPI_API_KEYS` 중 사용 가능한 키를 설정합니다.

## 분석 결과가 너무 길면 어떻게 하나요?

알림 채널별 메시지 길이 제한이 다릅니다. 긴 결과는 Email 또는 Custom Webhook을 우선 사용하거나, 보고서 길이 관련
설정을 줄여 전송 실패를 줄입니다.

## Docker에서 시간대가 맞지 않으면 어떻게 하나요?

컨테이너 환경 변수에 `TZ=Asia/Seoul`을 설정합니다.

```yaml
environment:
  - TZ=Asia/Seoul
```

## 문제를 보고할 때 무엇을 포함해야 하나요?

- 실행 명령
- `.env`에서 민감 값을 제거한 관련 설정
- 종목 예시
- 오류 로그
- 기대 결과와 실제 결과
- 재현 가능한 최소 절차
