<div align="center">

# 📈 주식 AI 분석 시스템

[![GitHub stars](https://img.shields.io/github/stars/ZhuLinsen/daily_stock_analysis?style=social)](https://github.com/ZhuLinsen/daily_stock_analysis/stargazers)
[![CI](https://github.com/ZhuLinsen/daily_stock_analysis/actions/workflows/ci.yml/badge.svg)](https://github.com/ZhuLinsen/daily_stock_analysis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Ready-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/)

> 🤖 AI 대형 모델 기반 KOSPI/KOSDAQ/미국 주식 관심 종목 지능형 분석 시스템. 매일 자동 분석 후 「의사결정 대시보드」를 WeChat/Feishu/Telegram/이메일로 푸시

[**기능 특징**](#-기능-특징) · [**빠른 시작**](#-빠른-시작) · [**푸시 예시**](#-푸시-예시) · [**완전 가이드**](docs/full-guide.md) · [**자주 묻는 질문**](docs/FAQ.md) · [**업데이트 로그**](docs/CHANGELOG.md)

한국어 | [English](docs/README_EN.md) | [繁體中文](docs/README_CHT.md)

</div>

## 💖 스폰서 (Sponsors)
<div align="center">
  <a href="https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis" target="_blank">
    <img src="./sources/serpapi_banner_zh.png" alt="검색 엔진의 실시간 금융 뉴스 데이터를 손쉽게 수집 - SerpApi" height="160">
  </a>
</div>
<br>


## ✨ 기능 특징

| 모듈 | 기능 | 설명 |
|------|------|------|
| AI | 의사결정 대시보드 | 핵심 결론 한 줄 요약 + 정확한 매수/매도 가격 + 체크리스트 |
| 분석 | 다차원 분석 | 기술적 분석(장중 실시간 MA/정배열) + 수급 분포 + 뉴스 정보 + 실시간 시세 |
| 시장 | 글로벌 시장 | KOSPI/KOSDAQ 한국 주식 및 미국 주식·지수(SPX, DJI, IXIC 등) 지원 |
| 전략 | 시장 전략 시스템 | 한국 주식 「3단계 복기 전략」과 미국 주식 「Regime Strategy」 내장. 공격/균형/방어 또는 risk-on/neutral/risk-off 계획 출력. "참고용이며 투자 조언이 아닙니다" 안내 포함 |
| 복기 | 시장 복기 | 매일 시장 개요, 섹터 등락; kr(한국 주식)/us(미국 주식)/both(둘 다) 전환 지원 |
| 이미지 인식 | 이미지로 추가 | 관심 종목 스크린샷 업로드 시 Vision LLM이 자동으로 종목 코드 추출, 한 번에 모니터링 목록 추가 |
| 백테스트 | AI 백테스트 검증 | 과거 분석 정확도 자동 평가, 방향 승률·익절/손절 적중률 |
| **Agent 종목 문의** | **전략 대화** | **다중 턴 전략 Q&A, 이동평균 골든크로스/채널 이론/파동 등 11가지 내장 전략, Web/Bot/API 전체 지원** |
| 푸시 | 다채널 알림 | WeChat, Feishu, Telegram, DingTalk, 이메일, Pushover |
| 자동화 | 정시 실행 | GitHub Actions 정시 실행, 서버 불필요 |

### 기술 스택 및 데이터 소스

| 유형 | 지원 |
|------|------|
| AI 모델 | [AIHubMix](https://aihubmix.com/?aff=CfMq), Gemini, OpenAI 호환, DeepSeek, Qwen, Claude 등([LiteLLM](https://github.com/BerriAI/litellm)을 통해 통합 호출, 다중 Key 부하 분산 지원) |
| 시세 데이터 | pykrx, YFinance |
| 뉴스 검색 | Tavily, SerpAPI, Bocha, Brave |

> 참고: 미국 주식 과거 데이터 및 실시간 시세는 YFinance를 통해 통합 제공하여 수정 주가 일관성 보장

### 내장 매매 원칙

| 규칙 | 설명 |
|------|------|
| 고점 추격 금지 | 이격률이 임계값 초과 시(기본 5%, 설정 가능) 자동 위험 경고; 강세 추세 종목은 자동 완화 |
| 추세 매매 | MA5 > MA10 > MA20 정배열 |
| 정확한 가격대 | 매수가, 손절가, 목표가 |
| 체크리스트 | 각 조건을 「충족 / 주의 / 미충족」으로 표시 |
| 뉴스 유효 기간 | 뉴스 최대 유효 기간 설정 가능(기본 3일), 오래된 정보 사용 방지 |

## 🚀 빠른 시작

### 방법 1: GitHub Actions (권장)

> 5분 만에 배포 완료, 비용 0원, 서버 불필요.


#### 1. 저장소 Fork

오른쪽 상단 `Fork` 버튼 클릭 (Star⭐ 도 눌러주시면 감사합니다)

#### 2. Secrets 설정

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

**AI 모델 설정 (최소 하나 설정 필수)**

> 상세 설정 방법은 [LLM 설정 가이드](docs/LLM_CONFIG_GUIDE.md) 참조 (3단계 설정, 채널 모드, Vision, Agent, 트러블슈팅). 고급 사용자는 `LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS` 또는 `LLM_CHANNELS` 다중 채널 모드 설정 가능.

> 💡 **[AIHubMix](https://aihubmix.com/?aff=CfMq) 추천**: Key 하나로 Gemini, GPT, Claude, DeepSeek 등 글로벌 주요 모델 사용 가능. VPN 불필요. 무료 모델(glm-5, gpt-4o-free 등) 포함. 유료 모델은 고안정성·무제한 동시 처리. 본 프로젝트 사용자는 **10% 충전 할인** 혜택.

| Secret 이름 | 설명 | 필수 여부 |
|------------|------|:----:|
| `AIHUBMIX_KEY` | [AIHubMix](https://aihubmix.com/?aff=CfMq) API Key, 하나의 Key로 전체 모델 전환 사용, 무료 모델 사용 가능 | 선택 |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/)에서 무료 Key 발급(VPN 필요) | 선택 |
| `ANTHROPIC_API_KEY` | [Anthropic Claude](https://console.anthropic.com/) API Key | 선택 |
| `ANTHROPIC_MODEL` | Claude 모델 (예: `claude-3-5-sonnet-20241022`) | 선택 |
| `OPENAI_API_KEY` | OpenAI 호환 API Key (DeepSeek, Qwen 등 지원) | 선택 |
| `OPENAI_BASE_URL` | OpenAI 호환 API 주소 (예: `https://api.deepseek.com/v1`) | 선택 |
| `OPENAI_MODEL` | 모델 이름 (예: `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, `gpt-5.2`) | 선택 |
| `OPENAI_VISION_MODEL` | 이미지 인식 전용 모델 (일부 서드파티 모델은 이미지 미지원; 미입력 시 `OPENAI_MODEL` 사용) | 선택 |

> 참고: AI 우선순위 Gemini > Anthropic > OpenAI(AIHubmix 포함), 최소 하나 설정 필수. `AIHUBMIX_KEY`는 `OPENAI_BASE_URL` 별도 설정 불필요, 시스템이 자동 적용. 이미지 인식은 Vision 지원 모델 필요. DeepSeek 추론 모드(deepseek-reasoner, deepseek-r1, qwq, deepseek-chat)는 모델명으로 자동 인식, 추가 설정 불필요.

<details>
<summary><b>알림 채널 설정</b> (클릭하여 펼치기, 최소 하나 설정 필수)</summary>


| Secret 이름 | 설명 | 필수 여부 |
|------------|------|:----:|
| `WECHAT_WEBHOOK_URL` | WeChat Webhook URL | 선택 |
| `FEISHU_WEBHOOK_URL` | Feishu Webhook URL | 선택 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token (@BotFather에서 발급) | 선택 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 선택 |
| `TELEGRAM_MESSAGE_THREAD_ID` | Telegram Topic ID (서브 토픽으로 전송 시 사용) | 선택 |
| `EMAIL_SENDER` | 발신 이메일 (예: `xxx@gmail.com`) | 선택 |
| `EMAIL_PASSWORD` | 이메일 앱 비밀번호 (로그인 비밀번호 아님) | 선택 |
| `EMAIL_RECEIVERS` | 수신 이메일 (여러 개는 쉼표로 구분, 비워두면 본인에게 발송) | 선택 |
| `EMAIL_SENDER_NAME` | 이메일 발신자 표시 이름 (기본값: daily_stock_analysis 주식 분석 어시스턴트) | 선택 |
| `STOCK_GROUP_N` / `EMAIL_GROUP_N` | 종목 그룹별 다른 이메일로 전송 (예: `STOCK_GROUP_1=005930,000660` `EMAIL_GROUP_1=user1@example.com`) | 선택 |
| `PUSHPLUS_TOKEN` | PushPlus Token ([발급 주소](https://www.pushplus.plus)) | 선택 |
| `PUSHPLUS_TOPIC` | PushPlus 그룹 코드 (다수 전송 시 그룹 전체 구독자에게 발송) | 선택 |
| `SERVERCHAN3_SENDKEY` | Server酱³ Sendkey ([발급 주소](https://sc3.ft07.com/), 모바일 앱 푸시 서비스) | 선택 |
| `CUSTOM_WEBHOOK_URLS` | 커스텀 Webhook (DingTalk 등 지원, 여러 개는 쉼표로 구분) | 선택 |
| `CUSTOM_WEBHOOK_BEARER_TOKEN` | 커스텀 Webhook Bearer Token (인증이 필요한 Webhook에 사용) | 선택 |
| `WEBHOOK_VERIFY_SSL` | Webhook HTTPS 인증서 검증 (기본 true). false로 설정 시 자체 서명 인증서 지원. 경고: 비활성화는 심각한 보안 위험, 신뢰할 수 있는 내부망에서만 사용 | 선택 |
| `SINGLE_STOCK_NOTIFY` | 개별 종목 즉시 알림 모드: `true`로 설정 시 종목 분석 완료 즉시 푸시 | 선택 |
| `REPORT_TYPE` | 보고서 유형: `simple`(간략) 또는 `full`(전체), Docker 환경에서는 `full` 권장 | 선택 |
| `REPORT_SUMMARY_ONLY` | 분석 결과 요약만 전송: `true`로 설정 시 개별 종목 상세 없이 요약만 푸시 | 선택 |
| `ANALYSIS_DELAY` | 개별 종목 분석과 시장 복기 사이의 지연 시간(초), API 요청 제한 방지, 예: `10` | 선택 |
| `MERGE_EMAIL_NOTIFICATION` | 개별 종목과 시장 복기 통합 발송 (기본 false), 이메일 수 감소 | 선택 |
| `MARKDOWN_TO_IMAGE_CHANNELS` | Markdown을 이미지로 변환하여 전송할 채널 (쉼표 구분): `telegram,wechat,custom,email` | 선택 |
| `MARKDOWN_TO_IMAGE_MAX_CHARS` | 이 길이 초과 시 이미지 변환 안 함, 초대형 이미지 방지 (기본 `15000`) | 선택 |
| `MD2IMG_ENGINE` | 이미지 변환 엔진: `wkhtmltoimage`(기본) 또는 `markdown-to-file`(이모지 지원 개선) | 선택 |

> 최소 하나의 채널 설정 필수, 여러 개 설정 시 동시 발송. 이미지 전송 및 엔진 설치 상세 내용은 [완전 가이드](docs/full-guide.md) 참조

</details>

**기타 설정**

| Secret 이름 | 설명 | 필수 여부 |
|------------|------|:----:|
| `STOCK_LIST` | 관심 종목 코드, 예: `005930,000660,AAPL,TSLA` | ✅ |
| `TAVILY_API_KEYS` | [Tavily](https://tavily.com/) 검색 API (뉴스 검색) | 권장 |
| `SERPAPI_API_KEYS` | [SerpAPI](https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis) 전채널 검색 | 선택 |
| `BOCHA_API_KEYS` | [Bocha Search](https://open.bocha.cn/) Web Search API (다국어 검색 최적화, AI 요약 지원, 여러 Key는 쉼표로 구분) | 선택 |
| `BRAVE_API_KEYS` | [Brave Search](https://brave.com/search/api/) API (프라이버시 우선, 미국 주식 최적화, 여러 Key는 쉼표로 구분) | 선택 |
| `TUSHARE_TOKEN` | [Tushare Pro](https://tushare.pro/weborder/#/login?reg=834638) Token | 선택 |
| `PREFETCH_REALTIME_QUOTES` | 실시간 시세 사전 조회 스위치: `false`로 설정 시 전시장 사전 조회 비활성화 (기본 `true`) | 선택 |
| `WECHAT_MSG_TYPE` | WeChat 메시지 유형, 기본 markdown, text 유형도 지원 | 선택 |
| `NEWS_MAX_AGE_DAYS` | 뉴스 최대 유효 기간(일), 기본 3, 오래된 정보 사용 방지 | 선택 |
| `BIAS_THRESHOLD` | 이격률 임계값(%), 기본 5.0, 초과 시 고점 추격 경고; 강세 추세 종목 자동 완화 | 선택 |
| `AGENT_MODE` | Agent 전략 문의 모드 활성화 (`true`/`false`, 기본 false) | 선택 |
| `AGENT_SKILLS` | 활성화할 전략 (쉼표 구분), `all`로 전체 11개 활성화; 미설정 시 기본 4개, `.env.example` 참조 | 선택 |
| `AGENT_MAX_STEPS` | Agent 최대 추론 단계 수 (기본 10) | 선택 |
| `AGENT_STRATEGY_DIR` | 커스텀 전략 디렉토리 (기본 내장 `strategies/`) | 선택 |
| `TRADING_DAY_CHECK_ENABLED` | 거래일 확인 (기본 `true`): 비거래일 실행 건너뜀; `false` 또는 `--force-run`으로 강제 실행 | 선택 |

#### 3. Actions 활성화

`Actions` 탭 → `I understand my workflows, go ahead and enable them`

#### 4. 수동 테스트

`Actions` → `매일 주식 분석` → `Run workflow` → `Run workflow`

#### 완료

기본적으로 매 **평일 18:00(KST, 한국 표준시)**에 자동 실행. 수동 트리거도 가능. 기본적으로 비거래일(한국/미국 공휴일 포함)에는 실행하지 않음.

> 💡 **거래일 확인 건너뛰기 두 가지 방법:**
> | 방법 | 설정 방식 | 적용 범위 | 적합한 상황 |
> |------|----------|----------|----------|
> | `TRADING_DAY_CHECK_ENABLED=false` | 환경 변수/Secrets | 전역, 장기 유효 | 테스트 환경, 장기 비활성화 |
> | `force_run` (UI 체크) | Actions 수동 트리거 시 선택 | 단일 실행 | 비거래일 임시 1회 실행 |
>
> - **환경 변수 방식**: `.env` 또는 GitHub Secrets에 설정, 모든 실행 방식(정시 트리거, 수동 트리거, 로컬 실행)에 영향
> - **UI 체크 방식**: GitHub Actions 수동 트리거 시에만 표시, 정시 작업에 영향 없음, 임시 필요에 적합

### 방법 2: 로컬 실행 / Docker 배포

```bash
# 저장소 클론
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git && cd daily_stock_analysis

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env && vim .env

# 분석 실행
python main.py
```

> Docker 배포, 정시 작업 설정은 [완전 가이드](docs/full-guide.md) 참조
> 데스크탑 클라이언트 패키징은 [데스크탑 패키징 안내](docs/desktop-package.md) 참조

## 📱 푸시 예시

### 의사결정 대시보드
```
🎯 2026-02-08 의사결정 대시보드
총 3개 종목 분석 | 🟢매수:0 🟡관망:2 🔴매도:1

📊 분석 결과 요약
⚪ 삼성전자(005930): 관망 | 점수 65 | 상승 전망
⚪ SK하이닉스(000660): 관망 | 점수 48 | 박스권
🟡 POSCO홀딩스(005490): 매도 | 점수 35 | 하락 전망

⚪ 삼성전자 (005930)
📰 주요 정보 요약
💭 뉴스 심리: 시장이 AI 반도체 성장성과 실적 호조에 주목, 심리는 긍정적이나 단기 차익 실현 매물과 외국인 순매도 압력 소화 필요.
📊 실적 전망: 뉴스 기반, 2025년 3분기 누적 실적 전년 대비 대폭 성장, 펀더멘털 견고하여 주가 지지.

🚨 리스크 경고:

리스크1: 2월 5일 외국인 순매도 3,630억 원, 단기 매도 압력 주의.
리스크2: 수급 집중도 35.15%로 물량 분산, 추가 상승 저항 가능성.
리스크3: 미국발 반도체 수출 규제 관련 이슈 지속, 모니터링 필요.
✨ 긍정적 촉매:

호재1: AI 서버·HBM 핵심 공급사로 AI 산업 성장 수혜.
호재2: 2025년 3분기 누적 영업이익 전년 대비 407% 급증, 실적 강세.
📢 최신 동향: 【최신 소식】삼성전자가 AI 메모리·파운드리 분야에서 글로벌 선두 입지 강화 중. 2월 5일 외국인 순매도 3,630억 원, 이후 자금 흐름 모니터링 필요.

---
생성 시간: 18:00
```

### 시장 복기
```
🎯 2026-01-10 시장 복기

📊 주요 지수
- 코스피: 2,650.12 (🟢+0.85%)
- 코스닥: 850.36 (🟢+1.02%)

📈 시장 현황
상승: 1,320 | 하락: 580 | 상한가: 45 | 하한가: 2

🔥 섹터 동향
상승 주도: 반도체, 2차전지, 인터넷
하락: 보험, 항공, 태양광
```
## ⚙️ 설정 안내

> 📖 전체 환경 변수, 정시 작업 설정은 [완전 설정 가이드](docs/full-guide.md) 참조


## 🖥️ Web 인터페이스

![img.png](sources/fastapi_server.png)

설정 관리, 작업 모니터링, 수동 분석 기능이 포함된 완전한 인터페이스.

**선택적 비밀번호 보호**: `.env`에서 `ADMIN_AUTH_ENABLED=true` 설정으로 Web 로그인 활성화. 최초 접속 시 웹페이지에서 초기 비밀번호 설정, Settings의 API 키 등 민감한 설정 보호. 상세 내용은 [완전 가이드](docs/full-guide.md) 참조.

### 이미지로 종목 추가

**설정 → 기본 설정**에서 「이미지로 추가」 블록을 찾아 관심 종목 스크린샷(앱 보유 화면, 시세 목록 스크린샷 등)을 드래그 앤 드롭하거나 선택하면, 시스템이 Vision AI로 자동으로 종목 코드를 인식하여 관심 목록에 병합.

**설정 및 제한**:
- `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` 또는 `OPENAI_API_KEY` 중 최소 하나 설정 필요 (Vision 지원 모델)
- JPG, PNG, WebP, GIF 지원, 단일 파일 최대 5MB; 요청 타임아웃 60초

**API 호출**: `POST /api/v1/stocks/extract-from-image`, 폼 필드 `file`, 반환값 `{ "codes": ["005930", "000660", ...] }`. 상세 내용은 [완전 가이드](docs/full-guide.md) 참조.

### 🤖 Agent 종목 전략 문의

`.env`에서 `AGENT_MODE=true` 설정 후 서비스 시작, `/chat` 페이지에 접속하여 다중 턴 전략 Q&A 시작.

- **전략 선택**: 이동평균 골든크로스, 채널 이론, 파동 이론, 상승 추세 등 11가지 내장 전략
- **자연어 질문**: 예: 「파동 이론으로 005930 분석해줘」, Agent가 자동으로 실시간 시세·캔들차트·기술지표·뉴스 도구 호출
- **스트리밍 진행 피드백**: AI 사고 경로 실시간 표시 (시세 조회 → 기술 분석 → 뉴스 검색 → 결론 생성)
- **다중 턴 대화**: 후속 질문 컨텍스트 지원, 세션 기록 영구 저장
- **Bot 지원**: `/ask <code> [strategy]` 명령으로 전략 분석 트리거
- **커스텀 전략**: `strategies/` 디렉토리에 YAML 파일 추가만으로 전략 등록, 코딩 불필요

> **참고**: Agent 모드는 외부 LLM(Gemini/OpenAI 등)에 의존하며, 각 대화 시 API 호출 비용이 발생합니다. 비 Agent 모드(`AGENT_MODE=false` 또는 미설정)의 정상 동작에는 영향 없음.

### 시작 방법

1. **서비스 시작** (기본적으로 프론트엔드 자동 빌드)
   ```bash
   python main.py --webui       # Web 인터페이스 시작 + 정시 분석 실행
   python main.py --webui-only  # Web 인터페이스만 시작
   ```
   시작 시 `apps/dsa-web`에서 자동으로 `npm install && npm run build` 실행.
   자동 빌드를 비활성화하려면 `WEBUI_AUTO_BUILD=false` 설정 후 수동 실행:
   ```bash
   cd ./apps/dsa-web
   npm install && npm run build
   cd ../..
   ```

`http://127.0.0.1:8000`에 접속하여 사용.

> `python main.py --serve` 도 동일한 명령으로 사용 가능

## 🗺️ Roadmap

지원 기능 및 향후 계획 확인: [업데이트 로그](docs/CHANGELOG.md)

> 제안 사항이 있으신가요? [Issue 제출](https://github.com/ZhuLinsen/daily_stock_analysis/issues) 환영합니다


---

## ☕ 프로젝트 지원

본 프로젝트가 도움이 되셨다면, 지속적인 유지 보수와 개발을 위한 후원을 환영합니다. 감사합니다 🙏
후원 시 연락처를 남겨주시면 감사히 확인하겠습니다.

| 支付宝 (Alipay) | 微信支付 (WeChat) | Ko-fi |
| :---: | :---: | :---: |
| <img src="./sources/alipay.jpg" width="200" alt="Alipay"> | <img src="./sources/wechatpay.jpg" width="200" alt="WeChat Pay"> | <a href="https://ko-fi.com/mumu157" target="_blank"><img src="./sources/ko-fi.png" width="200" alt="Ko-fi"></a> |

---

## 🤝 기여

Issue 및 Pull Request 환영합니다!

상세 내용은 [기여 가이드](docs/CONTRIBUTING.md) 참조

### 로컬 게이트 (먼저 실행 권장)

```bash
pip install -r requirements.txt
pip install flake8 pytest
./scripts/ci_gate.sh
```

프론트엔드(`apps/dsa-web`) 수정 시:

```bash
cd apps/dsa-web
npm ci
npm run lint
npm run build
```

## 📄 License
[MIT License](LICENSE) © 2026 ZhuLinsen

본 프로젝트를 사용하거나 이를 기반으로 2차 개발을 하신다면,
README 또는 문서에 출처를 명시하고 본 저장소 링크를 첨부해 주시면 매우 감사하겠습니다.
이는 프로젝트의 지속적인 유지 보수와 커뮤니티 발전에 도움이 됩니다.

## 📬 연락 및 협업
- GitHub Issues: [Issue 제출](https://github.com/ZhuLinsen/daily_stock_analysis/issues)
- 협업 이메일: zhuls345@gmail.com

## ⭐ Star History
**도움이 되셨다면 ⭐ Star를 눌러 응원해 주세요!**

<a href="https://star-history.com/#ZhuLinsen/daily_stock_analysis&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=ZhuLinsen/daily_stock_analysis&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=ZhuLinsen/daily_stock_analysis&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=ZhuLinsen/daily_stock_analysis&type=Date" />
 </picture>
</a>

## ⚠️ 면책 조항

본 프로젝트는 학습 및 연구 목적으로만 제공되며, 어떠한 투자 조언도 구성하지 않습니다. 주식 시장에는 위험이 따르며, 투자는 신중하게 결정하시기 바랍니다. 작성자는 본 프로젝트 사용으로 인해 발생하는 어떠한 손실에도 책임을 지지 않습니다.

---
