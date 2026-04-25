# 기여 가이드

이 저장소는 한국 및 미국 주식 분석 기준으로 유지합니다. 새 기능, 버그 수정, 문서 변경은 현재 지원 범위를 벗어나지
않도록 작성합니다.

## 개발 기준

- Python 3.10 이상을 기준으로 합니다.
- 기존 디렉터리 구조와 모듈 경계를 따릅니다.
- 설정은 `.env`와 `.env.example`을 기준으로 관리합니다.
- 새 주석은 영어로 작성합니다.
- 문서 본문은 한국어로 작성하되 명령어, 환경 변수, 코드 식별자는 영어를 유지합니다.

## 현재 지원 범위

- 한국 시장 데이터: `pykrx`
- 미국 시장 데이터: `yfinance`
- 한국 검색: Naver
- 글로벌 검색: Tavily, Brave, SerpAPI
- 알림: Telegram, Discord, Email, Pushover, Custom Webhook, AstrBot
- 예시 종목: `005930`, `000660`, `035420`, `AAPL`, `TSLA`, `NVDA`, `SPY`
- 예시 지수: `KOSPI`, `NASDAQ`

## 변경 전 점검

```bash
git status --short
rg -n "TODO|FIXME" .
```

작업 중 다른 사람이 수정한 파일을 되돌리지 않습니다. 요청받은 범위와 관련 없는 포맷 변경은 피합니다.

## 검증

핵심 코드 변경에는 최소한 문법 검증 또는 대응 테스트를 포함합니다.

```bash
./test.sh syntax
python -m py_compile main.py
flake8 main.py src/ --max-line-length=120
```

문서만 수정한 경우에는 관련 금지어 검색과 `git diff --check`를 수행합니다.

## PR 설명

PR 설명에는 다음 항목을 포함합니다.

- 배경과 문제
- 변경 범위
- 검증 명령과 결과
- 호환성 영향
- 롤백 방법
- 관련 이슈가 있으면 `Fixes #123` 또는 `Closes #123`

## 커밋

명시적 확인 없이 커밋하지 않습니다. 커밋 메시지는 영어로 작성하고 공동 작성자 문구는 추가하지 않습니다.
