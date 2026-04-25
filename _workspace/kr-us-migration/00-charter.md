# KR+US Migration Charter

## Mission

이 저장소를 중국/HK 시장 중심 분석 시스템에서 한국+미국 시장 중심 분석 시스템으로 완전 전환한다.
전환 방식은 complete-removal mode이며, 중국/HK 관련 시장, 데이터, 검색, 전달, 설정, UI, 문서, 테스트 표면은
호환성 shim 없이 제거한다.

## Fixed Decisions

- complete-removal mode를 적용한다. deprecated wrapper, no-op sender, hidden compatibility flag, legacy alias를 남기지 않는다.
- 한국 시장 검색은 네이버 API를 사용한다.
- 미국 시장 검색은 기존 글로벌 검색기를 유지한다.
- 한국 데이터 positive control은 `pykrx`, KRX calendar, KR index mapping이다.
- 미국 데이터 positive control은 `yfinance`, US index mapping이다.
- 중국/HK 시장과 중국 기반 검색은 제거한다.
- 중국 서비스와 중국 알림 채널은 제거한다.
- 코드 식별자, 주석, docstring은 영어로 정리한다.
- 사용자 노출 문구는 한국어를 기본으로 한다. API명, 제품명, 종목명 등 고유명사는 필요한 경우 영어를 유지할 수 있다.

## Removal Targets

- Markets: `cn`, `hk`, A-share, HK stock, 중국/HK 거래소와 지수 전제
- Search: `Bocha`, 중국 지역/언어 기본값, 중국 기반 검색 가정
- Data providers: `Akshare`, `Tushare`, `Baostock`, `PyTDX`, `Efinance`
- Delivery: `Feishu`, `WeChat`, `DingTalk`, `PushPlus`, `ServerChan`
- Config/UI/docs/tests: 제거 대상 기능을 노출하거나 검증하는 모든 활성 표면

## Constraints

- 기존 사용자 변경은 되돌리지 않는다.
- 커밋은 사용자 승인 전 수행하지 않는다.
- 코드 내부 표현은 영어로 작성한다.
- 사용자 표면은 한국어 중심으로 작성한다.
- 하네스 산출물은 `.codex/harness/`와 `_workspace/kr-us-migration/` 아래에 남긴다.

## Success Criteria

- 중국/HK 시장, 데이터 공급자, 검색 공급자, 전달 채널, 설정 키, UI 라벨, 문서, 테스트 잔재가 활성 경로에서 제거된다.
- 제거 대상은 호환성 shim 없이 사라진다.
- KR 검색은 네이버 API로 연결된다.
- US 검색은 기존 글로벌 검색기로 유지된다.
- KR 데이터는 `pykrx`, KRX calendar, KR index mapping을 유지한다.
- US 데이터는 `yfinance`, US index mapping을 유지한다.
- `cn`/`hk` 기본값과 시장 분기가 제거된다.
- 검증 체크리스트의 핵심 명령이 재현 가능하다.
