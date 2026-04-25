---
name: kr-us-market-migration
description: Use when a repository needs Chinese stock-market assumptions removed and replaced with Korean plus US stock analysis, including Naver search for Korean market content, retention of global search for US market content, removal of China-specific services, and renaming Chinese identifiers to English.
---

# KR+US Market Migration

## Overview

중국 시장 중심 저장소를 한국+미국 시장 중심 저장소로 바꾸는 저장소 전용 하네스 스킬이다. 중국 시장, 중국 검색, 중국 서비스, 중국어 식별자를 함께 정리하고, 한국 검색은 네이버 API로, 미국 검색은 기존 글로벌 검색기로 유지한다.

현재 저장소는 KR+US 전환이 일부 진행된 상태일 수 있다. 기존 `pykrx`, KRX, Naver, `yfinance`, US index mapping 경로는 보존 대상으로 먼저 확인하고, 남은 중국 표면만 제거 대상으로 분류한다.

## Use This Skill When

- 사용자 요청이 중국 시장 제거, KR+US 전환, 네이버 검색 API 도입을 함께 요구할 때
- 중국어 프롬프트, 로그, 주석, UI, 식별자를 정리해야 할 때
- Feishu, WeChat, DingTalk, PushPlus, ServerChan, Tushare, Baostock, PyTDX, Efinance, Bocha 같은 중국 생태계를 제거해야 할 때

## Do Not Use This Skill When

- 단일 문자열 번역만 필요한 경우
- 한국 시장만 추가하고 중국 시장은 유지해야 하는 경우
- 알림 채널 일부만 교체하는 작은 작업인 경우

## Ground Rules

- 사용자 노출 문구는 한국어 또는 영어만 남긴다.
- 코드 식별자는 영어만 사용한다.
- 중국어 식별자는 영어로 리네임한다.
- 한국 검색은 네이버 API를 사용한다.
- 미국 검색은 기존 글로벌 검색기를 유지한다.
- 한국 시장 데이터는 `pykrx`/KRX 경로를 우선 보존한다.
- 미국 시장 데이터는 `yfinance` 경로를 보존한다.
- 하네스 산출물은 `.codex/harness/`와 `_workspace/kr-us-migration/` 아래에 남긴다.
- 사용자가 명시적으로 요청하지 않는 한 전역 `~/.codex/skills`에 설치하지 않는다.
- 사용자가 명시적으로 승인하지 않는 한 커밋하지 않는다.

## Workflow

1. `_workspace/kr-us-migration/00-charter.md`를 읽고 범위를 고정한다.
2. `.codex/harness/agents/china-surface-auditor.md` 기준으로 감사부터 수행한다.
3. 감사 결과를 `_workspace/kr-us-migration/01-audit/`에 기록한다.
4. 기존 KR+US 보존 대상과 중국 제거 대상을 분리한다.
5. 수정이 필요하면 아래 브리프를 따른다.
   - `.codex/harness/agents/market-search-migrator.md`
   - `.codex/harness/agents/language-runtime-migrator.md`
   - `.codex/harness/agents/delivery-config-pruner.md`
6. 검증은 `.codex/harness/agents/migration-verifier.md`와 `_workspace/kr-us-migration/03-validation/verification-checklist.md`를 기준으로 진행한다.

## Required Outputs

- 감사 인벤토리
- 파일 소유권 맵
- 워커별 핸드오프 메모
- 검증 체크리스트
- 최종 마이그레이션 보고서

## Positive Controls

- `data_provider/pykrx_fetcher.py`
- `data_provider/kr_index_mapping.py`
- `data_provider/yfinance_fetcher.py`
- `data_provider/us_index_mapping.py`
- `src/core/trading_calendar.py`
- Naver API 설정과 상태 표시 경로

## Example Prompts

- "이 저장소에서 중국 주식 시장 의존성과 중국어 프롬프트를 제거하고 한국+미국 시장 기준으로 재구성해줘."
- "중국 검색과 중국 알림 채널을 모두 제거하고, 한국 뉴스는 네이버 API로, 미국 뉴스는 기존 글로벌 검색기로 유지하는 하네스를 적용해줘."
- "중국어 식별자를 영어로 바꾸고 KR+US 마이그레이션 범위를 감사한 뒤 실행 계획과 검증 게이트를 만들어줘."
