# Ownership Map

## Mode

- Migration mode: complete removal.
- China/HK market, data, search, delivery, config, UI, docs, and test surfaces are removed, not hidden behind compatibility shims.
- Code identifiers, comments, and docstrings are English in implementation tasks.
- User-facing strings are Korean by default, with English allowed only for proper nouns such as API names and ticker/index names.

## File Groups

### market-data-removal

- Primary:
  - `src/market_analyzer.py`
  - `src/agent/tools/market_tools.py`
  - `src/agent/tools/data_tools.py`
  - `data_provider/base.py`
  - `data_provider/__init__.py`
  - `data_provider/realtime_types.py`
  - `data_provider/akshare_fetcher.py`
  - `data_provider/efinance_fetcher.py`
  - `data_provider/tushare_fetcher.py`
  - `data_provider/baostock_fetcher.py`
  - `data_provider/pytdx_fetcher.py`
  - `data_provider/yfinance_fetcher.py` for China conversion removal only
  - `data_provider/pykrx_fetcher.py`, `data_provider/kr_index_mapping.py`, `data_provider/us_index_mapping.py` for preservation checks only
  - `pyproject.toml`, `requirements.txt` for China data provider dependency removal only
- Tests:
  - Delete or rewrite provider-specific China tests:
    - `tests/test_akshare_realtime_logging.py`
    - China provider portions of `tests/test_fetcher_logging.py`
    - China market portions of `tests/test_stock_code_bse.py`
  - `tests/test_pykrx_fetcher.py`
  - `tests/test_kr_index_mapping.py`
  - `tests/test_kr_trading_calendar.py`
  - `tests/test_yfinance_us_indices.py`
  - `tests/test_us_index_mapping.py`
  - market portions of `tests/test_market_strategy.py`

### search-routing-removal

- Primary:
  - `src/search_service.py`
  - `src/agent/tools/search_tools.py`
  - search initialization in `main.py`
  - search status in `bot/commands/status.py`
- Removal:
  - Delete `BochaSearchProvider` and all `bocha_keys` wiring.
  - Remove `BOCHA_API_KEYS` from active config, docs, API schemas, and UI labels.
  - Remove China-specific search defaults or Baidu/China assumptions.
- Preservation:
  - Keep Naver for KR search.
  - Keep existing global search providers such as Tavily, Brave, and SerpAPI unless a specific branch is China-only.
- Tests:
  - `tests/test_search_news_freshness.py`
  - market/search portions of `tests/test_agent_pipeline.py`
  - search/provider registry portions of `tests/test_agent_registry.py`

### language-runtime-migrator

- Primary:
  - User-facing strings, prompts, logs, docstrings, and comments in active Python/TypeScript files after deleted surfaces are removed
  - `src/analyzer.py`
  - `src/core/pipeline.py`
  - `src/services/`
  - `api/`
  - `bot/commands/`
  - `bot/models.py`, `bot/handler.py`, `bot/dispatcher.py` for surviving text after removed platform paths are deleted
  - `apps/dsa-web/src/pages/`
  - `apps/dsa-web/src/components/`
  - `apps/dsa-web/src/index.css` for surviving comments and user-visible CSS text after config cleanup
- Boundaries:
  - Do not change data provider removal owned by `market-data-removal`.
  - Do not change search provider routing owned by `search-routing-removal`.
  - Do not delete config keys or notification channels owned by `delivery-config-pruner`.
  - Do not spend effort translating code or docs that complete-removal owners will delete.
  - In shared files, translate surviving implementation comments/docstrings to English and surviving user-facing copy to Korean.

### delivery-config-pruner

- Primary:
  - `src/config.py`
  - `src/core/config_registry.py`
  - `src/notification.py`
  - `src/notification_sender/`
  - `src/feishu_doc.py`
  - `src/formatters.py` for removed delivery-specific formatting helpers such as Feishu markdown conversion
  - `bot/platforms/`
  - `bot/models.py`, `bot/handler.py`, `bot/dispatcher.py` for removed delivery platform enums, webhook handlers, and dispatch routing
  - `main.py` delivery startup sections
  - `pyproject.toml`, `requirements.txt` for delivery dependency removal, including `dingtalk-stream`
  - Config/API/UI/doc references directly tied to removed config keys during code cleanup:
    - `README.md`
    - `docs/full-guide.md`
    - `docs/LLM_CONFIG_GUIDE.md`
    - `docs/DEPLOY.md`
    - `docs/FAQ.md`
    - `docs/architecture/api_spec.json`
    - `docs/bot-command.md`
  - `apps/dsa-web/src/utils/systemConfigI18n.ts`
  - settings UI labels tied to config keys
- Removal:
  - Remove WeChat, Feishu, DingTalk, PushPlus, and ServerChan runtime paths.
  - Remove deleted delivery env vars from config parsing, validation, registry, API schemas, docs, and UI.
  - Remove no-op or compatibility sender shims instead of keeping them.
  - Preserve non-China delivery channels such as Telegram, email, Discord, Pushover, AstrBot, and generic custom webhook behavior unless tied to DingTalk-specific handling.
- Tests:
  - `tests/test_config_validate_structured.py`
  - `tests/test_system_config_service.py`
  - `tests/test_system_config_api.py`
  - `tests/test_notification.py`
  - `tests/test_notification_sender.py`
  - notification portions of `tests/test_pipeline_notification_image_routing.py`
  - delete or rewrite `tests/test_feishu_stream.py`

### docs-sync-owner

- Primary:
  - `README.md`
  - `docs/full-guide.md`
  - `docs/full-guide_EN.md`
  - `docs/FAQ.md`
  - `docs/FAQ_EN.md`
  - `docs/DEPLOY.md`
  - `docs/DEPLOY_EN.md`
  - `docs/bot-command.md`
  - `docs/architecture/api_spec.json`
  - `docs/docker/zeabur-deployment.md`
  - bot integration docs under `docs/bot/`
- Removal:
  - Remove China/HK stock formats, Chinese data providers, Bocha, and China delivery channel instructions.
  - Delete docs that exist only for removed integrations, such as Feishu and DingTalk bot setup docs.
  - Keep KR/US setup, Naver search, yfinance, pykrx, and global search provider docs synchronized.
- Sequencing:
  - Run after implementation surfaces settle and after `delivery-config-pruner` removes references directly tied to deleted config keys.
  - Own the final broad documentation rewrite, narrative consistency, examples, screenshots, and release-facing usage text.
  - Do not concurrently rewrite config-key references while `delivery-config-pruner` is actively removing those keys; coordinate by file or wait for the config cleanup diff.

## Deleted-File Candidates

- `data_provider/akshare_fetcher.py`
- `data_provider/efinance_fetcher.py`
- `data_provider/tushare_fetcher.py`
- `data_provider/baostock_fetcher.py`
- `data_provider/pytdx_fetcher.py`
- `src/notification_sender/feishu_sender.py`
- `src/notification_sender/wechat_sender.py`
- `src/notification_sender/pushplus_sender.py`
- `src/notification_sender/serverchan3_sender.py`
- `bot/platforms/feishu_stream.py`
- `bot/platforms/dingtalk.py`
- `bot/platforms/dingtalk_stream.py`
- `src/feishu_doc.py`
- `docs/bot/feishu-bot-config.md`
- `docs/bot/dingding-bot-config.md`
- `tests/test_akshare_realtime_logging.py`
- `tests/test_feishu_stream.py`

## Conflicts

- Removal wins over translation: if a surface is deleted, do not translate or preserve it as a shim first.
- Positive controls are protected: `pykrx`, KRX calendar, KR index mapping, Naver, `yfinance`, US index mapping, and global search providers require explicit preservation checks after nearby removals.
- `src/config.py`: market defaults and source priority affect `market-data-removal`; config key removal is owned by `delivery-config-pruner`; search key removal is owned by `search-routing-removal`.
- `src/core/config_registry.py`: market region options affect `market-data-removal`; delivery/search key visibility is owned by `delivery-config-pruner` and `search-routing-removal`.
- `src/search_service.py`: Bocha removal is owned by `search-routing-removal`; surviving wording cleanup inside the same file is owned by `language-runtime-migrator`.
- `data_provider/yfinance_fetcher.py`: China/HK conversion removal is owned by `market-data-removal`; US index behavior must remain intact.
- `pyproject.toml`, `requirements.txt`: China data provider dependency removal is owned by `market-data-removal`; delivery dependency removal such as `dingtalk-stream` is owned by `delivery-config-pruner`.
- Docs/API surfaces: `delivery-config-pruner` owns config/API/UI/doc references directly tied to removed config keys during code cleanup; `docs-sync-owner` owns final broad documentation rewrite after implementation surfaces settle.
- `src/formatters.py`: delivery-specific helpers for removed channels are owned by `delivery-config-pruner`; surviving generic formatting comments or docstrings are owned by `language-runtime-migrator`.
- `bot/models.py`, `bot/handler.py`, `bot/dispatcher.py`: removed delivery platform enums, handlers, and routing are owned by `delivery-config-pruner`; surviving command text, aliases, comments, and docstrings are owned by `language-runtime-migrator`.
- `apps/dsa-web/src/components/settings/*`: config-driven labels are owned by `delivery-config-pruner`; generic UI Chinese text is owned by `language-runtime-migrator`.
- `apps/dsa-web/src/index.css`: surviving comments and text-like CSS metadata are owned by `language-runtime-migrator` after config-driven UI cleanup.
- `tests/test_agent_pipeline.py`: tests span agent tools, search, and fixture language. Split edits by assertion area and delete China-only fixtures.
- `src/notification_sender/custom_webhook_sender.py`: generic custom webhook behavior may remain, but DingTalk-specific detection/signing/chunking is removed by `delivery-config-pruner`.
