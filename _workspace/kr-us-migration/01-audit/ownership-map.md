# Ownership Map

## File Groups

### market-search-migrator

- Primary:
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
  - `data_provider/yfinance_fetcher.py` for China conversion removal only
  - `data_provider/pykrx_fetcher.py`, `data_provider/kr_index_mapping.py`, `data_provider/us_index_mapping.py` for preservation checks only
- Tests:
  - `tests/test_pykrx_fetcher.py`
  - `tests/test_kr_index_mapping.py`
  - `tests/test_kr_trading_calendar.py`
  - `tests/test_yfinance_us_indices.py`
  - `tests/test_search_news_freshness.py`
  - market/search portions of `tests/test_agent_pipeline.py`

### language-runtime-migrator

- Primary:
  - User-facing strings, prompts, logs, docstrings, and comments in active Python/TypeScript files
  - `src/analyzer.py`
  - `src/core/pipeline.py`
  - `src/services/`
  - `api/`
  - `bot/commands/`
  - `apps/dsa-web/src/pages/`
  - `apps/dsa-web/src/components/`
- Boundaries:
  - Do not change search provider routing owned by `market-search-migrator`.
  - Do not delete config keys or notification channels owned by `delivery-config-pruner`.
  - In files owned by another worker, only translate text after the primary owner finishes or after orchestrator assignment.

### delivery-config-pruner

- Primary:
  - `src/config.py`
  - `src/core/config_registry.py`
  - `src/notification.py`
  - `src/notification_sender/`
  - `src/feishu_doc.py`
  - `bot/platforms/`
  - `main.py` delivery startup sections
  - `README.md`
  - `docs/full-guide.md`
  - `docs/LLM_CONFIG_GUIDE.md`
  - `docs/DEPLOY.md`
  - `docs/FAQ.md`
  - `docs/architecture/api_spec.json`
  - `docs/bot-command.md`
  - `apps/dsa-web/src/utils/systemConfigI18n.ts`
  - settings UI labels tied to config keys
- Tests:
  - `tests/test_config_validate_structured.py`
  - `tests/test_system_config_service.py`
  - `tests/test_system_config_api.py`
  - `tests/test_notification.py`
  - `tests/test_notification_sender.py`
  - notification portions of `tests/test_pipeline_notification_image_routing.py`

## Conflicts

- `src/config.py`: market defaults and source priority affect `market-search-migrator`; config key removal is owned by `delivery-config-pruner`. The orchestrator should approve the exact split before code edits.
- `src/core/config_registry.py`: market region options affect `market-search-migrator`; delivery/search key visibility is owned by `delivery-config-pruner`.
- `src/search_service.py`: search routing is owned by `market-search-migrator`; Korean/English wording cleanup inside the same file should be reviewed by `language-runtime-migrator`.
- `apps/dsa-web/src/components/settings/*`: config-driven labels are owned by `delivery-config-pruner`; generic UI Chinese text is owned by `language-runtime-migrator`.
- `tests/test_agent_pipeline.py`: tests span agent tools, search, and fixture language. Split edits by assertion area.
