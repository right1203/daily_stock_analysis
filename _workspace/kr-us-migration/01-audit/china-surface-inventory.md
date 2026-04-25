# China Surface Inventory

## Summary

- Status: baseline captured from focused static scans
- Scope owner: `china-surface-auditor`
- Date: 2026-04-25

이 감사는 하네스 보강을 위한 기준선이다. 전체 마이그레이션 완료를 의미하지 않는다.

## Findings

| Area | File | Pattern | Impact | Recommended Owner |
|------|------|---------|--------|-------------------|
| market/search | `src/search_service.py` | Bocha search engine, China SerpAPI defaults, A-share/HK keyword templates | 한국 Naver 검색과 미국 글로벌 검색 정책을 흐릴 수 있음 | `market-search-migrator` |
| market/search | `src/market_analyzer.py` | `region="cn"`, A-share market labels, China index assumptions | 시장 리뷰 기본값이 KR+US 정책과 충돌 | `market-search-migrator` |
| market/search | `src/agent/tools/market_tools.py` | tool schema exposes `cn` and China A-share descriptions | Agent가 중국 시장을 유효 경로로 안내할 수 있음 | `market-search-migrator` |
| market/search | `src/agent/tools/data_tools.py` | A-share/HK examples and A-share stock code descriptions | Agent tool metadata가 중국 종목을 기본 예시로 유지 | `market-search-migrator` |
| data providers | `data_provider/base.py` | Efinance, Akshare, Tushare, PyTDX, Baostock default fetcher list | 중국 데이터 공급자가 fallback 경로에 남을 수 있음 | `market-search-migrator` |
| data providers | `data_provider/akshare_fetcher.py` | A-share/HK routing, Sina/Tencent/Eastmoney endpoints | 중국 시장 활성 경로가 가장 크게 남아 있음 | `market-search-migrator` |
| data providers | `data_provider/efinance_fetcher.py` | deprecated Chinese A-share fetcher | 제거 또는 비활성화 후보 | `market-search-migrator` |
| data providers | `data_provider/tushare_fetcher.py` | deprecated Chinese A-share fetcher | 제거 또는 비활성화 후보 | `market-search-migrator` |
| data providers | `data_provider/baostock_fetcher.py` | deprecated Chinese A-share fetcher | 제거 또는 비활성화 후보 | `market-search-migrator` |
| data providers | `data_provider/pytdx_fetcher.py` | deprecated Chinese A-share fetcher | 제거 또는 비활성화 후보 | `market-search-migrator` |
| data providers | `data_provider/yfinance_fetcher.py` | A-share/HK conversion comments and index mapping | US `yfinance`는 유지하되 중국 변환 경로 제거 필요 | `market-search-migrator` |
| delivery/config | `src/config.py` | Bocha, Feishu, WeChat, DingTalk, PushPlus, ServerChan, China domain allowlist | 설정 표면이 중국 서비스와 중국 데이터 소스를 계속 노출 | `delivery-config-pruner` |
| delivery/config | `src/core/config_registry.py` | Tushare, Bocha, WeChat, DingTalk, Feishu, PushPlus, ServerChan fields | Web/API 설정 레지스트리에서 중국 서비스가 계속 보임 | `delivery-config-pruner` |
| delivery/config | `src/notification.py` | WeChat/Feishu/DingTalk/PushPlus/ServerChan channels | 알림 서비스 제거 정책과 충돌 | `delivery-config-pruner` |
| delivery/config | `src/notification_sender/*` | compatibility shims and sender classes for China channels | 일부는 비활성 shim, 일부는 테스트/설정과 연결됨 | `delivery-config-pruner` |
| delivery/config | `main.py`, `bot/platforms/*`, `src/feishu_doc.py` | Feishu/DingTalk startup and document integration | 중국 전달 채널 활성화 경로가 남아 있음 | `delivery-config-pruner` |
| docs/frontend | `README.md`, `docs/`, `apps/dsa-web/src/utils/systemConfigI18n.ts`, `apps/dsa-web/src/components/settings/*` | Chinese service labels and Chinese UI strings | 사용자 노출 문서/UI가 KR+US 전환과 불일치 | `delivery-config-pruner` with `language-runtime-migrator` review |
| language/runtime | `src/analyzer.py`, `src/core/pipeline.py`, `src/services/*`, `api/*`, `bot/commands/*`, `apps/dsa-web/src/**` | Chinese comments, logs, prompts, labels, fixtures | 런타임 메시지와 LLM 프롬프트가 중국어 기반으로 보일 수 있음 | `language-runtime-migrator` |
| tests | `tests/test_stock_code_bse.py`, `tests/test_pipeline_realtime_indicators.py`, `tests/test_notification*.py`, `tests/test_agent_pipeline.py` | Chinese market fixtures and China delivery channel assertions | 제거 작업 후 테스트 기대값 갱신 필요 | primary owner follows touched feature area |

## Notes

- Positive KR+US controls already exist: `data_provider/pykrx_fetcher.py`, `data_provider/kr_index_mapping.py`, `data_provider/yfinance_fetcher.py`, `data_provider/us_index_mapping.py`, `src/core/trading_calendar.py`, Naver status in `bot/commands/status.py`.
- `docs/CHANGELOG.md` contains historical Chinese release notes. Treat it as archival unless the user-facing current release section is being rewritten.
- `apps/dsa-web/package-lock.json` can contain incidental `cn`/`hk` substrings inside integrity hashes. Exclude it from semantic scans.
