# KR+US Migration Harness Design

**Date:** 2026-04-03

## Goal

중국 시장 중심의 주식 분석 저장소를 한국+미국 시장 중심 저장소로 전환하기 위한 Codex 하네스를 정의한다. 하네스는 중국 시장, 중국 검색, 중국 서비스, 중국어 식별자 잔재를 체계적으로 찾아 제거하고, 한국 검색은 네이버 API로, 미국 검색은 기존 글로벌 검색기로 유지하는 반복 가능한 작업 흐름을 제공한다.

## Scope

- 중국 시장 전제 제거: `cn`, `hk`, A-share, 중국 거래소/지수/검색 가정 제거
- 중국 서비스 제거: `Tushare`, `Baostock`, `PyTDX`, `Efinance`, `Bocha`, `Feishu`, `WeChat`, `DingTalk`, `PushPlus`, `ServerChan`
- 언어 정책 정리: LLM 상호작용, 주석, 로그, 프롬프트, UI 문구를 한국어 또는 영어만 남김
- 코드 식별자 규칙: 중국어 식별자는 영어로 변경, 한국어 식별자는 새로 도입하지 않음
- 검색 정책 정리: 한국 종목/시장 검색은 네이버 API, 미국 종목/시장 검색은 기존 글로벌 검색기 유지

## Non-Goals

- 이번 하네스 문서 자체가 저장소 전체 마이그레이션을 수행하지는 않음
- 전역 `~/.codex/skills` 설치는 하지 않음
- 실제 커밋/PR 생성 흐름은 포함하지 않음

## Architecture Choice

단일 에이전트보다 오케스트레이터 기반 팬아웃/팬인 구조를 사용한다. 이번 작업은 조사, 시장/검색 수정, 언어/식별자 정리, 설정/알림 정리, 검증으로 책임이 분리되고 상호 파일 소유권을 명확히 자를 수 있기 때문이다.

흐름은 다음과 같다.

1. 감사: 중국 표면적과 KR/US 전환 진행 상태를 인벤토리화
2. 병렬 수정: 시장/검색, 언어/식별자, 설정/알림을 분리 수행
3. 검증: 중국 잔재, 검색 라우팅, 언어 규칙, 핵심 검증 명령을 점검
4. 통합: 최종 보고서와 남은 리스크 정리

## Agent Set

| Agent | Type | Responsibility | Writes |
|------|------|----------------|--------|
| `china-surface-auditor` | `explorer` | 중국 표면적 전수 조사, 파일 소유권 제안 | `_workspace/kr-us-migration/01-audit/*.md` |
| `market-search-migrator` | `worker` | 시장 분기, 데이터 공급자, 검색 라우팅 정리 | `_workspace/kr-us-migration/02-handoffs/market-search.md` |
| `language-runtime-migrator` | `worker` | 프롬프트, 로그, 문구, 중국어 식별자 정리 | `_workspace/kr-us-migration/02-handoffs/language-runtime.md` |
| `delivery-config-pruner` | `worker` | 설정, 알림 채널, 문서, `.env.example` 정리 | `_workspace/kr-us-migration/02-handoffs/delivery-config.md` |
| `migration-verifier` | `explorer` | 잔존 흔적 스캔, 검증 결과 정리 | `_workspace/kr-us-migration/04-report/final-migration-report.md` |

## Workspace Layout

```text
_workspace/kr-us-migration/
  00-charter.md
  README.md
  01-audit/
    china-surface-inventory.md
    ownership-map.md
  02-handoffs/
    market-search.md
    language-runtime.md
    delivery-config.md
  03-validation/
    skill-trigger-tests.md
    verification-checklist.md
  04-report/
    final-migration-report.md
```

## Quality Gates

- 활성 코드 경로, 설정, 문서, 프롬프트, 로그에 중국어 문장이 남지 않아야 한다.
- 활성 경로에 중국 서비스 의존이 남지 않아야 한다.
- 한국 검색은 네이버 API 제공자 기반으로 확인 가능해야 한다.
- 미국 검색은 글로벌 검색기 유지가 확인 가능해야 한다.
- `cn`/`hk` 기본값과 시장 분기 잔재가 제거되어야 한다.
- 중국어 식별자는 영어 식별자로 치환되어야 한다.

## Risks

- 더티 워크트리에서 기존 사용자 변경과 충돌할 수 있다.
- 문서와 코드의 중국 서비스 제거 범위가 비동기적으로 남을 수 있다.
- 식별자 리네임은 테스트와 참조 문자열을 광범위하게 흔들 수 있다.

## Execution Note

이 설계는 실제 하네스 산출물 생성에 사용되며, 이 저장소의 정책에 따라 명시적 요청 없이 커밋하지 않는다.
