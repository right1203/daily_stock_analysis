# Complete Removal Inventory

## Summary

- Status: refreshed from active residue and positive-control scans
- Scope owner: Task 1, refresh audit and ownership
- Date: 2026-04-26
- Mode: complete removal. China/HK market, data, search, delivery, config, UI, docs, and tests should be removed, not retained as compatibility shims.

## Commands

China/HK residue scan:

```bash
rg -n "\bcn\b|\bhk\b|A-share|A-shares|A股|港股|上证|深证|创业板|科创|东方财富|沪|深|Bocha|bocha|Akshare|akshare|Tushare|tushare|Baostock|baostock|PyTDX|pytdx|Efinance|efinance|Feishu|feishu|WeChat|wechat|DingTalk|dingtalk|PushPlus|pushplus|ServerChan|serverchan" src api bot data_provider apps/dsa-web/src apps/dsa-desktop tests docs README.md main.py server.py webui.py pyproject.toml requirements.txt --glob "!docs/CHANGELOG.md" --glob "!docs/plans/**" --glob "!docs/superpowers/**" --glob "!sources/**" --glob "!*.png" --glob "!*.jpg" --glob "!*.ico"
```

Result: succeeded with active matches.

KR/US positive-control scan:

```bash
rg -n "Naver|NAVER|naver|pykrx|KRX|KOSPI|KOSDAQ|yfinance|YFinance|Yahoo|US index|S&P 500|Nasdaq|Dow" src api bot data_provider apps/dsa-web/src tests docs README.md main.py server.py webui.py pyproject.toml requirements.txt --glob "!docs/CHANGELOG.md" --glob "!docs/plans/**" --glob "!docs/superpowers/**"
```

Result: succeeded with expected KR/US matches.

## Domain Findings

| Domain | High-signal files | Representative findings | Owner |
|--------|-------------------|--------------------------|-------|
| Dependencies | `pyproject.toml`, `requirements.txt` | `efinance`, `akshare`, `tushare`, `pytdx`, `baostock`, `dingtalk-stream`, and China/HK comments remain in install surfaces. `pykrx` and `yfinance` are positive controls to keep. | `market-data-removal`, `delivery-config-pruner` |
| Data providers | `data_provider/base.py`, `data_provider/__init__.py`, `data_provider/realtime_types.py`, `data_provider/akshare_fetcher.py`, `data_provider/efinance_fetcher.py`, `data_provider/tushare_fetcher.py`, `data_provider/baostock_fetcher.py`, `data_provider/pytdx_fetcher.py` | Chinese provider classes are imported, exported, prioritized, and referenced by realtime source enums. Provider files are deletion candidates. | `market-data-removal` |
| Shared data provider | `data_provider/yfinance_fetcher.py` | `yfinance` is a US positive control, but this file still contains A-share/HK code conversion and China index mapping. Remove China/HK branches while preserving US index handling. | `market-data-removal` |
| KR data positive controls | `data_provider/pykrx_fetcher.py`, `data_provider/kr_index_mapping.py`, `src/core/trading_calendar.py`, `tests/test_pykrx_fetcher.py`, `tests/test_kr_index_mapping.py`, `tests/test_kr_trading_calendar.py` | `pykrx`, KRX calendar, KOSPI/KOSDAQ mapping, and KR tests are present and should be preserved. | `market-data-removal` |
| US data positive controls | `data_provider/yfinance_fetcher.py`, `data_provider/us_index_mapping.py`, `tests/test_yfinance_us_indices.py`, `tests/test_us_index_mapping.py` | `yfinance`, Yahoo Finance, S&P 500, Nasdaq, Dow, and US index tests are present and should be preserved. | `market-data-removal` |
| Search routing | `src/search_service.py`, `src/agent/tools/search_tools.py`, `main.py` | `BochaSearchProvider`, `bocha_keys`, Bocha docs/logs, and constructor wiring remain. Existing global search providers such as Tavily, Brave, and SerpAPI are positive controls unless tied to China-specific defaults. | `search-routing-removal` |
| Naver search positive control | `bot/commands/status.py`, config/search wiring reachable from `src/search_service.py` | Naver status and key checks remain. Later tasks must preserve Naver for KR search. | `search-routing-removal` |
| Config registry | `src/config.py`, `src/core/config_registry.py`, `apps/dsa-web/src/utils/systemConfigI18n.ts` | `TUSHARE_TOKEN`, `REALTIME_SOURCE_PRIORITY` China defaults, `BOCHA_API_KEYS`, WeChat/Feishu/DingTalk/PushPlus/ServerChan fields, Chinese domain allowlist entries, and `MARKET_REVIEW_REGION` `cn` options remain. | `delivery-config-pruner`, `market-data-removal` |
| Delivery runtime | `src/notification.py`, `src/notification_sender/*`, `src/core/pipeline.py`, `main.py`, `bot/platforms/*`, `src/feishu_doc.py`, `src/formatters.py` | WeChat, Feishu, DingTalk, PushPlus, ServerChan, Feishu document creation, and DingTalk webhook special casing remain. Compatibility shim files are not acceptable in complete-removal mode. | `delivery-config-pruner` |
| API/bot surfaces | `bot/handler.py`, `bot/models.py`, `bot/commands/market.py`, `bot/platforms/*` | Bot platform registration and market command language still include China delivery or China market assumptions. | `delivery-config-pruner`, `language-runtime-migrator` |
| Web UI | `apps/dsa-web/src/utils/systemConfigI18n.ts`, `apps/dsa-web/src/components/settings/LLMChannelEditor.tsx`, `apps/dsa-web/src/pages/ChatPage.tsx`, `apps/dsa-web/src/index.css` | Settings labels expose removed config keys. Some `.cn` endpoints and Chinese UI/font defaults remain. User-facing surfaces should be Korean after cleanup. | `delivery-config-pruner`, `language-runtime-migrator` |
| Documentation | `README.md`, `docs/full-guide.md`, `docs/full-guide_EN.md`, `docs/FAQ*.md`, `docs/DEPLOY*.md`, `docs/bot-command.md`, `docs/bot/*`, `docs/architecture/api_spec.json` | Current docs still advertise China data sources, China/HK stock formats, Bocha, and China delivery channels. Historical `docs/CHANGELOG.md` is excluded from blocking scans. | `docs-sync-owner` |
| Tests | `tests/test_akshare_realtime_logging.py`, `tests/test_feishu_stream.py`, `tests/test_notification*.py`, `tests/test_agent_pipeline.py`, `tests/test_market_strategy.py`, `tests/test_stock_code_bse.py`, `tests/test_market_analyzer_generate_text.py` | Tests still assert China data providers, China market names, `cn` region behavior, Bocha config, and China delivery channels. Delete provider-specific tests with deleted files; update shared tests to KR/US expectations. | owner follows touched feature area |

## Deleted-File Candidates

- Data providers: `data_provider/akshare_fetcher.py`, `data_provider/efinance_fetcher.py`, `data_provider/tushare_fetcher.py`, `data_provider/baostock_fetcher.py`, `data_provider/pytdx_fetcher.py`.
- Delivery senders: `src/notification_sender/feishu_sender.py`, `src/notification_sender/wechat_sender.py`, `src/notification_sender/pushplus_sender.py`, `src/notification_sender/serverchan3_sender.py`.
- Bot delivery platforms: `bot/platforms/feishu_stream.py`, `bot/platforms/dingtalk.py`, `bot/platforms/dingtalk_stream.py`.
- Feishu document path: `src/feishu_doc.py`.
- Provider/delivery tests tied only to deleted surfaces: `tests/test_akshare_realtime_logging.py`, `tests/test_feishu_stream.py`, plus removed-channel sections of `tests/test_notification.py` and `tests/test_notification_sender.py`.
- Docs for deleted bot integrations: `docs/bot/feishu-bot-config.md`, `docs/bot/dingding-bot-config.md`.

## Preservation Rules

- Preserve `pykrx`, KRX trading calendar behavior, KR index mapping, and Naver search.
- Preserve `yfinance`, US index mapping, and existing global search providers.
- Do not keep China/HK code through aliases, hidden flags, empty shims, deprecated senders, or compatibility wrappers.
- Do not translate or polish files that should be deleted; remove the deleted surface first, then clean shared files.
