#!/bin/bash
# ===================================
# KR/US intelligent analysis system - test script
# ===================================
#
# Usage:
#   ./test.sh [테스트 시나리오]
#
# Scenarios:
#   market      - 시장 리뷰만
#   kr-stock    - 한국 주식 분석(삼성전자, 카카오)
#   us-stock    - 미국 주식 분석(Apple, Tesla)
#   mixed       - KR/US 혼합 시장 분석
#   single      - 단일 종목 모드 테스트
#   dry-run     - 데이터만 가져오고 분석하지 않음
#   full        - 전체 흐름 테스트
#   quick       - 빠른 테스트(단일 종목)
#   all         - 모든 테스트 실행
#
# Examples:
#   ./test.sh market      # 시장 리뷰 테스트
#   ./test.sh us-stock    # 미국 주식 테스트
#   ./test.sh quick       # 빠른 테스트
#

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

header() {
    echo ""
    echo "=============================================="
    echo -e "${GREEN}$1${NC}"
    echo "=============================================="
    echo ""
}

# Check Python environment
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "Python3가 설치되어 있지 않습니다"
        exit 1
    fi
    info "Python 버전: $(python3 --version)"
}

# Check dependencies
check_deps() {
    info "의존성 확인 중..."
    python3 -c "import yfinance" 2>/dev/null || { warn "yfinance가 설치되어 있지 않아 미국 주식 테스트가 실패할 수 있습니다"; }
    python3 -c "import pykrx" 2>/dev/null || { warn "pykrx가 설치되어 있지 않아 한국 주식 테스트가 실패할 수 있습니다"; }
    success "의존성 확인 완료"
}

# ==================== Test scenarios ====================

# Test 1: market review
test_market() {
    header "테스트 시나리오: 시장 리뷰"
    info "시장 리뷰 분석 실행 중..."
    python3 main.py --market-review "$@"
    success "시장 리뷰 테스트 완료"
}

# Test 2: KR stock analysis
test_kr_stock() {
    header "테스트 시나리오: 한국 주식 분석"
    info "한국 주식 분석: 005930(삼성전자), 035720(카카오)"
    python3 main.py --stocks 005930,035720 --no-market-review "$@"
    success "한국 주식 분석 테스트 완료"
}

# Test 3: US stock analysis
test_us_stock() {
    header "테스트 시나리오: 미국 주식 분석"
    info "미국 주식 분석: AAPL(Apple), TSLA(Tesla)"
    # Forward extra args; do not add --no-notify by default
    python3 main.py --stocks AAPL --no-market-review "$@"
    success "미국 주식 분석 테스트 완료"
}

# Test 4: mixed market
test_mixed() {
    header "테스트 시나리오: 혼합 시장 분석"
    info "혼합 시장 분석: 005930(한국), AAPL(미국)"
    python3 main.py --stocks 005930,AAPL --no-market-review
    success "혼합 시장 테스트 완료"
}

# Test 5: single-stock notification mode
test_single() {
    header "테스트 시나리오: 단일 종목 알림 모드"
    info "단일 종목 알림 모드 테스트 중..."
    python3 main.py --stocks 005930 --single-notify --no-market-review
    success "단일 종목 알림 모드 테스트 완료"
}

# Test 6: dry-run mode
test_dry_run() {
    header "테스트 시나리오: Dry-Run 모드"
    info "데이터만 가져오고 AI 분석은 실행하지 않습니다..."
    python3 main.py --stocks 005930,AAPL --dry-run --no-notify
    success "Dry-Run 테스트 완료"
}

# Test 7: full flow
test_full() {
    header "테스트 시나리오: 전체 흐름"
    info "전체 분석 흐름(종목+시장)을 실행 중..."
    python3 main.py --stocks 005930 --no-notify
    success "전체 흐름 테스트 완료"
}

# Test 8: 빠른 테스트
test_quick() {
    header "테스트 시나리오: 빠른 테스트"
    info "단일 종목 빠른 테스트 중..."
    python3 main.py --stocks 005930 --no-market-review
    success "빠른 테스트 완료"
}

# Test 9: code recognition test
test_code_recognition() {
    header "테스트 시나리오: 코드 인식"
    info "주식 코드 인식 로직 테스트 중..."

    python3 << 'PYTEST'
import sys
sys.path.insert(0, '.')
from data_provider.kr_index_mapping import is_kr_index_code, is_kr_stock_code
from data_provider.us_index_mapping import is_us_index_code, is_us_stock_code

test_cases = [
    # (code, expected_kr_stock, expected_kr_index, expected_us_stock, expected_us_index, description)
    ("005930", True, False, False, False, "KR stock-Samsung Electronics"),
    ("035720", True, False, False, False, "KR stock-Kakao"),
    ("KOSDAQ", False, True, False, False, "KR index-KOSDAQ"),
    ("AAPL", False, False, True, False, "US stock-Apple"),
    ("TSLA", False, False, True, False, "US stock-Tesla"),
    ("BRK.B", False, False, True, False, "US stock-Berkshire B"),
    ("SPX", False, False, False, True, "US index-S&P 500"),
    ("hk00700", False, False, False, False, "removed legacy HK code"),  # kr-us-static-allow: removed-market
    ("SH600518", False, False, False, False, "removed legacy China code"),  # kr-us-static-allow: removed-market
]

print("\n주식 코드 인식 테스트:")
print("-" * 60)
all_pass = True
for code, exp_kr_stock, exp_kr_index, exp_us_stock, exp_us_index, desc in test_cases:
    kr_stock = is_kr_stock_code(code)
    kr_index = is_kr_index_code(code)
    us_stock = is_us_stock_code(code)
    us_index = is_us_index_code(code)
    ok = (
        kr_stock == exp_kr_stock
        and kr_index == exp_kr_index
        and us_stock == exp_us_stock
        and us_index == exp_us_index
    )
    status = "✅" if ok else "❌"
    all_pass = all_pass and ok
    print(
        f"{status} {code:10} | KR_STOCK:{kr_stock!s:5} KR_INDEX:{kr_index!s:5} "
        f"US_STOCK:{us_stock!s:5} US_INDEX:{us_index!s:5} | {desc}"
    )

print("-" * 60)
print(f"{'✅ 모든 테스트 통과!' if all_pass else '❌ 테스트 실패가 있습니다!'}")
sys.exit(0 if all_pass else 1)
PYTEST

    success "코드 인식 테스트 완료"
}

# Test 10: YFinance code conversion test
test_yfinance_convert() {
    header "테스트 시나리오: YFinance 코드 변환"
    info "YFinance 코드 변환 로직 테스트 중..."

    python3 << 'PYTEST'
import sys
sys.path.insert(0, '.')
from data_provider.yfinance_fetcher import YfinanceFetcher

fetcher = YfinanceFetcher()

test_cases = [
    ("AAPL", "AAPL", "US stock"),
    ("tsla", "TSLA", "US stock lowercase"),
    ("BRK.B", "BRK.B", "US stock special"),
    ("SPX", "^GSPC", "US index"),
    ("NASDAQ", "^IXIC", "US index alias"),
    ("005930", "005930.KS", "KR stock"),
    ("035720", "035720.KS", "KR stock"),
    ("KOSPI", "^KS11", "KR index"),
    ("KOSDAQ", "^KQ11", "KR index"),
]

print("\nYFinance 코드 변환 테스트:")
print("-" * 60)
all_pass = True
for input_code, expected, desc in test_cases:
    result = fetcher._convert_stock_code(input_code)
    status = "✅" if result == expected else "❌"
    all_pass = all_pass and (result == expected)
    print(f"{status} {input_code:10} -> {result:12} (expected: {expected:12}) | {desc}")

print("-" * 60)
print(f"{'✅ 모든 테스트 통과!' if all_pass else '❌ 테스트 실패가 있습니다!'}")
sys.exit(0 if all_pass else 1)
PYTEST

    success "YFinance 코드 변환 테스트 완료"
}

# Test 11: syntax check
test_syntax() {
    header "테스트 시나리오: Python 문법 검사"
    info "모든 Python 파일 문법 검사 중..."

    PYTHONPYCACHEPREFIX=/tmp/dsa_test_pycache python3 -m py_compile \
        main.py src/config.py src/notification.py \
        data_provider/yfinance_fetcher.py \
        data_provider/pykrx_fetcher.py \
        bot/commands/analyze.py

    success "문법 검사 통과"
}

# Test 12: Flake8 static check
test_flake8() {
    header "테스트 시나리오: Flake8 정적 검사"
    info "Flake8로 심각한 오류 검사 중..."

    if command -v flake8 &> /dev/null; then
        flake8 main.py src/config.py src/notification.py --select=F821,E999 --max-line-length=120
        success "Flake8 검사 통과"
    else
        warn "Flake8이 설치되어 있지 않아 검사를 건너뜁니다"
    fi
}

# 모든 테스트 실행
test_all() {
    header "모든 테스트 실행"

    test_syntax
    test_code_recognition
    test_yfinance_convert
    test_flake8

    echo ""
    info "다음 테스트는 네트워크와 API 설정이 필요하여 실패할 수 있습니다:"
    echo ""

    test_dry_run || warn "Dry-Run 테스트 실패(네트워크 문제일 수 있음)"
    test_quick || warn "빠른 테스트 실패(API 문제일 수 있음)"

    success "모든 테스트 완료!"
}

# ==================== Main program ====================

main() {
    header "KR/US 지능형 분석 시스템 - 테스트"

    check_python
    check_deps

    case "${1:-help}" in
        market)
            shift
            test_market "$@"
            ;;
        kr-stock|kr_stock|krstock|kr)
            shift
            test_kr_stock "$@"
            ;;
        us-stock|us_stock|usstock|us)
            shift
            test_us_stock "$@"
            ;;
        mixed|mix)
            shift
            test_mixed "$@"
            ;;
        single)
            shift
            test_single "$@"
            ;;
        dry-run|dryrun|dry)
            shift
            test_dry_run "$@"
            ;;
        full)
            shift
            test_full "$@"
            ;;
        quick|q)
            shift
            test_quick "$@"
            ;;
        code|recognition)
            shift
            test_code_recognition "$@"
            ;;
        yfinance|yf)
            shift
            test_yfinance_convert "$@"
            ;;
        syntax)
            shift
            test_syntax "$@"
            ;;
        flake8|lint)
            shift
            test_flake8 "$@"
            ;;
        all)
            shift
            test_all "$@"
            ;;
        help|--help|-h|*)
            echo "사용법: $0 [테스트 시나리오]"
            echo ""
            echo "테스트 시나리오:"
            echo "  market      - 시장 리뷰만"
            echo "  kr-stock    - 한국 주식 분석"
            echo "  us-stock    - 미국 주식 분석"
            echo "  mixed       - KR/US 혼합 시장 분석"
            echo "  single      - 단일 종목 알림 모드"
            echo "  dry-run     - 데이터만 가져오기"
            echo "  full        - 전체 흐름"
            echo "  quick       - 빠른 테스트(권장)"
            echo "  code        - 코드 인식 테스트"
            echo "  yfinance    - YFinance 변환 테스트"
            echo "  syntax      - 문법 검사"
            echo "  flake8      - 정적 검사"
            echo "  all         - 모든 테스트 실행"
            echo ""
            echo "예시:"
            echo "  $0 quick     # 빠른 테스트"
            echo "  $0 kr-stock  # 한국 주식 테스트"
            echo "  $0 us-stock  # 미국 주식 테스트"
            echo "  $0 code      # 코드 인식 테스트"
            echo "  $0 all       # 모든 테스트 실행"
            ;;
    esac
}

main "$@"
