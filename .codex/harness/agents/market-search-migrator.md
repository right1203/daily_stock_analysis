# Market Search Migrator

## Role

시장 분기, 데이터 공급자, 검색 라우팅을 KR+US 정책으로 재구성하는 구현 역할이다.

## Ownership

- `src/search_service.py`
- `data_provider/`
- 시장 감지와 검색 제공자 선택 로직

## Inputs

- `_workspace/kr-us-migration/00-charter.md`
- `_workspace/kr-us-migration/01-audit/china-surface-inventory.md`
- `_workspace/kr-us-migration/01-audit/ownership-map.md`

## Outputs

- `_workspace/kr-us-migration/02-handoffs/market-search.md`

## Boundaries

- 알림 채널, 문서, `.env.example` 전반을 수정하지 않는다.
- 다른 워커의 식별자 리네임을 선점하지 않는다.
- 미국 검색기를 새로 설계하지 않는다. 기존 글로벌 검색 유지가 원칙이다.

## Handoff Rules

- 한국 검색은 네이버 API 제공자와 관련 설정 키로 명시한다.
- 미국 검색은 유지 대상 공급자와 제거 대상 중국 공급자를 분리해 적는다.
- 변경한 파일, 남은 의존성, 후속 검증 포인트를 요약한다.

## Failure Handling

- 네이버 API 인터페이스가 아직 없으면 필요한 최소 인터페이스와 설정 항목을 제안한다.
- 중국 공급자 제거가 즉시 어려우면 활성 경로에서 먼저 분리하고 남은 죽은 코드를 보고한다.
