# LLM 설정 가이드

이 문서는 KR/US 주식 분석 환경에서 AI 모델을 설정하는 방법을 설명합니다. 빠른 실행은 [README](../README.md)를 참고하세요.

## 설정 우선순위

LLM 설정은 아래 순서로 적용됩니다.

```text
LITELLM_CONFIG > LLM_CHANNELS > 단일 API Key
```

상위 방식이 설정되면 하위 방식은 사용하지 않습니다. 예를 들어 `LLM_CHANNELS`를 설정하면 `GEMINI_API_KEY` 같은 단일 Key 설정은 무시됩니다.

## 단일 모델 설정

가장 간단한 방식입니다. 사용할 서비스의 API Key를 `.env`에 입력합니다.

```bash
GEMINI_API_KEY=
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
```

모델을 명시하려면 LiteLLM 형식인 `provider/model`을 사용합니다.

```bash
LITELLM_MODEL=gemini/gemini-2.5-flash
LITELLM_FALLBACK_MODELS=openai/gpt-4o-mini,anthropic/claude-3-5-sonnet-20241022
```

## 채널 설정

여러 모델 또는 여러 API 엔드포인트를 분리해서 운영할 때 사용합니다.

```bash
LLM_CHANNELS=gemini,openai

LLM_GEMINI_API_KEYS=key1,key2
LLM_GEMINI_MODELS=gemini/gemini-2.5-flash

LLM_OPENAI_BASE_URL=https://api.openai.com/v1
LLM_OPENAI_API_KEY=
LLM_OPENAI_MODELS=gpt-4o-mini
```

`BASE_URL`이 있는 OpenAI 호환 채널은 모델 이름에 접두사를 붙이지 않아도 됩니다. 기본 제공 provider는 `gemini/gemini-2.5-flash`처럼 전체 이름을 쓰는 것을 권장합니다.

## YAML 설정

복잡한 라우팅, 배포별 모델 분리, 표준 LiteLLM 설정이 필요하면 YAML을 사용합니다.

```bash
LITELLM_CONFIG=./litellm_config.yaml
```

키는 파일에 직접 쓰지 말고 환경 변수로 참조하세요.

```yaml
api_key: "os.environ/OPENAI_API_KEY"
```

## Vision 모델

Web 설정의 이미지 종목 추출 기능은 Vision 모델을 사용합니다.

```bash
VISION_MODEL=gemini/gemini-2.0-flash
VISION_PROVIDER_PRIORITY=gemini,anthropic,openai
```

`VISION_MODEL`을 설정했다면 해당 provider의 API Key도 함께 설정해야 합니다.

## 검증

```bash
python test_env.py --config
python test_env.py --llm
```

`--config`는 설정 구조만 확인합니다. `--llm`은 실제 API를 호출하므로 네트워크와 사용량이 필요합니다.

## 문제 해결

| 증상 | 확인할 항목 |
|------|-------------|
| LLM이 설정되지 않음 | `LITELLM_CONFIG`, `LLM_CHANNELS`, 단일 API Key 중 하나가 있는지 확인 |
| 모델 이름 오류 | `provider/model` 형식인지 확인 |
| 이미지 추출 실패 | `VISION_MODEL`과 해당 API Key가 함께 설정됐는지 확인 |
| 요청 제한 | 여러 API Key 또는 fallback 모델 설정 |
| Web 설정과 `.env`가 다름 | 실제 실행 환경에 반영된 환경 변수를 확인 |
