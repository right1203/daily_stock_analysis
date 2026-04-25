# Verification Checklist

## Static Scans

중국어 문자열 잔존 스캔:

```bash
rg -n "[\p{Han}]" src api bot data_provider apps/dsa-web/src tests docs README.md main.py analyzer_service.py webui.py server.py strategies --glob '!docs/CHANGELOG.md' --glob '!apps/dsa-web/package-lock.json' --glob '!sources/**'
```

중국 서비스 잔존 스캔:

```bash
rg -n "Tushare|Baostock|PyTDX|pytdx|Efinance|efinance|Bocha|bocha|Feishu|feishu|WeChat|wechat|DingTalk|dingtalk|PushPlus|pushplus|ServerChan|serverchan" src api bot data_provider apps/dsa-web/src tests docs README.md main.py analyzer_service.py webui.py server.py --glob '!docs/CHANGELOG.md' --glob '!apps/dsa-web/package-lock.json' --glob '!sources/**'
```

시장 분기 잔존 스캔:

```bash
rg -n "\\bcn\\b|\\bhk\\b|A-share|A-shares|A股|港股|沪|深|上证|创业板|科创|东方财富|雪球|博查" src api bot data_provider apps/dsa-web/src tests docs README.md main.py analyzer_service.py webui.py server.py --glob '!docs/CHANGELOG.md' --glob '!apps/dsa-web/package-lock.json' --glob '!sources/**'
```

KR+US 보존 확인:

```bash
rg -n "Naver|NAVER|naver|pykrx|KRX|KOSPI|KOSDAQ|yfinance|YFinance|Yahoo|US index|S&P 500|Nasdaq|Dow" src api bot data_provider apps/dsa-web/src tests docs README.md main.py analyzer_service.py webui.py server.py
```

## Syntax And Test Checks

핵심 문법 검증:

```bash
python3 -m py_compile main.py src/*.py data_provider/*.py
```

핵심 테스트 예시:

```bash
pytest tests/test_kr_stock_detection.py tests/test_kr_market_profile.py tests/test_search_news_freshness.py -v
```

설정/라우팅 검증 예시:

```bash
pytest tests/test_system_config_service.py tests/test_agent_executor.py -v
```

KR/US 데이터 경로 검증 예시:

```bash
pytest tests/test_pykrx_fetcher.py tests/test_kr_index_mapping.py tests/test_yfinance_us_indices.py tests/test_kr_trading_calendar.py -v
```

알림/설정 정리 검증 예시:

```bash
pytest tests/test_config_validate_structured.py tests/test_notification.py tests/test_notification_sender.py -v
```

## Latest Verification - 2026-04-26

Dependency sync:

```bash
uv sync --extra dev
```

Focused pytest suite:

```bash
uv run pytest tests/test_notification_sender.py tests/test_notification.py tests/test_config_validate_structured.py tests/test_agent_executor.py tests/test_pipeline_realtime_indicators.py tests/test_pykrx_fetcher.py tests/test_pipeline_notification_image_routing.py -q
```

Result:

```text
122 passed, 1 warning in 1.93s
```

Full pytest suite:

```bash
uv run pytest
```

Result:

```text
430 passed, 21 skipped, 39 warnings, 88 subtests passed in 23.68s
```

Warnings are currently from third-party `pykrx`/`pkg_resources`, Pydantic v2 deprecations, `lark_oapi` deprecations, and legacy `test_env.py` tests returning bool values.

## Harness Artifact Checks

하네스 파일 존재 확인:

```bash
find docs/plans .codex/harness _workspace/kr-us-migration -type f | sort
```

금지 잔재 확인:

```bash
rg -n "\\.cl[a]ude/|Team[C]reate|Send[M]essage|Task[C]reate|Task[U]pdate|general-purpos[e]|model: \"op[u]s\"" .codex/harness _workspace/kr-us-migration
```

## Interpretation Rules

- `docs/CHANGELOG.md` is archival and should not block migration unless current release notes are being edited.
- `apps/dsa-web/package-lock.json` can contain incidental `cn` or `hk` inside hashes and should not be treated as semantic evidence.
- Deprecated compatibility shims are allowed only if they are detached from active config, UI, docs, and runtime routing.
- Positive KR+US controls must remain present after cleanup.
