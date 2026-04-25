# -*- coding: utf-8 -*-
"""Environment validation helper for the KR/US stock analysis system."""

import argparse
import logging
import os
import sys
from datetime import date, datetime

# Proxy config is controlled by USE_PROXY and is off by default.
if os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("USE_PROXY", "false").lower() == "true":
    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    proxy_port = os.getenv("PROXY_PORT", "10809")
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_header(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title: str) -> None:
    """Print a subsection title."""
    print(f"\n--- {title} ---")


def _configured(value) -> str:
    """Return a Korean configured/not-configured marker."""
    return "설정됨 ✓" if value else "미설정 ✗"


def test_config() -> bool:
    """Validate configuration loading."""
    print_header("1. 설정 로드 테스트")

    from src.config import get_config
    from src.notification import NotificationService

    config = get_config()

    print_section("기본 설정")
    print(f"  종목 목록: {config.stock_list}")
    print(f"  데이터베이스 경로: {config.database_path}")
    print(f"  최대 동시 작업 수: {config.max_workers}")
    print(f"  디버그 모드: {config.debug}")

    print_section("API 설정")
    print(f"  Naver Search API Keys: {_configured(config.naver_api_keys)}")
    if config.naver_api_keys:
        print(f"    첫 번째 Key 앞 8자리: {config.naver_api_keys[0][:8]}...")

    print(f"  Gemini API Key: {_configured(config.gemini_api_key)}")
    if config.gemini_api_key:
        print(f"    Key 앞 8자리: {config.gemini_api_key[:8]}...")
    print(f"  Gemini 기본 모델: {config.gemini_model}")
    print(f"  Gemini 대체 모델: {config.gemini_model_fallback}")

    print_section("알림 설정")
    notification_service = NotificationService()
    if notification_service.is_available():
        print(f"  알림 채널: {notification_service.get_channel_names()}")
    else:
        print("  알림 채널: 미설정 ✗")

    print_section("설정 검증")
    issues = config.validate_structured()
    prefix = {"error": "  ✗", "warning": "  ⚠", "info": "  ·"}
    for issue in issues:
        print(f"{prefix.get(issue.severity, '  ?')} [{issue.severity.upper()}] {issue.message}")
    if not any(i.severity in ("error", "warning") for i in issues):
        print("  ✓ 핵심 설정 검증 통과")

    return True


def view_database() -> bool:
    """Show stored market data from the configured database."""
    print_header("2. 데이터베이스 조회")

    from sqlalchemy import text
    from src.storage import get_db

    db = get_db()
    session = db.get_session()
    try:
        print_section("데이터베이스 연결")
        print("  ✓ 연결 성공")

        result = session.execute(text("""
            SELECT code, COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date, data_source
            FROM stock_daily
            GROUP BY code
            ORDER BY code
        """))
        stocks = result.fetchall()

        print_section(f"저장된 종목 데이터 ({len(stocks)}개)")
        if stocks:
            print(f"  {'Code':<10} {'Rows':<8} {'Start':<12} {'Latest':<12} {'Source'}")
            print("  " + "-" * 60)
            for row in stocks:
                print(f"  {row[0]:<10} {row[1]:<8} {row[2]!s:<12} {row[3]!s:<12} {row[4] or 'Unknown'}")
        else:
            print("  데이터가 없습니다")

        today = date.today()
        result = session.execute(text("""
            SELECT code, date, open, high, low, close, pct_chg, volume, ma5, ma10, ma20, volume_ratio
            FROM stock_daily
            WHERE date = :today
            ORDER BY code
        """), {"today": today})
        today_data = result.fetchall()

        print_section(f"오늘 데이터 ({today})")
        if today_data:
            for row in today_data:
                code, _, open_, high, low, close, pct_chg, volume, ma5, ma10, _, vol_ratio = row
                print(f"\n  [{code}]")
                print(f"    시가: {open_:.2f}  고가: {high:.2f}  저가: {low:.2f}  종가: {close:.2f}")
                print(f"    등락률: {pct_chg:.2f}%  거래량: {volume:,.0f}")
                print(f"    MA5: {ma5:.2f}  MA10: {ma10:.2f}  거래량 비율: {vol_ratio:.2f}")
        else:
            print("  오늘 데이터가 없습니다")

        result = session.execute(text("""
            SELECT code, date, close, pct_chg, volume, data_source
            FROM stock_daily
            ORDER BY date DESC, code
            LIMIT 10
        """))
        recent = result.fetchall()

        print_section("최근 10개 기록")
        if recent:
            print(f"  {'Code':<10} {'Date':<12} {'Close':<10} {'Change%':<8} {'Volume':<15} {'Source'}")
            print("  " + "-" * 70)
            for row in recent:
                volume = f"{row[4]:,.0f}" if row[4] else "N/A"
                print(f"  {row[0]:<10} {row[1]!s:<12} {row[2]:<10.2f} {row[3]:<8.2f} {volume:<15} {row[5] or 'Unknown'}")
    finally:
        session.close()

    return True


def test_data_fetch(stock_code: str = "005930") -> bool:
    """Test market data fetching with a retained KR/US symbol."""
    print_header("3. 데이터 조회 테스트")

    from data_provider import DataFetcherManager

    manager = DataFetcherManager()

    print_section("데이터 소스 목록")
    for i, name in enumerate(manager.available_fetchers, 1):
        print(f"  {i}. {name}")

    print_section(f"{stock_code} 데이터 조회")
    print("  조회 중입니다. 몇 초 정도 걸릴 수 있습니다...")

    try:
        df, source = manager.get_daily_data(stock_code, days=5)
        print("  ✓ 조회 성공")
        print(f"    데이터 소스: {source}")
        print(f"    레코드 수: {len(df)}")

        print_section("데이터 미리보기(최근 5개)")
        if not df.empty:
            preview_cols = ["date", "open", "high", "low", "close", "pct_chg", "volume"]
            existing_cols = [c for c in preview_cols if c in df.columns]
            print(df[existing_cols].tail().to_string(index=False))
        return True
    except Exception as e:
        print(f"  ✗ 조회 실패: {e}")
        return False


def test_llm() -> bool:
    """Test Gemini analysis calls."""
    print_header("4. LLM (Gemini) 호출 테스트")

    import socket
    import time

    from src.analyzer import GeminiAnalyzer
    from src.config import get_config

    config = get_config()

    print_section("모델 설정")
    print(f"  기본 모델: {config.gemini_model}")
    print(f"  대체 모델: {config.gemini_model_fallback}")

    print_section("네트워크 연결 확인")
    try:
        socket.setdefaulttimeout(10)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("generativelanguage.googleapis.com", 443))
        print("  ✓ Google API 서버에 연결할 수 있습니다")
    except Exception as e:
        print(f"  ✗ Google API 서버에 연결할 수 없습니다: {e}")
        print("  안내: 네트워크 연결 또는 프록시 설정을 확인하세요")
        return False

    analyzer = GeminiAnalyzer()
    print_section("모델 초기화")
    if analyzer.is_available():
        print("  ✓ 모델 초기화 성공")
    else:
        print("  ✗ 모델 초기화 실패(API Key 확인 필요)")
        return False

    test_context = {
        "code": "005930",
        "date": date.today().isoformat(),
        "today": {
            "open": 72000.0,
            "high": 72800.0,
            "low": 71600.0,
            "close": 72500.0,
            "volume": 12000000,
            "amount": 870000000000,
            "pct_chg": 0.83,
            "ma5": 72100.0,
            "ma10": 71800.0,
            "ma20": 71000.0,
            "volume_ratio": 1.1,
        },
        "ma_status": "정배열",
        "volume_change_ratio": 1.05,
        "price_change_ratio": 0.83,
    }

    print_section("테스트 요청 전송")
    print("  테스트 종목: 삼성전자 (005930)")
    print("  Gemini API 호출 중입니다(타임아웃: 60초)...")

    start_time = time.time()
    try:
        result = analyzer.analyze(test_context)
        elapsed = time.time() - start_time
        print(f"\n  ✓ API 호출 성공 (소요: {elapsed:.2f}초)")

        print_section("분석 결과")
        print(f"  심리 점수: {result.sentiment_score}/100")
        print(f"  추세 전망: {result.trend_prediction}")
        print(f"  투자 판단: {result.operation_advice}")
        print(f"  기술 분석: {result.technical_analysis[:80]}..." if len(result.technical_analysis) > 80 else f"  기술 분석: {result.technical_analysis}")
        print(f"  뉴스 요약: {result.news_summary[:80]}..." if len(result.news_summary) > 80 else f"  뉴스 요약: {result.news_summary}")
        print(f"  종합 요약: {result.analysis_summary}")
        if not result.success:
            print(f"\n  ⚠ 주의: {result.error_message}")
        return result.success
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n  ✗ API 호출 실패 (소요: {elapsed:.2f}초)")
        print(f"  오류: {e}")
        return False


def test_notification() -> bool:
    """Test notification delivery through configured channels."""
    print_header("5. 알림 전송 테스트")

    from src.notification import NotificationService

    service = NotificationService()

    print_section("설정 확인")
    if service.is_available():
        print(f"  ✓ 알림 채널 설정됨: {service.get_channel_names()}")
    else:
        print("  ✗ 알림 채널이 설정되지 않았습니다")
        return False

    print_section("테스트 메시지 전송")
    test_message = f"""## 시스템 테스트 메시지

이 메시지는 **KR/US 주식 지능형 분석 시스템**에서 보낸 테스트 메시지입니다.

- 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 테스트 목적: 설정된 알림 채널 검증

이 메시지를 받았다면 알림 기능이 정상적으로 설정된 것입니다."""

    print("  전송 중...")

    try:
        success = service.send(test_message)
        if success:
            print("  ✓ 메시지 전송 성공. 설정된 알림 채널을 확인하세요")
        else:
            print("  ✗ 메시지 전송 실패")
        return success
    except Exception as e:
        print(f"  ✗ 전송 예외: {e}")
        return False


def run_all_tests() -> None:
    """Run the default environment checks."""
    print("\n" + "🚀" * 20)
    print("  KR/US 주식 지능형 분석 시스템 - 환경 검증")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("🚀" * 20)

    results = {}
    for name, func in (("설정 로드", test_config), ("데이터베이스", view_database)):
        try:
            results[name] = func()
        except Exception as e:
            print(f"  ✗ {name} 테스트 실패: {e}")
            results[name] = False

    print_header("테스트 결과 요약")
    for name, passed in results.items():
        status = "✓ 통과" if passed else "✗ 실패"
        print(f"  {status}: {name}")

    print("\n안내: --llm, --fetch, --notify 옵션으로 개별 테스트를 실행할 수 있습니다")


def query_stock_data(stock_code: str, days: int = 10) -> None:
    """Query stored data for a stock."""
    print_header(f"종목 데이터 조회: {stock_code}")

    from sqlalchemy import text
    from src.storage import get_db

    db = get_db()
    session = db.get_session()
    try:
        result = session.execute(text("""
            SELECT date, open, high, low, close, pct_chg, volume, amount, ma5, ma10, ma20, volume_ratio
            FROM stock_daily
            WHERE code = :code
            ORDER BY date DESC
            LIMIT :limit
        """), {"code": stock_code, "limit": days})

        rows = result.fetchall()
        if rows:
            print(f"\n  최근 {len(rows)}개 기록:\n")
            print(f"  {'Date':<12} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Change%':<8} {'MA5':<10} {'MA10':<10} {'VolRatio':<8}")
            print("  " + "-" * 100)
            for row in rows:
                dt, open_, high, low, close, pct_chg, _, _, ma5, ma10, _, vol_ratio = row
                print(f"  {dt!s:<12} {open_:<10.2f} {high:<10.2f} {low:<10.2f} {close:<10.2f} {pct_chg:<8.2f} {ma5:<10.2f} {ma10:<10.2f} {vol_ratio:<8.2f}")
        else:
            print(f"  {stock_code} 데이터가 없습니다")
    finally:
        session.close()


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="KR/US 주식 지능형 분석 시스템 - 환경 검증 테스트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", action="store_true", help="데이터베이스 내용 조회")
    parser.add_argument("--llm", action="store_true", help="LLM 호출 테스트")
    parser.add_argument("--fetch", action="store_true", help="데이터 조회 테스트")
    parser.add_argument("--notify", action="store_true", help="알림 전송 테스트")
    parser.add_argument("--config", action="store_true", help="설정 조회")
    parser.add_argument("--stock", type=str, help="지정 종목 데이터 조회, 예: --stock 005930")
    parser.add_argument("--all", action="store_true", help="모든 테스트 실행(LLM 포함)")

    args = parser.parse_args()

    if not any([args.db, args.llm, args.fetch, args.notify, args.config, args.stock, args.all]):
        run_all_tests()
        return 0

    if args.config:
        test_config()
    if args.db:
        view_database()
    if args.stock:
        query_stock_data(args.stock)
    if args.fetch:
        test_data_fetch()
    if args.llm:
        test_llm()
    if args.notify:
        test_notification()
    if args.all:
        test_config()
        view_database()
        test_data_fetch()
        test_llm()
        test_notification()

    return 0


if __name__ == "__main__":
    sys.exit(main())
