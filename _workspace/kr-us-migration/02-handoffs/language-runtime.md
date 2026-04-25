# Language Runtime Handoff

## Status

- in progress on `codex/kr-us-market-cleanup`

## Owned Files

- User-facing strings, prompts, logs, docstrings, and comments in active runtime files
- `src/analyzer.py`
- `src/core/pipeline.py`
- `src/services/`
- `api/`
- `bot/commands/`
- `apps/dsa-web/src/pages/`
- `apps/dsa-web/src/components/`
- Tests that assert text output or fixture names

## Queued Work

- Translate remaining Chinese user-facing messages to Korean or English.
- Convert mixed Chinese/Korean comments and docstrings to Korean or English.
- Rename Chinese identifiers to English where they are active code identifiers.
- Update tests that assert Chinese labels, example stock names, or Chinese market descriptions.
- Leave historical `docs/CHANGELOG.md` entries alone unless current release notes are being rewritten.

## Remaining Risks

- Broad renames can affect API schemas, saved history, and serialized report fields. Prefer message translation first and identifier renames second.
- Frontend strings and backend schema descriptions may need coordinated updates to avoid mismatched UI/API text.
- Some Chinese characters appear in proper nouns or historical references; classify before replacing.

## Completed In Current Slice

- Agent user-message tests now assert Korean labels for stock code, report type, and decision dashboard output.
- Structured config validation tests now assert Korean notification/search messages.
- Realtime indicator tests now use KR stock examples and Korean MA status labels.

## Suggested Verification

```bash
rg -n "[\p{Han}]" src api bot apps/dsa-web/src tests --glob '!apps/dsa-web/package-lock.json'
python3 -m py_compile main.py src/*.py data_provider/*.py
```

Completed:

```bash
uv run pytest tests/test_agent_executor.py::TestBuildUserMessage tests/test_config_validate_structured.py::TestValidateStructuredNotification tests/test_pipeline_realtime_indicators.py -q
```
