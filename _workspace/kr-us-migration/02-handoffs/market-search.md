# Market Search Handoff

## Status

- in progress on `codex/kr-us-market-cleanup`

## Owned Files

- `src/search_service.py`
- `src/market_analyzer.py`
- `src/agent/tools/market_tools.py`
- `src/agent/tools/data_tools.py`
- `data_provider/base.py`
- `data_provider/__init__.py`
- `data_provider/akshare_fetcher.py`
- `data_provider/efinance_fetcher.py`
- `data_provider/tushare_fetcher.py`
- `data_provider/baostock_fetcher.py`
- `data_provider/pytdx_fetcher.py`
- `data_provider/yfinance_fetcher.py` for removing China/HK conversion only

## Queued Work

- Replace `cn`/`hk` market defaults with KR+US-only behavior.
- Remove Bocha search from active routing and keep Naver for Korean market content.
- Preserve the existing global search path for US market content.
- Remove A-share/HK keyword templates and stock-code examples from agent tools.
- Remove Chinese fetchers from default fetcher lists and realtime source priority.
- Preserve `pykrx`, KRX trading calendar, `yfinance`, and US index mapping.

## Started Changes

- `src/agent/tools/market_tools.py`: changed `get_market_indices` schema and default region from `cn` to `kr`, with `kr/us` as the only exposed enum values.
- `src/agent/tools/data_tools.py`: replaced A-share/HK stock-code examples in agent-visible parameter descriptions with KR/US examples.
- `src/market_analyzer.py`: changed `MarketAnalyzer` default and invalid-region fallback from `cn` to `kr`.
- `src/config.py`: changed structured validation to treat Tavily/Brave/SerpAPI as active global search engines and to ignore China-only delivery channels when deciding whether notifications are configured.
- `data_provider/pykrx_fetcher.py`: made the optional pykrx import robust when transitive imports fail.
- `tests/test_agent_registry.py`: added schema regression tests for KR/US-only agent tool metadata.
- `tests/test_market_strategy.py`: added default/fallback region regression tests for `MarketAnalyzer`.
- `tests/test_config_validate_structured.py`, `tests/test_agent_executor.py`, and `tests/test_pipeline_realtime_indicators.py`: aligned expected strings and market examples with KR+US behavior.

## Remaining Risks

- `src/config.py` and `src/core/config_registry.py` contain market defaults and search config; coordinate those edits with `delivery-config-pruner`.
- Some Chinese providers may be import-compatible shims. Decide whether to delete files or detach them from active paths before implementation.
- `akshare_fetcher.py` is large and mixes A-share, HK, and some US fallback logic. Removal should be staged with tests.

## Suggested Verification

```bash
pytest tests/test_pykrx_fetcher.py tests/test_kr_index_mapping.py tests/test_yfinance_us_indices.py tests/test_search_news_freshness.py -v
```

Completed for started changes:

```bash
python3 -m pytest tests/test_agent_registry.py::TestBuiltinToolDefinitions -q
python3 -m pytest tests/test_market_strategy.py -q
uv run pytest tests/test_notification_sender.py tests/test_notification.py tests/test_config_validate_structured.py tests/test_agent_executor.py tests/test_pipeline_realtime_indicators.py tests/test_pykrx_fetcher.py tests/test_pipeline_notification_image_routing.py -q
uv run pytest
```
