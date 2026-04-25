# KR+US Migration Harness Reinforcement Design

**Date:** 2026-04-25

## Goal

기존 KR+US 마이그레이션 하네스를 폐기하지 않고 보강한다. 목표는 현재 저장소에 남아 있는 중국 시장, 중국어 문구, 중국 검색, 중국 알림/문서 서비스 잔재를 반복적으로 감사하고 수정할 수 있는 실행 가능한 Codex 작업 체계를 완성하는 것이다.

## Confirmed Scope

- 한국 시장은 유지 및 강화한다: `pykrx`, KRX 거래일, KOSPI/KOSDAQ 지수 매핑, Naver 검색 API.
- 미국 시장은 유지한다: `yfinance`, US index mapping, 기존 글로벌 검색기.
- 중국 시장은 제거한다: `cn`, `hk`, A-share/HK stock routing, 중국 거래소/지수 가정.
- 중국 검색은 제거한다: Bocha, 중국 지역/언어 기본값, 중국어 검색 템플릿.
- 중국 서비스는 제거한다: Feishu, WeChat, DingTalk, PushPlus, ServerChan, Tushare, Baostock, PyTDX, Efinance.
- 사용자 노출 문구는 한국어/영어로 정리한다.
- 코드 식별자는 영어만 사용한다.

## Chosen Approach

선택지는 기존 하네스 보강이다. 이미 `.codex/harness`, `_workspace/kr-us-migration`, `docs/plans/2026-04-03-*` 산출물이 존재하므로 새 구조로 갈아엎지 않고 아래를 채운다.

- placeholder 감사 파일을 실제 스캔 결과 기반으로 갱신
- 워커별 파일 소유권을 더 명확히 분리
- 검증 체크리스트에 KR+US 보존 항목과 중국 제거 항목을 모두 포함
- 저장소 로컬 스킬을 현재 부분 마이그레이션 상태에 맞게 보강

## Architecture

하네스 구조는 오케스트레이터 기반 팬아웃/팬인 패턴을 유지한다.

1. `china-surface-auditor`가 읽기 전용으로 중국 표면을 감사한다.
2. 메인 오케스트레이터가 감사 결과를 세 워커 소유권으로 나눈다.
3. `market-search-migrator`는 시장/검색/데이터 공급자 경로를 맡는다.
4. `language-runtime-migrator`는 사용자 문구, 프롬프트, 로그, 식별자명을 맡는다.
5. `delivery-config-pruner`는 설정, 알림 채널, 문서를 맡는다.
6. `migration-verifier`는 정적 스캔과 핵심 테스트를 실행해 최종 보고서를 갱신한다.

## Current Signals

빠른 스캔 기준으로 이미 KR+US 요소는 존재한다.

- `README.md`는 KR+US 프로젝트로 설명한다.
- `data_provider/pykrx_fetcher.py`, `data_provider/kr_index_mapping.py`, `src/core/trading_calendar.py`가 한국 시장 경로를 제공한다.
- `data_provider/yfinance_fetcher.py`, `data_provider/us_index_mapping.py`가 미국 시장 경로를 유지한다.
- `bot/commands/status.py`에는 Naver 검색 설정 상태가 노출된다.

동시에 아래 중국 기반 표면이 아직 남아 있다.

- `src/search_service.py`의 Bocha 검색, 중국 SerpAPI 기본값, A-share/HK 검색 템플릿
- `data_provider/`의 중국 데이터 공급자와 `cn`/`hk` 라우팅
- `src/config.py`, `src/core/config_registry.py`, `src/notification.py`의 중국 알림/검색 설정
- `apps/dsa-web/src/`의 중국어 UI 문구와 중국 LLM 채널 기본값
- `docs/`, `tests/`, `bot/`, `api/`의 중국어 문구와 중국 시장 fixture

## Quality Gates

- 활성 코드 경로에서 `cn`/`hk` 기본값과 A-share/HK 라우팅이 제거되어야 한다.
- 한국 검색은 Naver API 설정과 테스트로 확인되어야 한다.
- 미국 검색과 `yfinance` 경로는 제거하지 않아야 한다.
- 중국 데이터 공급자는 활성 fallback 목록에서 제거되어야 한다.
- 중국 알림/문서 서비스는 설정 레지스트리, API schema, Web UI, 문서에서 제거되어야 한다.
- 사용자 노출 문구와 LLM 프롬프트는 한국어/영어만 남아야 한다.
- 검증은 정적 스캔, `py_compile`, KR/US 핵심 테스트로 재현 가능해야 한다.

## Non-Goals

- 이번 보강은 실제 마이그레이션 전체를 완료하지 않는다.
- 전역 `~/.codex/skills` 설치는 하지 않는다.
- 사용자 승인 없이 커밋하지 않는다.
