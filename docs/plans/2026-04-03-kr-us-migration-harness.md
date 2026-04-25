# KR+US Migration Harness Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 중국 시장 기반 주식 분석 저장소를 한국+미국 시장 기반으로 전환하기 위한 Codex 하네스 산출물을 생성한다.

**Architecture:** 오케스트레이터가 먼저 중국 표면적을 감사하고, 이후 시장/검색, 언어/식별자, 설정/알림 정리를 병렬 워커 브리프로 분리한다. 각 역할은 `_workspace/kr-us-migration` 아래 파일 산출물을 남기고, 최종 검증 에이전트가 잔존 흔적과 검증 결과를 통합한다.

**Tech Stack:** Markdown, Codex harness briefs, repository-local skill draft, ripgrep-based audit, Python validator script

---

### Task 1: Write The Design And Charter

**Files:**
- Create: `docs/plans/2026-04-03-kr-us-migration-harness-design.md`
- Create: `_workspace/kr-us-migration/00-charter.md`
- Create: `_workspace/kr-us-migration/README.md`

**Step 1: Write the design document**

설계 문서에 목표, 범위, 비목표, 아키텍처 선택, 에이전트 집합, 품질 게이트를 기록한다.

**Step 2: Write the workspace charter**

차터에 아래 규칙을 적는다.

- KR 검색은 네이버 API
- US 검색은 기존 글로벌 검색 유지
- 중국 서비스 제거
- 중국어 식별자는 영어로만 변경
- 커밋은 사용자 승인 전 금지

**Step 3: Write the workspace README**

워크스페이스 폴더 구조와 산출물 파일명 규칙을 적는다.

**Step 4: Verify the files exist**

Run: `find docs/plans .codex/harness _workspace/kr-us-migration -maxdepth 2 -type f | sort`
Expected: design doc, workspace charter, and workspace README are listed

### Task 2: Author The Orchestrator

**Files:**
- Create: `.codex/harness/orchestrator.md`

**Step 1: Draft the orchestrator**

오케스트레이터 문서에 에이전트 표, 각 phase, `spawn_agent`/`send_input`/`wait_agent`/`close_agent` 사용 기준, 파일 전달 규칙을 적는다.

**Step 2: Add output paths**

각 에이전트가 쓰는 `_workspace/kr-us-migration/...` 경로를 명시한다.

**Step 3: Review for Codex-only concepts**

Claude 전용 개념이나 가짜 에이전트 타입이 없는지 확인한다.

### Task 3: Author Agent Briefs

**Files:**
- Create: `.codex/harness/agents/china-surface-auditor.md`
- Create: `.codex/harness/agents/market-search-migrator.md`
- Create: `.codex/harness/agents/language-runtime-migrator.md`
- Create: `.codex/harness/agents/delivery-config-pruner.md`
- Create: `.codex/harness/agents/migration-verifier.md`

**Step 1: Write one brief per role**

각 브리프에 아래 섹션을 포함한다.

- Role
- Ownership
- Inputs
- Outputs
- Boundaries
- Handoff Rules
- Failure Handling

**Step 2: Keep ownership disjoint**

서로 다른 워커가 같은 파일 세트를 수정하지 않도록 명시한다.

**Step 3: Review with ripgrep**

Run: `rg -n "Role|Ownership|Inputs|Outputs|Boundaries|Handoff Rules|Failure Handling" .codex/harness/agents`
Expected: every agent brief contains the required sections

### Task 4: Author The Repository-Local Skill Draft

**Files:**
- Create: `.codex/harness/skills/kr-us-market-migration/SKILL.md`

**Step 1: Write the frontmatter**

`name`과 `description`만 사용하고, description은 언제 이 스킬을 써야 하는지만 적는다.

**Step 2: Write the skill body**

본문에는 다음을 적는다.

- 적용 조건
- 기본 규칙
- 감사 절차
- 역할 브리프 참조 경로
- 검증 게이트
- 산출물 경로

**Step 3: Add realistic prompts**

2~3개의 현실적인 실행 프롬프트 예시를 포함하거나 별도 검증 문서와 연결한다.

### Task 5: Add Validation Assets

**Files:**
- Create: `_workspace/kr-us-migration/03-validation/skill-trigger-tests.md`
- Create: `_workspace/kr-us-migration/03-validation/verification-checklist.md`

**Step 1: Write trigger tests**

should-trigger와 should-not-trigger 프롬프트를 각각 적는다.

**Step 2: Write the verification checklist**

다음을 포함한다.

- 중국어 잔존 스캔
- 중국 서비스 잔존 스캔
- `cn`/`hk` 시장 분기 잔존 스캔
- 네이버 검색 제공자 존재 확인
- 핵심 검증 명령

**Step 3: Verify grep patterns are explicit**

Run: `sed -n '1,240p' _workspace/kr-us-migration/03-validation/verification-checklist.md`
Expected: concrete `rg`, `pytest`, and `py_compile` commands are present

### Task 6: Validate The Skill Draft

**Files:**
- Modify: `.codex/harness/skills/kr-us-market-migration/SKILL.md`

**Step 1: Run the skill validator**

Run: `python3 /Users/younghun/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/harness/skills/kr-us-market-migration/SKILL.md`
Expected: frontmatter and structure validation pass

**Step 2: Fix any validator findings**

필요하면 frontmatter와 본문 구조를 최소 수정한다.

**Step 3: Re-run validation**

Run: `python3 /Users/younghun/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/harness/skills/kr-us-market-migration/SKILL.md`
Expected: PASS

### Task 7: Review The Harness As A Whole

**Files:**
- Review: `docs/plans/2026-04-03-kr-us-migration-harness-design.md`
- Review: `docs/plans/2026-04-03-kr-us-migration-harness.md`
- Review: `.codex/harness/**`
- Review: `_workspace/kr-us-migration/**`

**Step 1: List created files**

Run: `find docs/plans .codex/harness _workspace/kr-us-migration -type f | sort`
Expected: all planned harness files are present

**Step 2: Scan for forbidden residues**

Run: `rg -n "\\.claude/|TeamCreate|SendMessage|TaskCreate|TaskUpdate|general-purpose|Explore|Plan|model: \\\"opus\\\"" docs/plans .codex/harness _workspace/kr-us-migration`
Expected: no matches

**Step 3: Review against scope**

하네스가 중국 시장 제거, 네이버 검색, US 글로벌 검색 유지, 중국어 식별자 영어화 규칙을 모두 포함하는지 확인한다.

**Step 4: Optional commit step**

이 저장소는 명시적 승인 없이 커밋하지 않는다. 사용자가 요청한 경우에만 아래를 실행한다.

```bash
git add docs/plans .codex/harness _workspace/kr-us-migration
git commit -m "docs: add KR+US migration harness"
```
