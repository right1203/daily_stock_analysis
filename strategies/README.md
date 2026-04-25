# 트레이딩 전략 디렉터리 / Trading Strategies

이 디렉터리는 자연어 전략 파일을 YAML 형식으로 보관합니다. 시스템 시작 시 이 디렉터리의 모든 `.yaml` 파일을 자동으로 로드합니다.

## 사용자 전략 작성 방법

`.yaml` 파일을 만들고 원하는 자연어로 트레이딩 전략을 작성하면 됩니다. 별도 코드 작성은 필요하지 않습니다.

### 최소 템플릿

```yaml
name: my_strategy
display_name: 나의 전략
description: 전략 목적을 짧게 설명

instructions: |
  전략 설명을 작성합니다.
  판단 기준, 진입 조건, 종료 조건을 자연어로 적습니다.
  get_daily_history, analyze_trend 같은 도구 이름을 언급해 AI가 사용할 데이터를 안내할 수 있습니다.
```

### 전체 템플릿

```yaml
name: my_strategy
display_name: 나의 전략
description: 전략이 잘 맞는 시장 상황을 짧게 설명

# Strategy category: trend, pattern, reversal, framework.
category: trend

# Related core rule IDs, optional.
core_rules: [1, 2, 3]

# Tools required by the strategy, optional.
required_tools:
  - get_daily_history
  - analyze_trend
  - get_realtime_quote

# Detailed strategy instructions in natural language with Markdown support.
instructions: |
  **나의 전략 이름**

  판단 기준:

  1. **조건 1**:
     - `analyze_trend`로 이동평균 배열을 확인합니다.
     - 기대하는 추세 특성을 설명합니다.

  2. **조건 2**:
     - 거래량 조건을 설명합니다.

  점수 조정:
  - 조건 충족 시 권장하는 sentiment_score 조정값
  - `buy_reason`에 전략 이름을 남깁니다.
```

### 핵심 트레이딩 원칙 참고

| ID | 원칙 |
| --- | --- |
| 1 | 엄격한 진입: 이격률이 5% 미만일 때만 진입 검토 |
| 2 | 추세 추종: MA5 > MA10 > MA20 상승 배열 선호 |
| 3 | 효율 우선: 거래량으로 추세 유효성 확인 |
| 4 | 매수 선호 지점: 이동평균 지지선 되돌림 우선 |
| 5 | 위험 점검: 부정 뉴스는 우선 배제 |
| 6 | 가격과 거래량 확인: 가격 움직임을 거래량으로 검증 |
| 7 | 강한 추세 종목: 주도 종목은 기준을 일부 완화 가능 |

## 사용자 전략 디렉터리

내장 전략 디렉터리 외에 환경 변수로 추가 전략 디렉터리를 지정할 수 있습니다.

```bash
CUSTOM_STRATEGY_DIRS=/path/to/my/strategies,/path/to/team/strategies
```

시스템은 내장 전략과 사용자 전략을 함께 로드합니다. 이름이 충돌하면 사용자 전략이 내장 전략을 덮어씁니다.
