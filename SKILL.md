---
name: stock-analysis
description: "개별 종목, 여러 종목, 또는 시장 리뷰가 필요할 때 사용하는 주식 분석 스킬입니다."
---

# 주식 분석기

이 스킬은 `analyzer_service.py`의 분석 흐름을 기준으로 개별 종목, 종목 목록, 시장 리뷰를 실행하는 방법을 정리합니다.

## 출력 구조 (`AnalysisResult`)

분석 함수는 `AnalysisResult` 객체 또는 객체 목록을 반환합니다. 핵심 필드는 다음과 같습니다.

`dashboard` 속성은 네 가지 주요 영역으로 구성됩니다.

1. **`core_conclusion`**: 한 문장 요약, 신호 유형, 포지션 제안.
2. **`data_perspective`**: 추세, 가격 위치, 거래량, 수급 관련 데이터.
3. **`intelligence`**: 뉴스, 위험 알림, 긍정 촉매.
4. **`battle_plan`**: 매수 또는 매도 기준, 포지션 전략, 위험 관리 체크리스트.

## 설정 (`Config`)

모든 분석 함수는 선택적 `config` 객체를 받을 수 있습니다. 이 객체는 API 키, 알림 설정, 분석 파라미터 같은 앱 설정을 포함합니다.

`config`를 전달하지 않으면 `.env`에서 로드한 전역 설정 인스턴스를 사용합니다.

**참고:** [`Config`](src/config.py)

## 함수

### 1. 개별 종목 분석

**설명:** 개별 종목을 분석하고 결과를 반환합니다.

**사용 시점:** 사용자가 특정 종목 분석을 요청할 때 사용합니다.

**입력:**

- `stock_code` (str): 분석할 종목 코드.
- `config` (Config, optional): 설정 객체. 기본값은 `None`.
- `full_report` (bool, optional): 전체 리포트 생성 여부. 기본값은 `False`.
- `notifier` (NotificationService, optional): 알림 서비스 객체. 기본값은 `None`.

**출력:** `Optional[AnalysisResult]`

분석 성공 시 `AnalysisResult` 객체를 반환하고, 실패 시 `None`을 반환합니다.

**예시:**

```python
from analyzer_service import analyze_stock

result = analyze_stock("005930")
if result:
    print(f"종목: {result.name} ({result.code})")
    print(f"심리 점수: {result.sentiment_score}")
    print(f"투자 의견: {result.operation_advice}")
```

**참고:** [`analyze_stock`](./analyzer_service.py)

### 2. 여러 종목 분석

**설명:** 종목 코드 목록을 분석하고 결과 목록을 반환합니다.

**사용 시점:** 사용자가 여러 종목을 한번에 분석하려고 할 때 사용합니다.

**입력:**

- `stock_codes` (List[str]): 분석할 종목 코드 목록.
- `config` (Config, optional): 설정 객체. 기본값은 `None`.
- `full_report` (bool, optional): 각 종목의 전체 리포트 생성 여부. 기본값은 `False`.
- `notifier` (NotificationService, optional): 알림 서비스 객체. 기본값은 `None`.

**출력:** `List[AnalysisResult]`

`AnalysisResult` 객체 목록을 반환합니다.

**예시:**

```python
from analyzer_service import analyze_stocks

results = analyze_stocks(["005930", "AAPL", "SPY"])
for result in results:
    print(f"종목: {result.name}, 투자 의견: {result.operation_advice}")
```

**참고:** [`analyze_stocks`](./analyzer_service.py)

### 3. 시장 리뷰 실행

**설명:** 전체 시장을 리뷰하고 리포트를 반환합니다.

**사용 시점:** 사용자가 시장 개요, 요약, 또는 장 마감 리뷰를 요청할 때 사용합니다.

**입력:**

- `config` (Config, optional): 설정 객체. 기본값은 `None`.
- `notifier` (NotificationService, optional): 알림 서비스 객체. 기본값은 `None`.

**출력:** `Optional[str]`

시장 리뷰 리포트 문자열을 반환하고, 실패 시 `None`을 반환합니다.

**예시:**

```python
from analyzer_service import perform_market_review

report = perform_market_review()
if report:
    print(report)
```

**참고:** [`perform_market_review`](./analyzer_service.py)
