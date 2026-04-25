# KR+US Migration Charter

## Mission

이 저장소를 중국 시장 중심 분석 시스템에서 한국+미국 시장 중심 분석 시스템으로 재구성한다.

## Fixed Decisions

- 한국 시장 검색은 네이버 API를 사용한다.
- 미국 시장 검색은 기존 글로벌 검색기를 유지한다.
- 중국 시장과 중국 기반 검색은 제거한다.
- 중국 서비스와 중국 알림 채널은 제거한다.
- 중국어 식별자는 영어로 변경한다.
- 사용자 노출 문구는 한국어 또는 영어만 허용한다.

## Removal Targets

- Markets: `cn`, `hk`, A-share, 중국 거래소/지수 전제
- Search: `Bocha`, 중국 지역/언어 기본값, 중국 기반 검색 가정
- Data providers: `Tushare`, `Baostock`, `PyTDX`, `Efinance`
- Delivery: `Feishu`, `WeChat`, `DingTalk`, `PushPlus`, `ServerChan`

## Constraints

- 기존 사용자 변경은 되돌리지 않는다.
- 커밋은 사용자 승인 전 수행하지 않는다.
- 코드 식별자는 영어만 사용한다.
- 하네스 산출물은 `.codex/harness/`와 `_workspace/kr-us-migration/` 아래에 남긴다.

## Success Criteria

- 중국어 문자열과 중국 서비스 잔재가 활성 경로에서 제거된다.
- KR 검색은 네이버 API로 연결된다.
- US 검색은 기존 글로벌 검색기로 유지된다.
- `cn`/`hk` 기본값과 시장 분기가 제거된다.
- 검증 체크리스트의 핵심 명령이 재현 가능하다.
