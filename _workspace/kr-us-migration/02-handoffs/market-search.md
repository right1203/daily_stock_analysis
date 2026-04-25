# Market Search Handoff

## Status

- queued from baseline audit

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

## Remaining Risks

- `src/config.py` and `src/core/config_registry.py` contain market defaults and search config; coordinate those edits with `delivery-config-pruner`.
- Some Chinese providers may be import-compatible shims. Decide whether to delete files or detach them from active paths before implementation.
- `akshare_fetcher.py` is large and mixes A-share, HK, and some US fallback logic. Removal should be staged with tests.

## Suggested Verification

```bash
pytest tests/test_pykrx_fetcher.py tests/test_kr_index_mapping.py tests/test_yfinance_us_indices.py tests/test_search_news_freshness.py -v
```
