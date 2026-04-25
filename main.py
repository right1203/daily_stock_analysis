# -*- coding: utf-8 -*-
"""
===================================
관심 종목 지능형 분석 시스템 - 메인 스케줄러
===================================

역할:
1. 각 모듈을 조율하여 종목 분석 프로세스 완료
2. 저동시성 스레드 풀 스케줄링 구현
3. 전역 예외 처리, 단일 종목 실패가 전체에 영향 미치지 않도록 보장
4. 커맨드라인 진입점 제공

사용법:
    python main.py              # 정상 실행
    python main.py --debug      # 디버그 모드
    python main.py --dry-run    # 데이터만 조회, 분석 없음

매매 철학 (분석에 반영됨):
- 엄격한 진입 전략: 고점 추격 금지, 이격률 > 5% 시 매수 불가
- 추세 매매: MA5>MA10>MA20 정배열 종목만 매매
- 효율 우선: 수급 구조가 좋은 종목에 집중
- 매수 시점 선호: 거래량 감소 후 MA5/MA10 지지 리테스트
"""
import os
from src.config import setup_env
setup_env()

# 프록시 설정 - USE_PROXY 환경 변수로 제어, 기본 비활성화
# GitHub Actions 환경에서는 프록시 설정 자동 건너뜀
if os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("USE_PROXY", "false").lower() == "true":
    # 로컬 개발 환경, 프록시 활성화 (.env에서 PROXY_HOST 및 PROXY_PORT 설정 가능)
    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    proxy_port = os.getenv("PROXY_PORT", "10809")
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url

import argparse
import logging
import sys
import time
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from data_provider.base import canonical_stock_code
from src.core.pipeline import StockAnalysisPipeline
from src.core.market_review import run_market_review
from src.webui_frontend import prepare_webui_frontend_assets
from src.config import get_config, Config
from src.logging_config import setup_logging


logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """커맨드라인 인수 파싱"""
    parser = argparse.ArgumentParser(
        description='관심 종목 지능형 분석 시스템',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
예시:
  python main.py                    # 정상 실행
  python main.py --debug            # 디버그 모드
  python main.py --dry-run          # 데이터만 조회, AI 분석 없음
  python main.py --stocks 005930,AAPL  # 특정 종목 지정 분석
  python main.py --no-notify        # 푸시 알림 전송 안 함
  python main.py --single-notify    # 단일 종목 푸시 모드 활성화 (분석 완료 즉시 푸시)
  python main.py --schedule         # 예약 작업 모드 활성화
  python main.py --market-review    # 시장 전체 복기만 실행
        '''
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='디버그 모드 활성화, 상세 로그 출력'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='데이터만 조회, AI 분석 없음'
    )

    parser.add_argument(
        '--stocks',
        type=str,
        help='분석할 종목 코드 지정, 쉼표 구분 (설정 파일 덮어씀)'
    )

    parser.add_argument(
        '--no-notify',
        action='store_true',
        help='푸시 알림 전송 안 함'
    )

    parser.add_argument(
        '--single-notify',
        action='store_true',
        help='단일 종목 푸시 모드 활성화: 종목 분석 완료 즉시 푸시, 일괄 푸시 아님'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='동시 스레드 수 (기본값: 설정 값 사용)'
    )

    parser.add_argument(
        '--schedule',
        action='store_true',
        help='예약 작업 모드 활성화, 매일 정해진 시간에 실행'
    )

    parser.add_argument(
        '--no-run-immediately',
        action='store_true',
        help='예약 작업 시작 시 즉시 실행 안 함'
    )

    parser.add_argument(
        '--market-review',
        action='store_true',
        help='시장 전체 복기 분석만 실행'
    )

    parser.add_argument(
        '--no-market-review',
        action='store_true',
        help='시장 전체 복기 분석 건너뜀'
    )

    parser.add_argument(
        '--force-run',
        action='store_true',
        help='거래일 검사 건너뜀, 전체 분석 강제 실행 (Issue #373)'
    )

    parser.add_argument(
        '--webui',
        action='store_true',
        help='Web 관리 인터페이스 시작'
    )

    parser.add_argument(
        '--webui-only',
        action='store_true',
        help='Web 서비스만 시작, 자동 분석 실행 안 함'
    )

    parser.add_argument(
        '--serve',
        action='store_true',
        help='FastAPI 백엔드 서비스 시작 (분석 작업도 동시 실행)'
    )

    parser.add_argument(
        '--serve-only',
        action='store_true',
        help='FastAPI 백엔드 서비스만 시작, 자동 분석 실행 안 함'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='FastAPI 서비스 포트 (기본값: 8000)'
    )

    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='FastAPI 서비스 수신 주소 (기본값: 0.0.0.0)'
    )

    parser.add_argument(
        '--no-context-snapshot',
        action='store_true',
        help='분석 컨텍스트 스냅샷 저장 안 함'
    )

    # === Backtest ===
    parser.add_argument(
        '--backtest',
        action='store_true',
        help='백테스트 실행 (과거 분석 결과 평가)'
    )

    parser.add_argument(
        '--backtest-code',
        type=str,
        default=None,
        help='특정 종목 코드만 백테스트'
    )

    parser.add_argument(
        '--backtest-days',
        type=int,
        default=None,
        help='백테스트 평가 윈도우 (거래일 수, 기본값: 설정 값 사용)'
    )

    parser.add_argument(
        '--backtest-force',
        action='store_true',
        help='강제 백테스트 (이미 결과가 있어도 재계산)'
    )

    return parser.parse_args()


def _compute_trading_day_filter(
    config: Config,
    args: argparse.Namespace,
    stock_codes: List[str],
) -> Tuple[List[str], Optional[str], bool]:
    """
    Compute filtered stock list and effective market review region (Issue #373).

    Returns:
        (filtered_codes, effective_region, should_skip_all)
        - effective_region None = use config default (check disabled)
        - effective_region '' = all relevant markets closed, skip market review
        - should_skip_all: skip entire run when no stocks and no market review to run
    """
    force_run = getattr(args, 'force_run', False)
    if force_run or not getattr(config, 'trading_day_check_enabled', True):
        return (stock_codes, None, False)

    from src.core.trading_calendar import (
        get_market_for_stock,
        get_open_markets_today,
        compute_effective_region,
    )

    open_markets = get_open_markets_today()
    filtered_codes = []
    for code in stock_codes:
        mkt = get_market_for_stock(code)
        if mkt in open_markets or mkt is None:
            filtered_codes.append(code)

    if config.market_review_enabled and not getattr(args, 'no_market_review', False):
        effective_region = compute_effective_region(
            getattr(config, 'market_review_region', 'kr') or 'kr', open_markets
        )
    else:
        effective_region = None

    should_skip_all = (not filtered_codes) and (effective_region or '') == ''
    return (filtered_codes, effective_region, should_skip_all)


def run_full_analysis(
    config: Config,
    args: argparse.Namespace,
    stock_codes: Optional[List[str]] = None
):
    """
    전체 분석 프로세스 실행 (개별 종목 + 시장 전체 복기)

    예약 작업에서 호출하는 메인 함수
    """
    try:
        # Issue #529: Hot-reload STOCK_LIST from .env on each scheduled run
        if stock_codes is None:
            config.refresh_stock_list()

        # Issue #373: Trading day filter (per-stock, per-market)
        effective_codes = stock_codes if stock_codes is not None else config.stock_list
        filtered_codes, effective_region, should_skip = _compute_trading_day_filter(
            config, args, effective_codes
        )
        if should_skip:
            logger.info(
                "오늘 모든 관련 시장이 비거래일입니다, 실행 건너뜀. --force-run으로 강제 실행 가능."
            )
            return
        if set(filtered_codes) != set(effective_codes):
            skipped = set(effective_codes) - set(filtered_codes)
            logger.info("오늘 휴장 종목 건너뜀: %s", skipped)
        stock_codes = filtered_codes

        # 커맨드라인 인수 --single-notify 설정 덮어쓰기 (#55)
        if getattr(args, 'single_notify', False):
            config.single_stock_notify = True

        # Issue #190: 개별 종목과 시장 전체 복기 통합 푸시
        merge_notification = (
            getattr(config, 'merge_email_notification', False)
            and config.market_review_enabled
            and not getattr(args, 'no_market_review', False)
            and not config.single_stock_notify
        )

        # 스케줄러 생성
        save_context_snapshot = None
        if getattr(args, 'no_context_snapshot', False):
            save_context_snapshot = False
        query_id = uuid.uuid4().hex
        pipeline = StockAnalysisPipeline(
            config=config,
            max_workers=args.workers,
            query_id=query_id,
            query_source="cli",
            save_context_snapshot=save_context_snapshot
        )

        # 1. 개별 종목 분석 실행
        results = pipeline.run(
            stock_codes=stock_codes,
            dry_run=args.dry_run,
            send_notification=not args.no_notify,
            merge_notification=merge_notification
        )

        # Issue #128: 분석 간격 - 개별 종목 분석과 시장 분석 사이에 지연 추가
        analysis_delay = getattr(config, 'analysis_delay', 0)
        if (
            analysis_delay > 0
            and config.market_review_enabled
            and not args.no_market_review
            and effective_region != ''
        ):
            logger.info(f"{analysis_delay}초 후 시장 전체 복기 실행 (API 제한 방지)...")
            time.sleep(analysis_delay)

        # 2. 시장 전체 복기 실행 (활성화된 경우, 개별 종목 전용 모드가 아닌 경우)
        market_report = ""
        if (
            config.market_review_enabled
            and not args.no_market_review
            and effective_region != ''
        ):
            review_result = run_market_review(
                notifier=pipeline.notifier,
                analyzer=pipeline.analyzer,
                search_service=pipeline.search_service,
                send_notification=not args.no_notify,
                merge_notification=merge_notification,
                override_region=effective_region,
            )
            # Keep market review content available for merged notification output.
            if review_result:
                market_report = review_result

        # Issue #190: 통합 푸시 (개별 종목 + 시장 전체 복기)
        if merge_notification and (results or market_report) and not args.no_notify:
            parts = []
            if market_report:
                parts.append(f"# 📈 시장 전체 복기\n\n{market_report}")
            if results:
                dashboard_content = pipeline.notifier.generate_dashboard_report(results)
                parts.append(f"# 🚀 개별 종목 의사결정 대시보드\n\n{dashboard_content}")
            if parts:
                combined_content = "\n\n---\n\n".join(parts)
                if pipeline.notifier.is_available():
                    if pipeline.notifier.send(combined_content, email_send_to_all=True):
                        logger.info("통합 푸시 완료 (개별 종목 + 시장 전체 복기)")
                    else:
                        logger.warning("통합 푸시 실패")

        # 요약 출력
        if results:
            logger.info("\n===== 분석 결과 요약 =====")
            for r in sorted(results, key=lambda x: x.sentiment_score, reverse=True):
                emoji = r.get_emoji()
                logger.info(
                    f"{emoji} {r.name}({r.code}): {r.operation_advice} | "
                    f"평점 {r.sentiment_score} | {r.trend_prediction}"
                )

        logger.info("\n작업 실행 완료")

        # === 자동 백테스트 ===
        try:
            if getattr(config, 'backtest_enabled', False):
                from src.services.backtest_service import BacktestService

                logger.info("자동 백테스트 시작...")
                service = BacktestService()
                stats = service.run_backtest(
                    force=False,
                    eval_window_days=getattr(config, 'backtest_eval_window_days', 10),
                    min_age_days=getattr(config, 'backtest_min_age_days', 14),
                    limit=200,
                )
                logger.info(
                    f"자동 백테스트 완료: processed={stats.get('processed')} saved={stats.get('saved')} "
                    f"completed={stats.get('completed')} insufficient={stats.get('insufficient')} errors={stats.get('errors')}"
                )
        except Exception as e:
            logger.warning(f"자동 백테스트 실패 (무시됨): {e}")

    except Exception as e:
        logger.exception(f"분석 프로세스 실행 실패: {e}")


def start_api_server(host: str, port: int, config: Config) -> None:
    """
    백그라운드 스레드에서 FastAPI 서비스 시작

    Args:
        host: 수신 주소
        port: 수신 포트
        config: 설정 객체
    """
    import threading
    import uvicorn

    def run_server():
        level_name = (config.log_level or "INFO").lower()
        uvicorn.run(
            "api.app:app",
            host=host,
            port=port,
            log_level=level_name,
            log_config=None,
        )

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.info(f"FastAPI 서비스 시작됨: http://{host}:{port}")


def _is_truthy_env(var_name: str, default: str = "true") -> bool:
    """Parse common truthy / falsy environment values."""
    value = os.getenv(var_name, default).strip().lower()
    return value not in {"0", "false", "no", "off"}

def start_bot_stream_clients(config: Config) -> None:
    """Start bot stream clients when enabled in config."""
    return None


def main() -> int:
    """
    메인 진입점 함수

    Returns:
        종료 코드 (0 = 성공)
    """
    # 커맨드라인 인수 파싱
    args = parse_arguments()

    # 설정 로드 (로그 설정 전에 로드하여 로그 디렉토리 조회)
    config = get_config()

    # 로그 설정 (콘솔 및 파일 출력)
    setup_logging(log_prefix="stock_analysis", debug=args.debug, log_dir=config.log_dir)

    logger.info("=" * 60)
    logger.info("관심 종목 지능형 분석 시스템 시작")
    logger.info(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 설정 검증
    warnings = config.validate()
    for warning in warnings:
        logger.warning(warning)

    # 종목 목록 파싱 (대문자로 통일 Issue #355)
    stock_codes = None
    if args.stocks:
        stock_codes = [canonical_stock_code(c) for c in args.stocks.split(',') if (c or "").strip()]
        logger.info(f"커맨드라인에서 지정한 종목 목록 사용: {stock_codes}")

    # === --webui / --webui-only 인수 처리, --serve / --serve-only에 매핑 ===
    if args.webui:
        args.serve = True
    if args.webui_only:
        args.serve_only = True

    # 구버전 WEBUI_ENABLED 환경 변수 호환
    if config.webui_enabled and not (args.serve or args.serve_only):
        args.serve = True

    # === Web 서비스 시작 (활성화된 경우) ===
    start_serve = (args.serve or args.serve_only) and os.getenv("GITHUB_ACTIONS") != "true"

    # 구버전 WEBUI_HOST/WEBUI_PORT 호환: --host/--port로 지정하지 않은 경우 구 변수 사용
    if start_serve:
        if args.host == '0.0.0.0' and os.getenv('WEBUI_HOST'):
            args.host = os.getenv('WEBUI_HOST')
        if args.port == 8000 and os.getenv('WEBUI_PORT'):
            args.port = int(os.getenv('WEBUI_PORT'))

    bot_clients_started = False
    if start_serve:
        if not prepare_webui_frontend_assets():
            logger.warning("프론트엔드 정적 자산이 준비되지 않았습니다, FastAPI 서비스 계속 시작 (Web 페이지 이용 불가할 수 있음)")
        try:
            start_api_server(host=args.host, port=args.port, config=config)
            bot_clients_started = True
        except Exception as e:
            logger.error(f"FastAPI 서비스 시작 실패: {e}")

    if bot_clients_started:
        start_bot_stream_clients(config)

    # === Web 서비스 전용 모드: 자동 분석 실행 안 함 ===
    if args.serve_only:
        logger.info("모드: Web 서비스 전용")
        logger.info(f"Web 서비스 실행 중: http://{args.host}:{args.port}")
        logger.info("/api/v1/analysis/stock/{code} 엔드포인트로 분석 트리거")
        logger.info(f"API 문서: http://{args.host}:{args.port}/docs")
        logger.info("Ctrl+C로 종료...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n사용자 중단, 프로그램 종료")
        return 0

    try:
        # 모드0: 백테스트
        if getattr(args, 'backtest', False):
            logger.info("모드: 백테스트")
            from src.services.backtest_service import BacktestService

            service = BacktestService()
            stats = service.run_backtest(
                code=getattr(args, 'backtest_code', None),
                force=getattr(args, 'backtest_force', False),
                eval_window_days=getattr(args, 'backtest_days', None),
            )
            logger.info(
                f"백테스트 완료: processed={stats.get('processed')} saved={stats.get('saved')} "
                f"completed={stats.get('completed')} insufficient={stats.get('insufficient')} errors={stats.get('errors')}"
            )
            return 0

        # 모드1: 시장 전체 복기만
        if args.market_review:
            from src.analyzer import GeminiAnalyzer
            from src.core.market_review import run_market_review
            from src.notification import NotificationService
            from src.search_service import SearchService

            # Issue #373: Trading day check for market-review-only mode.
            # Do NOT use _compute_trading_day_filter here: that helper checks
            # config.market_review_enabled, which would wrongly block an
            # explicit --market-review invocation when the flag is disabled.
            effective_region = None
            if not getattr(args, 'force_run', False) and getattr(config, 'trading_day_check_enabled', True):
                from src.core.trading_calendar import get_open_markets_today, compute_effective_region as _compute_region
                open_markets = get_open_markets_today()
                effective_region = _compute_region(
                    getattr(config, 'market_review_region', 'kr') or 'kr', open_markets
                )
                if effective_region == '':
                    logger.info("오늘 시장 전체 복기 관련 시장이 모두 비거래일입니다, 실행 건너뜀. --force-run으로 강제 실행 가능.")
                    return 0

            logger.info("모드: 시장 전체 복기만")
            notifier = NotificationService()

            # 검색 서비스 및 분석기 초기화 (설정된 경우)
            search_service = None
            analyzer = None

            if config.naver_api_keys or config.tavily_api_keys or config.brave_api_keys or config.serpapi_keys:
                search_service = SearchService(
                    naver_keys=config.naver_api_keys,
                    tavily_keys=config.tavily_api_keys,
                    brave_keys=config.brave_api_keys,
                    serpapi_keys=config.serpapi_keys,
                    news_max_age_days=config.news_max_age_days,
                )

            if config.gemini_api_key or config.openai_api_key:
                analyzer = GeminiAnalyzer(api_key=config.gemini_api_key)
                if not analyzer.is_available():
                    logger.warning("AI 분석기 초기화 후 사용 불가, API Key 설정 확인 필요")
                    analyzer = None
            else:
                logger.warning("API Key (Gemini/OpenAI) 미감지, 템플릿으로만 리포트 생성")

            run_market_review(
                notifier=notifier,
                analyzer=analyzer,
                search_service=search_service,
                send_notification=not args.no_notify,
                override_region=effective_region,
            )
            return 0

        # 모드2: 예약 작업 모드
        if args.schedule or config.schedule_enabled:
            logger.info("모드: 예약 작업")
            logger.info(f"매일 실행 시간: {config.schedule_time}")

            # Determine whether to run immediately:
            # Command line arg --no-run-immediately overrides config if present.
            # Otherwise use config (defaults to True).
            should_run_immediately = config.schedule_run_immediately
            if getattr(args, 'no_run_immediately', False):
                should_run_immediately = False

            logger.info(f"시작 시 즉시 실행: {should_run_immediately}")

            from src.scheduler import run_with_schedule

            def scheduled_task():
                run_full_analysis(config, args, stock_codes)

            run_with_schedule(
                task=scheduled_task,
                schedule_time=config.schedule_time,
                run_immediately=should_run_immediately
            )
            return 0

        # 모드3: 정상 단일 실행
        if config.run_immediately:
            run_full_analysis(config, args, stock_codes)
        else:
            logger.info("즉시 분석 실행 안 함으로 설정됨 (RUN_IMMEDIATELY=false)")

        logger.info("\n프로그램 실행 완료")

        # 서비스가 활성화되어 있고 예약 작업 모드가 아닌 경우 프로그램 유지
        keep_running = start_serve and not (args.schedule or config.schedule_enabled)
        if keep_running:
            logger.info("API 서비스 실행 중 (Ctrl+C로 종료)...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        return 0

    except KeyboardInterrupt:
        logger.info("\n사용자 중단, 프로그램 종료")
        return 130

    except Exception as e:
        logger.exception(f"프로그램 실행 실패: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
