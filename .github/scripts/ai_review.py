#!/usr/bin/env python3
"""
AI code review script used by GitHub Actions PR Review workflow.
"""
import json
import os
import subprocess
import traceback


MAX_DIFF_LENGTH = 18000
REVIEW_PATHS = [
    '*.py',
    '*.md',
    'README.md',
    'AGENTS.md',
    'docs/**',
    '.github/PULL_REQUEST_TEMPLATE.md',
    'requirements.txt',
    'pyproject.toml',
    'setup.cfg',
    '.github/workflows/*.yml',
    '.github/scripts/*.py',
]


def run_git(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ git command failed: {' '.join(args)}")
        print(result.stderr.strip())
        return ''
    return result.stdout.strip()


def get_diff():
    """Get PR diff content for review-relevant files."""
    base_ref = os.environ.get('GITHUB_BASE_REF', 'main')
    diff = run_git(['git', 'diff', f'origin/{base_ref}...HEAD', '--', *REVIEW_PATHS])
    truncated = len(diff) > MAX_DIFF_LENGTH
    return diff[:MAX_DIFF_LENGTH], truncated


def get_changed_files():
    """Get changed file list for review-relevant files."""
    base_ref = os.environ.get('GITHUB_BASE_REF', 'main')
    output = run_git(['git', 'diff', '--name-only', f'origin/{base_ref}...HEAD', '--', *REVIEW_PATHS])
    return output.split('\n') if output else []


def get_pr_context():
    """Read PR title/body from GitHub event payload when available."""
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not event_path or not os.path.exists(event_path):
        return '', ''
    try:
        with open(event_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        pr = payload.get('pull_request', {})
        return (pr.get('title') or '').strip(), (pr.get('body') or '').strip()
    except Exception:
        return '', ''


def classify_files(files):
    py_files = [f for f in files if f.endswith('.py')]
    doc_files = [f for f in files if f.endswith('.md') or f.startswith('docs/') or f in ('README.md', 'AGENTS.md')]
    ci_files = [f for f in files if f.startswith('.github/workflows/')]
    config_files = [
        f for f in files if f in ('requirements.txt', 'pyproject.toml', 'setup.cfg', '.github/PULL_REQUEST_TEMPLATE.md')
    ]
    return py_files, doc_files, ci_files, config_files


def build_prompt(diff_content, files, truncated, pr_title, pr_body):
    """Build AI review prompt aligned with AGENTS.md requirements."""
    truncate_notice = ''
    if truncated:
        truncate_notice = "\n\n> ⚠️ 주의: diff가 너무 길어 잘렸습니다. 표시된 내용을 기반으로 검토하고 불확실한 부분을 표시해 주세요.\n"

    py_files, doc_files, ci_files, config_files = classify_files(files)

    return f"""당신은 이 저장소의 PR 리뷰 어시스턴트입니다. 변경 내용과 PR 설명을 바탕으로 "코드 + 문서 + CI" 통합 리뷰를 수행하세요.

## PR 정보
- 제목: {pr_title or '(empty)'}
- 설명:
{pr_body or '(empty)'}

## 수정 파일 통계
- Python: {len(py_files)}
- Docs/Markdown: {len(doc_files)}
- CI Workflow: {len(ci_files)}
- Config/Template: {len(config_files)}

수정 파일 목록:
{', '.join(files)}{truncate_notice}

## 코드 변경사항 (diff)
```diff
{diff_content}
```

## 반드시 준수해야 할 리뷰 규칙（저장소 AGENTS.md 기반）
1. 필요성（Necessity）: 명확한 문제/비즈니스 가치가 있는지, 불필요한 리팩토링을 피해야 함.
2. 연관성（Traceability）: 관련 Issue（Fixes/Refs）가 있는지; Issue가 없을 때 동기와 수락 기준을 제시했는지.
3. 유형 판별（Type）: fix/feat/refactor/docs/chore/test가 적절한지.
4. 설명 완전성（Description Completeness）: 배경, 범위, 검증 명령 및 결과, 호환성 위험, 롤백 방안이 포함되어 있는지.
5. 병합 판정（Merge Readiness）: Ready / Not Ready를 제시하고 차단 항목을 나열.
6. 사용자에게 보이는 기능이 포함된 경우, README.md와 docs/CHANGELOG.md가 동기화되어 있는지 확인.

## 리뷰 출력 요구사항
- 한국어를 사용하세요.
- 먼저 "결론": `Ready to Merge` 또는 `Not Ready`.
- 그런 다음 구조화된 결과:
  - 필요성: 통과/미통과 + 이유
  - 연관성: 통과/미통과 + 근거
  - 유형: 권장 유형
  - 설명 완전성: 완전/불완전（누락 항목）
  - 위험 수준: 낮음/중간/높음 + 핵심 위험
  - 필수 수정 항목（최대 5개, 우선순위 순）
  - 권장 항목（최대 5개）
- 발견된 문제는 가능한 한 파일 경로를 지정하고 영향을 설명하세요.
- 정보가 부족한 경우, "현재 diff/PR 설명으로는 확인할 수 없음"이라고 명확히 작성하세요.
"""


def review_with_gemini(prompt):
    """Run review with Gemini API."""
    api_key = os.environ.get('GEMINI_API_KEY')
    model = os.environ.get('GEMINI_MODEL') or os.environ.get('GEMINI_MODEL_FALLBACK') or 'gemini-2.5-flash'

    if not api_key:
        print("❌ Gemini API Key가 설정되지 않았습니다（GitHub Secrets 확인: GEMINI_API_KEY）")
        return None

    print(f"🤖 사용 모델: {model}")

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        print(f"✅ Gemini ({model}) 리뷰 성공")
        return response.text
    except ImportError as e:
        print(f"❌ Gemini 의존성이 설치되지 않았습니다: {e}")
        print("   google-genai가 설치되어 있는지 확인하세요: pip install google-genai")
        return None
    except Exception as e:
        print(f"❌ Gemini 리뷰 실패: {e}")
        traceback.print_exc()
        return None


def review_with_openai(prompt):
    """Run review with OpenAI-compatible API as fallback."""
    api_key = os.environ.get('OPENAI_API_KEY')
    base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    if not api_key:
        print("❌ OpenAI API Key가 설정되지 않았습니다（GitHub Secrets 확인: OPENAI_API_KEY）")
        return None

    print(f"🌐 Base URL: {base_url}")
    print(f"🤖 사용 모델: {model}")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3
        )
        print(f"✅ OpenAI 호환 인터페이스 ({model}) 리뷰 성공")
        return response.choices[0].message.content
    except ImportError as e:
        print(f"❌ OpenAI 의존성이 설치되지 않았습니다: {e}")
        print("   openai가 설치되어 있는지 확인하세요: pip install openai")
        return None
    except Exception as e:
        print(f"❌ OpenAI 호환 인터페이스 리뷰 실패: {e}")
        traceback.print_exc()
        return None


def ai_review(diff_content, files, truncated):
    """Run AI review: Gemini first, then OpenAI fallback."""
    pr_title, pr_body = get_pr_context()
    prompt = build_prompt(diff_content, files, truncated, pr_title, pr_body)

    result = review_with_gemini(prompt)
    if result:
        return result

    print("OpenAI 호환 인터페이스 시도 중...")
    result = review_with_openai(prompt)
    if result:
        return result

    return None


def main():
    diff, truncated = get_diff()
    files = get_changed_files()

    if not diff or not files:
        print("검토할 코드/문서/설정 변경사항이 없습니다. AI 리뷰를 건너뜁니다")
        summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary_file:
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write("## 🤖 AI 코드 리뷰\n\n✅ 검토할 변경사항이 없습니다\n")
        return

    print(f"리뷰 파일: {files}")
    if truncated:
        print(f"⚠️ Diff 내용이 {MAX_DIFF_LENGTH}자로 잘렸습니다")

    review = ai_review(diff, files, truncated)

    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')

    strict_mode = os.environ.get('AI_REVIEW_STRICT', 'false').lower() == 'true'

    if review:
        if summary_file:
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write(f"## 🤖 AI 코드 리뷰\n\n{review}\n")

        with open('ai_review_result.txt', 'w', encoding='utf-8') as f:
            f.write(review)

        print("AI 리뷰 완료")
    else:
        print("⚠️ 모든 AI 인터페이스를 사용할 수 없습니다")
        if summary_file:
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write("## 🤖 AI 코드 리뷰\n\n⚠️ AI 인터페이스를 사용할 수 없습니다. 설정을 확인해 주세요\n")
        if strict_mode:
            raise SystemExit("AI_REVIEW_STRICT=true and no AI review result is available")


if __name__ == '__main__':
    main()
