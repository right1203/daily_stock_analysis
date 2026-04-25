# Delivery Config Handoff

## Status

- queued from baseline audit

## Owned Files

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

## Queued Work

- Remove China delivery channels from active config and settings surfaces: Feishu, WeChat, DingTalk, PushPlus, ServerChan.
- Remove Bocha and Tushare/China data provider settings from config UI and docs.
- Preserve Discord, Telegram, email, Pushover, custom webhook where they are not China-specific.
- Update docs so current setup describes KR+US, Naver, `pykrx`, and `yfinance`.
- Remove Feishu document integration from active startup paths or mark it unsupported consistently.

## Remaining Risks

- Existing notification tests still cover China channels; update or remove them in the same slice as the channel cleanup.
- Some sender modules already act as compatibility shims. Decide whether to keep unsupported stubs temporarily or remove imports fully.
- API schema docs are generated-like JSON; update them only with the same source-of-truth convention used by the project.

## Suggested Verification

```bash
pytest tests/test_config_validate_structured.py tests/test_system_config_service.py tests/test_notification.py tests/test_notification_sender.py -v
```
