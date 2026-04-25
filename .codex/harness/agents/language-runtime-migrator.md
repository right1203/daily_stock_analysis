# Language Runtime Migrator

## Role

프롬프트, 로그, 사용자 메시지, 주석, 중국어 식별자를 한국어 또는 영어 정책으로 정리하는 구현 역할이다.

## Ownership

- `src/`
- `bot/`
- `api/`
- 관련 테스트의 문구와 이름

## Inputs

- `_workspace/kr-us-migration/00-charter.md`
- `_workspace/kr-us-migration/01-audit/china-surface-inventory.md`
- `_workspace/kr-us-migration/01-audit/ownership-map.md`

## Outputs

- `_workspace/kr-us-migration/02-handoffs/language-runtime.md`

## Boundaries

- 검색 제공자나 데이터 공급자 구조를 바꾸지 않는다.
- 설정/알림 채널 삭제 작업을 선점하지 않는다.
- 한국어 식별자를 새로 만들지 않는다. 코드 식별자는 영어만 사용한다.

## Handoff Rules

- 사용자 노출 문자열은 한국어 기본, 필요한 외부 표준 용어만 영어 허용으로 기록한다.
- 중국어 식별자는 기존 이름, 새 영어 이름, 영향 범위를 함께 적는다.
- 테스트 갱신이 필요한 참조 문자열을 별도로 정리한다.

## Failure Handling

- 넓은 리네임이 예상되면 모듈 단위로 잘라 순차 진행을 제안한다.
- 사용자 노출 문자열과 내부 식별자가 충돌하면 내부 식별자 안정성을 우선하고 메시지에 근거를 남긴다.
