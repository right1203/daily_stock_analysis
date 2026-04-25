# KR+US Market Migration Orchestrator

중국 시장 중심 저장소를 한국+미국 시장 중심 저장소로 전환할 때 사용하는 Codex 오케스트레이터 가이드다. 메인 에이전트가 감사, 병렬 수정, 검증을 조율하고, 모든 핸드오프는 `_workspace/kr-us-migration` 산출물로 남긴다.

## Current Reinforcement Mode

이 저장소는 이미 KR+US 전환이 일부 진행된 상태다. 오케스트레이터는 전체 재작성보다 기존 하네스를 보강하고, 남은 중국 표면을 실제 감사 결과로 추적한다.

유지 대상:

- 한국 시장: `pykrx`, KRX 거래일, KOSPI/KOSDAQ 매핑
- 한국 검색: Naver API
- 미국 시장: `yfinance`, US index mapping
- 미국 검색: 기존 글로벌 검색기

제거 대상:

- 중국 시장: `cn`, `hk`, A-share/HK stock routing
- 중국 검색: Bocha, 중국 지역/언어 기본값, 중국어 검색 템플릿
- 중국 데이터 공급자: Tushare, Baostock, PyTDX, Efinance
- 중국 전달 채널: Feishu, WeChat, DingTalk, PushPlus, ServerChan

## Agent Matrix

| Name | agent_type | Model | Ownership | Output |
|------|-----------|-------|-----------|--------|
| `china-surface-auditor` | `explorer` | inherit | 읽기 전용 감사, 파일 소유권 제안 | `_workspace/kr-us-migration/01-audit/china-surface-inventory.md` |
| `market-search-migrator` | `worker` | inherit | `src/search_service.py`, `data_provider/`, 시장/검색/데이터 라우팅 | `_workspace/kr-us-migration/02-handoffs/market-search.md` |
| `language-runtime-migrator` | `worker` | inherit | 사용자 문구, 프롬프트, 로그, 식별자 정리 | `_workspace/kr-us-migration/02-handoffs/language-runtime.md` |
| `delivery-config-pruner` | `worker` | inherit | `src/config.py`, 설정 레지스트리, 알림 채널, 문서 | `_workspace/kr-us-migration/02-handoffs/delivery-config.md` |
| `migration-verifier` | `explorer` | inherit | 잔존 흔적 스캔, 검증 보고서 | `_workspace/kr-us-migration/04-report/final-migration-report.md` |

## Phase 1: Prepare

1. 사용자 요청에서 다음을 고정한다.
   - 중국 생태계 제거 범위
   - 한국 검색은 네이버 API
   - 미국 검색은 기존 글로벌 검색기 유지
   - 중국어 식별자는 영어로 변경
2. `_workspace/kr-us-migration/00-charter.md`를 최신 규칙으로 갱신한다.
3. 감사 시작 전에 더티 워크트리와 충돌 가능성을 확인한다.

## Phase 2: Audit

1. `china-surface-auditor`를 읽기 전용으로 시작한다.
2. 다음 관점의 인벤토리를 작성하게 한다.
   - 중국어 문자열
   - 중국 서비스 의존성
   - `cn`/`hk` 시장 분기
   - 중국어 식별자
   - KR/US 전환이 이미 반영된 지점
3. `ownership-map.md`에 수정 후보를 워커별로 분배한다.

예시 프롬프트:

```text
Read-only audit. Own no edits. Inspect active code, config, docs, and tests for Chinese market assumptions, Chinese-language user text, China-only services, and Chinese identifiers. Write findings to _workspace/kr-us-migration/01-audit/china-surface-inventory.md and propose disjoint file ownership in _workspace/kr-us-migration/01-audit/ownership-map.md.
```

## Phase 3: Fan Out

감사 결과를 기준으로 병렬 가능한 워커만 시작한다.

### market-search-migrator

- 한국 검색을 네이버 API로 전환
- 미국 검색은 기존 글로벌 검색기 유지
- 중국 데이터 공급자와 중국 시장 분기를 제거

### language-runtime-migrator

- 중국어 문장 제거
- 프롬프트, 로그, 사용자 메시지를 한국어/영어로 정리
- 중국어 식별자를 영어로 치환

### delivery-config-pruner

- 중국 서비스 관련 env/config 제거
- 문서와 설정 기본값 정리
- 제거 대상 알림 채널과 설명 정리

각 워커 프롬프트에는 아래를 반드시 포함한다.

- 소유 파일 범위
- 다른 워커 변경을 되돌리지 말 것
- 충돌 발견 시 즉시 보고할 것
- 요약 결과를 지정된 `_workspace` 파일에 남길 것

## Phase 4: Handoff

1. 메인 에이전트만 `send_input`으로 핸드오프한다.
2. 한 워커 결과를 다른 워커가 참고해야 하면 요약만 전달한다.
3. 긴 내용은 파일 경로로 전달하고, 메시지는 의사결정만 남긴다.

예시:

```text
Use _workspace/kr-us-migration/01-audit/ownership-map.md as the source of truth for file boundaries. Do not expand into delivery/config files.
```

## Phase 5: Verify And Integrate

1. `migration-verifier`를 실행한다.
2. 아래 항목을 보고서로 정리하게 한다.
   - 중국어 잔존 여부
   - 중국 서비스 잔존 여부
   - `cn`/`hk` 잔존 여부
   - 네이버 검색 제공자 존재 여부
   - `pykrx`/KRX 및 `yfinance`/US 경로 보존 여부
   - 핵심 테스트/문법 검증 결과
3. 메인 에이전트가 최종 결과를 사용자에게 요약한다.

## Failure Policy

- 한 워커가 실패하면 1회만 범위를 좁혀 재지시한다.
- 파일 소유권 충돌이 생기면 메인 에이전트가 즉시 ownership을 재분배한다.
- 감사 산출물이 불완전하면 수정 작업을 시작하지 않는다.

## Output Contract

- 감사: `_workspace/kr-us-migration/01-audit/*.md`
- 워커 핸드오프: `_workspace/kr-us-migration/02-handoffs/*.md`
- 검증: `_workspace/kr-us-migration/03-validation/*.md`
- 최종 보고: `_workspace/kr-us-migration/04-report/final-migration-report.md`
