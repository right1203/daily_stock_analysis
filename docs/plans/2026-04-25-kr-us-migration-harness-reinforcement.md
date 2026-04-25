# KR+US Migration Harness Reinforcement Implementation Plan

> **For Codex:** Use the repository-local harness briefs in `.codex/harness/agents/`. Do not commit unless the user explicitly approves it.

**Goal:** Turn the existing KR+US migration harness from a mostly scaffolded set of files into an actionable workflow with real audit evidence, ownership boundaries, and verification gates.

**Architecture:** Keep the current orchestrator and agent brief structure. Fill the audit and ownership artifacts first, then use those artifacts to drive market/search, language/runtime, and delivery/config cleanup in separate slices. Verification remains a final read-only gate.

**Tech Stack:** Markdown harness artifacts, Codex subagent briefs, `rg`, `py_compile`, `pytest`, Python 3.10+, React/TypeScript Web UI.

---

### Task 1: Refresh The Harness Design

**Files:**
- Create: `docs/plans/2026-04-25-kr-us-migration-harness-reinforcement-design.md`
- Modify: `.codex/harness/orchestrator.md`
- Modify: `.codex/harness/skills/kr-us-market-migration/SKILL.md`

**Step 1: Record the approved approach**

Document that the user chose to reinforce the existing KR+US harness rather than replacing it.

**Step 2: Preserve the KR+US decisions**

State that Korean market support, Naver search, US market support, `yfinance`, and the existing global search path are retained.

**Step 3: Clarify non-goals**

State that this harness update does not globally install a skill and does not commit without approval.

**Step 4: Validate the repository-local skill**

Run:

```bash
python3 /Users/younghun/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/harness/skills/kr-us-market-migration/SKILL.md
```

Expected: validation passes.

### Task 2: Replace Pending Audit Placeholders

**Files:**
- Modify: `_workspace/kr-us-migration/01-audit/china-surface-inventory.md`
- Modify: `_workspace/kr-us-migration/01-audit/ownership-map.md`

**Step 1: Run focused scans**

Run:

```bash
rg -l "[\p{Han}]" src api bot data_provider apps/dsa-web/src tests docs README.md main.py analyzer_service.py webui.py server.py strategies --glob '!docs/CHANGELOG.md' --glob '!apps/dsa-web/package-lock.json' --glob '!sources/**'
```

Expected: files with remaining Chinese-language or Chinese-market text are listed.

Run:

```bash
rg -n "Tushare|Baostock|PyTDX|pytdx|Efinance|efinance|Bocha|bocha|Feishu|feishu|WeChat|wechat|DingTalk|dingtalk|PushPlus|pushplus|ServerChan|serverchan" src api bot data_provider apps/dsa-web/src tests docs README.md main.py analyzer_service.py webui.py server.py --glob '!docs/CHANGELOG.md' --glob '!apps/dsa-web/package-lock.json' --glob '!sources/**'
```

Expected: China-specific service references are listed.

**Step 2: Summarize by ownership**

Group findings into market/search, language/runtime, and delivery/config ownership. Avoid assigning the same file to multiple workers unless the ownership map explicitly marks a coordination point.

**Step 3: Mark positive KR+US controls**

Record existing `pykrx`, KRX, Naver, `yfinance`, and US index mapping surfaces so future cleanup does not remove them.

### Task 3: Prepare Worker Handoff Files

**Files:**
- Modify: `_workspace/kr-us-migration/02-handoffs/market-search.md`
- Modify: `_workspace/kr-us-migration/02-handoffs/language-runtime.md`
- Modify: `_workspace/kr-us-migration/02-handoffs/delivery-config.md`

**Step 1: Convert placeholders into scoped backlogs**

For each handoff, record owned files, queued actions, blocked coordination points, and verification commands.

**Step 2: Keep file boundaries disjoint**

If a file crosses boundaries, assign a primary owner and list the secondary owner as a reviewer.

**Step 3: Leave implementation status clear**

Because this task reinforces the harness rather than completing the full migration, mark code cleanup as queued rather than complete.

### Task 4: Strengthen Verification Gates

**Files:**
- Modify: `_workspace/kr-us-migration/03-validation/verification-checklist.md`
- Modify: `_workspace/kr-us-migration/03-validation/skill-trigger-tests.md`
- Modify: `_workspace/kr-us-migration/04-report/final-migration-report.md`

**Step 1: Add removal scans**

Include explicit commands for Chinese text, China services, `cn`/`hk`, A-share/HK, Bocha, and China delivery channels.

**Step 2: Add retention scans**

Include positive checks for Naver, `pykrx`, KRX, `yfinance`, KR index mapping, and US index mapping.

**Step 3: Add executable validation**

Include `py_compile` and focused pytest commands for KR market, US index, search freshness, config, and notification routing.

### Task 5: Whole-Harness Review

**Files:**
- Review: `docs/plans/2026-04-25-kr-us-migration-harness-reinforcement-design.md`
- Review: `docs/plans/2026-04-25-kr-us-migration-harness-reinforcement.md`
- Review: `.codex/harness/**`
- Review: `_workspace/kr-us-migration/**`

**Step 1: List harness files**

Run:

```bash
find docs/plans .codex/harness _workspace/kr-us-migration -type f | sort
```

Expected: reinforced design, execution plan, orchestrator, briefs, skill draft, audit, handoffs, validation, and final report files are listed.

**Step 2: Scan for non-Codex leftovers**

Run:

```bash
rg -n "\\.cl[a]ude/|Team[C]reate|Send[M]essage|Task[C]reate|Task[U]pdate|general-purpos[e]|model: \"op[u]s\"" .codex/harness _workspace/kr-us-migration
```

Expected: no matches.

**Step 3: Validate the skill draft**

Run:

```bash
python3 /Users/younghun/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/harness/skills/kr-us-market-migration/SKILL.md
```

Expected: validation passes.
