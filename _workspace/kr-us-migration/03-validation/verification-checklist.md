# Verification Checklist

## Static Scans

Complete-removal provider/search/delivery product scan. This must return no active product or docs matches after cleanup.
Intentional negative tests and removed-field denylists are covered by `pytest tests/test_kr_us_static_residue.py -v`.
The pytest guard is authoritative for marker-aware checks inside `src/core/config_registry.py`.

```bash
rg -n -i "akshare|baostock|bocha|dingtalk|efinance|feishu|pushplus|pytdx|serverchan3|serverchan|tushare|wecom|wechat" src api bot data_provider apps/dsa-web/src apps/dsa-desktop docs README.md main.py server.py webui.py pyproject.toml requirements.txt .env.example SKILL.md docker --glob '!src/core/config_registry.py' --glob '!docs/CHANGELOG.md' --glob '!docs/plans/**' --glob '!docs/superpowers/**' --glob '!sources/**' --glob '!*.png' --glob '!*.jpg' --glob '!*.ico'
```

Complete-removal market token product scan. This must return no active product or docs matches after cleanup.
Intentional negative tests and unsupported-region assertions are covered by `pytest tests/test_kr_us_static_residue.py -v`.

```bash
rg -n "(?i:\bcn\b|\bhk\b|A-share|A-shares|HK stock|HK stocks|\bSH[0-9]{6}\b|\bSZ[0-9]{6}\b|\bHK[0-9]{5}\b)|A股|港股|上证|深证|创业板|科创|东方财富|沪|深|\.SH\b|\.SZ\b|\.SS\b|\.HK\b" src api bot data_provider apps/dsa-web/src apps/dsa-desktop docs README.md main.py server.py webui.py pyproject.toml requirements.txt .env.example SKILL.md docker --glob '!docs/CHANGELOG.md' --glob '!docs/plans/**' --glob '!docs/superpowers/**' --glob '!sources/**' --glob '!*.png' --glob '!*.jpg' --glob '!*.ico'
```

Compatibility-shim scan. Complete-removal mode should not keep no-op wrappers for removed providers or delivery channels:

```bash
rg -n "compatibility shim|deprecated.*Chinese|out of scope for the KR\+US|not supported in the KR\+US build|legacy alias|no-op" src api bot data_provider apps/dsa-web/src apps/dsa-desktop tests docs README.md main.py server.py webui.py --glob '!docs/CHANGELOG.md' --glob '!docs/plans/**' --glob '!docs/superpowers/**' --glob '!sources/**'
```

KR/US positive-control scan. This must keep expected matches for `pykrx`, KRX, KOSPI/KOSDAQ, Naver, `yfinance`, Yahoo, S&P 500, Nasdaq, Dow, and US index mapping:

```bash
rg -n "Naver|NAVER|naver|pykrx|KRX|KOSPI|KOSDAQ|yfinance|YFinance|Yahoo|US index|S&P 500|Nasdaq|Dow" src api bot data_provider apps/dsa-web/src tests docs README.md main.py server.py webui.py pyproject.toml requirements.txt --glob '!docs/CHANGELOG.md' --glob '!docs/plans/**' --glob '!docs/superpowers/**'
```

Global search provider preservation scan. Existing global providers must remain unless a match is China-specific:

```bash
rg -n "Tavily|tavily|Brave|brave|SerpAPI|serpapi|GoogleSearch" src api bot apps/dsa-web/src tests docs README.md main.py server.py webui.py pyproject.toml requirements.txt --glob '!docs/CHANGELOG.md' --glob '!docs/plans/**' --glob '!docs/superpowers/**'
```

Implementation-language scan for surviving active code. Any remaining Chinese text in code requires explicit review; user-facing text should be Korean:

```bash
rg -n "[\p{Han}]" src api bot data_provider apps/dsa-web/src tests main.py server.py webui.py pyproject.toml requirements.txt --glob '!*.png' --glob '!*.jpg' --glob '!*.ico'
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

KR/US 기준선 정적 회귀 가드:

```bash
pytest tests/test_kr_us_static_residue.py -v
```

## Latest Verification - 2026-04-26

Task 2 KR/US market option lock red/green evidence:

Red command:

```bash
python3 -m pytest tests/test_kr_trading_calendar.py tests/test_market_strategy.py tests/test_market_analyzer_generate_text.py tests/test_agent_registry.py -v
```

Red result summary:

```text
5 expected failures before implementation:
- A/H prompt text remained in market recap prompts.
- Legacy A-share examples remained in API schema examples.
- Frontend validation accepted SH600519 and 00700.
- Market indices handler routed cn into the data manager.
```

Green command:

```bash
python3 -m pytest tests/test_kr_trading_calendar.py tests/test_market_strategy.py tests/test_market_analyzer_generate_text.py tests/test_agent_registry.py -v
```

Green result:

```text
81 passed, 13 warnings
```

Syntax and diff checks:

```bash
python3 -m py_compile src/core/trading_calendar.py src/core/market_profile.py src/core/market_strategy.py src/market_analyzer.py src/agent/tools/market_tools.py src/agent/tools/data_tools.py api/v1/schemas/analysis.py api/v1/schemas/stocks.py
git diff --check
```

Result:

```text
py_compile passed using python3 -m py_compile.
git diff --check passed.
```

Deferred frontend verification:

```text
Frontend full build deferred because apps/dsa-web/node_modules is not installed.
Frontend validator behavior is covered by pytest executing validation.ts through Node.
```

Task 2 validator alignment follow-up:

```bash
python3 -m pytest tests/test_agent_registry.py::TestBuiltinToolDefinitions::test_frontend_stock_code_validation_is_kr_us_only -v
python3 -m pytest tests/test_kr_trading_calendar.py tests/test_market_strategy.py tests/test_market_analyzer_generate_text.py tests/test_agent_registry.py -v
PYTHONPYCACHEPREFIX=/tmp/dsa_pycache_batch python3 -m py_compile src/core/trading_calendar.py src/core/market_profile.py src/core/market_strategy.py src/market_analyzer.py src/agent/tools/market_tools.py src/agent/tools/data_tools.py api/v1/schemas/analysis.py api/v1/schemas/stocks.py
git diff --check
```

Result:

```text
frontend validator targeted test: 1 passed
focused Task 2 suite: 81 passed, 13 warnings
py_compile passed
git diff --check passed
```

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
- Deprecated compatibility shims are not allowed in complete-removal mode.
- Positive KR+US controls must remain present after cleanup.
- Complete-removal scans may mention migration harness files under `_workspace/kr-us-migration/`; those files are audit artifacts and are not part of the active product scan scope.
