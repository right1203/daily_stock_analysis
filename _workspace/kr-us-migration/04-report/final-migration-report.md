# Final Migration Report

## Status

- KR+US pytest remediation completed on `codex/kr-us-market-cleanup`
- broader China surface migration still in progress

## Verification Summary

- Baseline audit artifacts now identify remaining China-specific surfaces and KR+US positive controls.
- Worker handoff files now contain queued scopes, ownership boundaries, risks, and suggested verification commands.
- Before remediation: `45 failed, 385 passed, 21 skipped, 33 warnings, 88 subtests passed`.
- After remediation: `430 passed, 21 skipped, 39 warnings, 88 subtests passed in 23.68s`.
- Focused remediation suite: `122 passed, 1 warning in 1.93s`.

## Blocking Findings

- Active code still references some China market/search/delivery surfaces. See `_workspace/kr-us-migration/01-audit/china-surface-inventory.md`.
- `src/core/config_registry.py`, `src/search_service.py`, bot platform integrations, and generated/API documentation remain cross-cutting coordination points.
- China-channel sender modules are compatibility shims and are now detached from active channel detection/validation, but downstream UI/docs cleanup still needs a separate pass.

## Non-Blocking Findings

- `docs/CHANGELOG.md` contains historical Chinese entries and should be treated as archival unless current release notes are rewritten.
- `pykrx` currently requires `pkg_resources`, so runtime dependency resolution pins `setuptools<81`; this should be revisited when `pykrx` removes that dependency.
