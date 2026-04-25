import type { SystemConfigCategory } from '../types/systemConfig';

const categoryTitleMap: Record<SystemConfigCategory, string> = {
  base: '기본 설정',
  data_source: '데이터 및 검색',
  ai_model: 'AI 모델',
  notification: '알림 채널',
  system: '시스템 설정',
  agent: 'Agent 설정',
  backtest: '백테스트 설정',
  uncategorized: '기타',
};

const categoryDescriptionMap: Partial<Record<SystemConfigCategory, string>> = {
  base: '관심 종목과 기본 실행 값을 관리합니다.',
  data_source: 'KR/US 데이터 보조 설정과 뉴스 검색 키를 관리합니다.',
  ai_model: '모델 공급자, 모델명, 추론 파라미터를 관리합니다.',
  notification: 'Telegram, Email, Discord, Pushover, AstrBot, Custom Webhook 알림을 관리합니다.',
  system: '스케줄, 로그, 포트 등 시스템 설정을 관리합니다.',
  agent: 'Agent 모드, 스킬, 전략 설정을 관리합니다.',
  backtest: '백테스트 사용 여부, 평가 기간, 엔진 파라미터를 관리합니다.',
  uncategorized: '분류되지 않은 설정입니다.',
};

const fieldTitleMap: Record<string, string> = {
  STOCK_LIST: '관심 종목 목록',
  TAVILY_API_KEYS: 'Tavily API Keys',
  SERPAPI_API_KEYS: 'SerpAPI API Keys',
  BRAVE_API_KEYS: 'Brave API Keys',
  NAVER_API_KEYS: 'Naver API Keys',
  ENABLE_REALTIME_TECHNICAL_INDICATORS: '장중 실시간 기술 지표',
  LITELLM_MODEL: '기본 모델',
  LITELLM_FALLBACK_MODELS: '대체 모델',
  LITELLM_CONFIG: 'LiteLLM 설정 파일',
  LLM_CHANNELS: 'LLM 채널 목록',
  AIHUBMIX_KEY: 'AIHubmix Key',
  DEEPSEEK_API_KEY: 'DeepSeek API Key',
  GEMINI_API_KEY: 'Gemini API Key',
  GEMINI_MODEL: 'Gemini 모델',
  GEMINI_TEMPERATURE: 'Gemini 온도',
  OPENAI_API_KEY: 'OpenAI API Key',
  OPENAI_BASE_URL: 'OpenAI Base URL',
  OPENAI_MODEL: 'OpenAI 모델',
  ASTRBOT_URL: 'AstrBot URL',
  ASTRBOT_TOKEN: 'AstrBot Token',
  REPORT_SUMMARY_ONLY: '분석 결과 요약만 전송',
  SCHEDULE_TIME: '예약 실행 시간',
  HTTP_PROXY: 'HTTP 프록시',
  LOG_LEVEL: '로그 레벨',
  WEBUI_PORT: 'WebUI 포트',
  AGENT_MODE: 'Agent 모드 사용',
  AGENT_MAX_STEPS: 'Agent 최대 단계',
  AGENT_SKILLS: 'Agent 활성 스킬',
  AGENT_STRATEGY_DIR: 'Agent 전략 디렉터리',
  BACKTEST_ENABLED: '백테스트 사용',
  BACKTEST_EVAL_WINDOW_DAYS: '백테스트 평가 기간(거래일)',
  BACKTEST_MIN_AGE_DAYS: '백테스트 최소 경과일',
  BACKTEST_ENGINE_VERSION: '백테스트 엔진 버전',
  BACKTEST_NEUTRAL_BAND_PCT: '백테스트 중립 구간 임계값(%)',
};

const fieldDescriptionMap: Record<string, string> = {
  STOCK_LIST: '쉼표로 종목 코드를 구분합니다. 예: 005930,AAPL.',
  TAVILY_API_KEYS: '뉴스 검색용 Tavily 키입니다. 쉼표로 여러 키를 입력할 수 있습니다.',
  SERPAPI_API_KEYS: '뉴스 검색용 SerpAPI 키입니다. 쉼표로 여러 키를 입력할 수 있습니다.',
  BRAVE_API_KEYS: '뉴스 검색용 Brave Search 키입니다. 쉼표로 여러 키를 입력할 수 있습니다.',
  NAVER_API_KEYS: 'Naver 검색 키 쌍입니다. client_id:client_secret 형식으로 입력합니다.',
  ENABLE_REALTIME_TECHNICAL_INDICATORS: '장중 분석 시 실시간 가격으로 MA5/MA10/MA20과 추세를 계산합니다.',
  LITELLM_MODEL: '기본 모델입니다. provider/model 형식으로 입력합니다. 예: gemini/gemini-2.5-flash.',
  LITELLM_FALLBACK_MODELS: '기본 모델 실패 시 순서대로 시도할 대체 모델 목록입니다.',
  LITELLM_CONFIG: 'LiteLLM YAML 설정 파일 경로입니다. 고급 설정이며 가장 높은 우선순위를 가집니다.',
  LLM_CHANNELS: '채널 이름 목록입니다. 위의 채널 편집기에서 관리하는 것을 권장합니다.',
  AIHUBMIX_KEY: 'AIHubmix 통합 API 키입니다. 기본 Base URL은 aihubmix.com/v1입니다.',
  DEEPSEEK_API_KEY: 'DeepSeek 공식 API 키입니다. 입력하면 deepseek-chat 모델을 자동으로 사용할 수 있습니다.',
  GEMINI_API_KEY: 'Gemini 호출에 사용할 API 키입니다.',
  GEMINI_MODEL: 'Gemini 분석 모델명을 설정합니다.',
  GEMINI_TEMPERATURE: '모델 출력의 무작위성을 제어합니다. 일반 범위는 0.0부터 2.0까지입니다.',
  OPENAI_API_KEY: 'OpenAI 호환 서비스 호출에 사용할 API 키입니다.',
  OPENAI_BASE_URL: 'OpenAI 호환 API 주소입니다. 예: https://api.deepseek.com/v1.',
  OPENAI_MODEL: 'OpenAI 호환 모델명입니다. 예: gpt-4o-mini, deepseek-chat.',
  ASTRBOT_URL: 'AstrBot 알림을 전송할 Webhook 또는 API 엔드포인트 URL입니다.',
  ASTRBOT_TOKEN: 'AstrBot 인증이 필요한 경우 사용할 액세스 토큰입니다.',
  REPORT_SUMMARY_ONLY: '종목별 상세 없이 분석 결과 요약만 전송합니다.',
  SCHEDULE_TIME: '매일 예약 작업 실행 시간입니다. HH:MM 형식입니다.',
  HTTP_PROXY: '네트워크 프록시 주소입니다. 필요하지 않으면 비워둡니다.',
  LOG_LEVEL: '로그 출력 레벨을 설정합니다.',
  WEBUI_PORT: 'WebUI 서버 수신 포트입니다.',
  AGENT_MODE: '주식 분석에 ReAct Agent를 사용할지 설정합니다.',
  AGENT_MAX_STEPS: 'Agent가 사고하고 도구를 호출할 수 있는 최대 단계 수입니다.',
  AGENT_SKILLS: '활성화할 스킬 또는 전략 목록입니다. 예: trend_following,value_investing.',
  AGENT_STRATEGY_DIR: 'Agent 전략 YAML 파일을 저장하는 디렉터리 경로입니다.',
  BACKTEST_ENABLED: '백테스트 기능 사용 여부입니다(true/false).',
  BACKTEST_EVAL_WINDOW_DAYS: '백테스트 평가 기간입니다. 단위는 거래일입니다.',
  BACKTEST_MIN_AGE_DAYS: '이 일수보다 오래된 분석 기록만 백테스트합니다.',
  BACKTEST_ENGINE_VERSION: '결과 버전을 구분하기 위한 백테스트 엔진 버전입니다.',
  BACKTEST_NEUTRAL_BAND_PCT: '중립 구간 임계값입니다. 예: 2는 -2%부터 +2%까지를 의미합니다.',
};

export function getCategoryTitleZh(category: SystemConfigCategory, fallback?: string): string {
  return categoryTitleMap[category] || fallback || category;
}

export function getCategoryDescriptionZh(category: SystemConfigCategory, fallback?: string): string {
  return categoryDescriptionMap[category] || fallback || '';
}

export function getFieldTitleZh(key: string, fallback?: string): string {
  return fieldTitleMap[key] || fallback || key;
}

export function getFieldDescriptionZh(key: string, fallback?: string): string {
  return fieldDescriptionMap[key] || fallback || '';
}
