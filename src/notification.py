# -*- coding: utf-8 -*-
"""
===================================
주식 분석 시스템 - 알림 레이어
===================================

기능:
1. 분석 결과를 일일 리포트로 종합
2. Markdown 형식 출력 지원
3. 다채널 푸시 (자동 감지):
   - Telegram Bot
   - 이메일 SMTP
   - Discord Bot
   - Pushover (모바일/데스크톱 푸시)
   - 사용자 정의 Webhook
"""
import logging
from datetime import datetime
from typing import List, Any, Optional
from enum import Enum

from src.config import get_config
from src.analyzer import AnalysisResult
from src.utils.data_processing import normalize_model_used
from src.notification_sender import (
    AstrbotSender,
    CustomWebhookSender,
    DiscordSender,
    EmailSender,
    PushoverSender,
    TelegramSender,
)

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """알림 채널 유형"""
    TELEGRAM = "telegram"  # Telegram
    EMAIL = "email"        # 이메일
    PUSHOVER = "pushover"  # Pushover
    CUSTOM = "custom"      # 사용자 정의 Webhook
    DISCORD = "discord"    # Discord 봇
    ASTRBOT = "astrbot"
    UNKNOWN = "unknown"    # 알 수 없음


class ChannelDetector:
    """
    채널 감지기 - 간소화 버전

    설정에 따라 직접 채널 유형을 판단합니다 (URL 파싱 불필요)
    """
    
    @staticmethod
    def get_channel_name(channel: NotificationChannel) -> str:
        """채널 한국어 이름을 반환합니다"""
        names = {
            NotificationChannel.TELEGRAM: "Telegram",
            NotificationChannel.EMAIL: "이메일",
            NotificationChannel.PUSHOVER: "Pushover",
            NotificationChannel.CUSTOM: "사용자 정의 Webhook",
            NotificationChannel.DISCORD: "Discord 봇",
            NotificationChannel.ASTRBOT: "ASTRBOT 봇",
            NotificationChannel.UNKNOWN: "알 수 없는 채널",
        }
        return names.get(channel, "알 수 없는 채널")


class NotificationService(
    AstrbotSender,
    CustomWebhookSender,
    DiscordSender,
    EmailSender,
    PushoverSender,
    TelegramSender,
):
    """
    알림 서비스

    담당:
    1. Markdown 형식의 분석 일보 생성
    2. 설정된 모든 채널로 메시지 푸시 (다채널 병렬)
    3. 로컬 일보 저장 지원

    지원 채널:
    - Telegram Bot
    - 이메일 SMTP
    - Pushover (모바일/데스크톱 푸시)
    - Discord
    - AstrBot
    - 사용자 정의 Webhook

    주의: 설정된 모든 채널로 푸시 전송됩니다
    """
    
    def __init__(self, source_message: Optional[Any] = None):
        """
        알림 서비스 초기화

        설정된 모든 채널을 감지하며, 푸시 시 모든 채널로 전송합니다
        """
        config = get_config()
        self._source_message = source_message
        self._context_channels: List[str] = []

        # Markdown을 이미지로 변환 (Issue #289)
        self._markdown_to_image_channels = set(
            getattr(config, 'markdown_to_image_channels', []) or []
        )
        self._markdown_to_image_max_chars = getattr(
            config, 'markdown_to_image_max_chars', 15000
        )

        # 분석 결과 요약만 (Issue #262): true 시 요약만 푸시, 개별 종목 상세 제외
        self._report_summary_only = getattr(config, 'report_summary_only', False)

        # 각 채널 초기화
        AstrbotSender.__init__(self, config)
        CustomWebhookSender.__init__(self, config)
        DiscordSender.__init__(self, config)
        EmailSender.__init__(self, config)
        PushoverSender.__init__(self, config)
        TelegramSender.__init__(self, config)
        
        # 설정된 모든 채널 감지
        self._available_channels = self._detect_all_channels()

        if not self._available_channels and not self._context_channels:
            logger.warning(
                "유효한 알림 채널이 설정되지 않았습니다. "
                "푸시 알림을 전송하지 않습니다"
            )
        else:
            channel_names = [ChannelDetector.get_channel_name(ch) for ch in self._available_channels]
            channel_names.extend(self._context_channels)
            logger.info(f"{len(channel_names)}개 알림 채널이 설정되었습니다: {', '.join(channel_names)}")

    def _collect_models_used(self, results: List[AnalysisResult]) -> List[str]:
        models: List[str] = []
        for result in results:
            model = normalize_model_used(getattr(result, "model_used", None))
            if model:
                models.append(model)
        return list(dict.fromkeys(models))
    
    def _detect_all_channels(self) -> List[NotificationChannel]:
        """
        설정된 모든 채널 감지

        Returns:
            설정된 채널 목록
        """
        channels = []

        # Telegram
        if self._is_telegram_configured():
            channels.append(NotificationChannel.TELEGRAM)

        # 이메일
        if self._is_email_configured():
            channels.append(NotificationChannel.EMAIL)

        # Pushover
        if self._is_pushover_configured():
            channels.append(NotificationChannel.PUSHOVER)

        # 사용자 정의 Webhook
        if self._custom_webhook_urls:
            channels.append(NotificationChannel.CUSTOM)
        
        # Discord
        if self._is_discord_configured():
            channels.append(NotificationChannel.DISCORD)
        # AstrBot
        if self._is_astrbot_configured():
            channels.append(NotificationChannel.ASTRBOT)
        return channels

    def is_available(self) -> bool:
        """알림 서비스 사용 가능 여부 확인 (채널 또는 컨텍스트 채널이 하나 이상 존재)"""
        return len(self._available_channels) > 0 or self._has_context_channel()

    def get_available_channels(self) -> List[NotificationChannel]:
        """설정된 모든 채널 반환"""
        return self._available_channels

    def get_channel_names(self) -> str:
        """설정된 모든 채널 이름 반환"""
        names = [ChannelDetector.get_channel_name(ch) for ch in self._available_channels]
        return ', '.join(names)

    # ===== Context channel =====
    def _has_context_channel(self) -> bool:
        """Return whether a source-message context reply channel is available."""
        return False

    def send_to_context(self, content: str) -> bool:
        """Send through a source-message context channel if one is supported."""
        return False
        
    def generate_daily_report(
        self,
        results: List[AnalysisResult],
        report_date: Optional[str] = None
    ) -> str:
        """
        Generate a detailed Markdown daily report.

        Args:
            results: Analysis result list.
            report_date: Report date. Defaults to today.

        Returns:
            Markdown report content.
        """
        if report_date is None:
            report_date = datetime.now().strftime('%Y-%m-%d')

        # Title.
        report_lines = [
            f"# 📅 {report_date} 주식 AI 분석 리포트",
            "",
            f"> 총 **{len(results)}**개 종목 분석 | 생성 시간: {datetime.now().strftime('%H:%M:%S')}",
            "",
            "---",
            "",
        ]

        # Sort by score descending.
        sorted_results = sorted(
            results, 
            key=lambda x: x.sentiment_score, 
            reverse=True
        )
        
        # Summary statistics based on decision_type.
        buy_count = sum(1 for r in results if getattr(r, 'decision_type', '') == 'buy')
        sell_count = sum(1 for r in results if getattr(r, 'decision_type', '') == 'sell')
        hold_count = sum(1 for r in results if getattr(r, 'decision_type', '') in ('hold', ''))
        avg_score = sum(r.sentiment_score for r in results) / len(results) if results else 0
        
        report_lines.extend([
            "## 📊 운용 제안 요약",
            "",
            "| 지표 | 값 |",
            "|------|------|",
            f"| 🟢 매수/추가매수 제안 | **{buy_count}**개 |",
            f"| 🟡 보유/관망 제안 | **{hold_count}**개 |",
            f"| 🔴 비중축소/매도 제안 | **{sell_count}**개 |",
            f"| 📈 평균 긍정 점수 | **{avg_score:.1f}**점 |",
            "",
            "---",
            "",
        ])
        
        # Issue #262: summary_only outputs only the summary and skips per-stock details.
        if self._report_summary_only:
            report_lines.extend(["## 📊 분석 결과 요약", ""])
            for r in sorted_results:
                emoji = r.get_emoji()
                report_lines.append(
                    f"{emoji} **{r.name}({r.code})**: {r.operation_advice} | "
                    f"점수 {r.sentiment_score} | {r.trend_prediction}"
                )
        else:
            report_lines.extend(["## 📈 종목별 상세 분석", ""])
            # Detailed analysis per stock.
            for result in sorted_results:
                emoji = result.get_emoji()
                confidence_stars = (
                    result.get_confidence_stars()
                    if hasattr(result, 'get_confidence_stars')
                    else '⭐⭐'
                )
                
                report_lines.extend([
                    f"### {emoji} {result.name} ({result.code})",
                    "",
                    f"**운용 제안: {result.operation_advice}** | "
                    f"**종합 점수: {result.sentiment_score}점** | "
                    f"**추세 전망: {result.trend_prediction}** | "
                    f"**신뢰도: {confidence_stars}**",
                    "",
                ])

                self._append_market_snapshot(report_lines, result)
                
                # Key points.
                if hasattr(result, 'key_points') and result.key_points:
                    report_lines.extend([
                        f"**🎯 핵심 포인트**: {result.key_points}",
                        "",
                    ])
                
                # Buy/sell rationale.
                if hasattr(result, 'buy_reason') and result.buy_reason:
                    report_lines.extend([
                        f"**💡 판단 근거**: {result.buy_reason}",
                        "",
                    ])
                
                # Trend analysis.
                if hasattr(result, 'trend_analysis') and result.trend_analysis:
                    report_lines.extend([
                        "#### 📉 추세 분석",
                        f"{result.trend_analysis}",
                        "",
                    ])
                
                # Short- and medium-term outlook.
                outlook_lines = []
                if hasattr(result, 'short_term_outlook') and result.short_term_outlook:
                    outlook_lines.append(f"- **단기(1-3일)**: {result.short_term_outlook}")
                if hasattr(result, 'medium_term_outlook') and result.medium_term_outlook:
                    outlook_lines.append(f"- **중기(1-2주)**: {result.medium_term_outlook}")
                if outlook_lines:
                    report_lines.extend([
                        "#### 🔮 시장 전망",
                        *outlook_lines,
                        "",
                    ])
                
                # Technical analysis.
                tech_lines = []
                if result.technical_analysis:
                    tech_lines.append(f"**종합**: {result.technical_analysis}")
                if hasattr(result, 'ma_analysis') and result.ma_analysis:
                    tech_lines.append(f"**이동평균**: {result.ma_analysis}")
                if hasattr(result, 'volume_analysis') and result.volume_analysis:
                    tech_lines.append(f"**거래량**: {result.volume_analysis}")
                if hasattr(result, 'pattern_analysis') and result.pattern_analysis:
                    tech_lines.append(f"**패턴**: {result.pattern_analysis}")
                if tech_lines:
                    report_lines.extend([
                        "#### 📊 기술적 분석",
                        *tech_lines,
                        "",
                    ])
                
                # Fundamental analysis.
                fund_lines = []
                if hasattr(result, 'fundamental_analysis') and result.fundamental_analysis:
                    fund_lines.append(result.fundamental_analysis)
                if hasattr(result, 'sector_position') and result.sector_position:
                    fund_lines.append(f"**업종 내 위치**: {result.sector_position}")
                if hasattr(result, 'company_highlights') and result.company_highlights:
                    fund_lines.append(f"**기업 하이라이트**: {result.company_highlights}")
                if fund_lines:
                    report_lines.extend([
                        "#### 🏢 기본적 분석",
                        *fund_lines,
                        "",
                    ])
                
                # News and sentiment.
                news_lines = []
                if result.news_summary:
                    news_lines.append(f"**뉴스 요약**: {result.news_summary}")
                if hasattr(result, 'market_sentiment') and result.market_sentiment:
                    news_lines.append(f"**시장 심리**: {result.market_sentiment}")
                if hasattr(result, 'hot_topics') and result.hot_topics:
                    news_lines.append(f"**관련 이슈**: {result.hot_topics}")
                if news_lines:
                    report_lines.extend([
                        "#### 📰 뉴스/심리",
                        *news_lines,
                        "",
                    ])
                
                # Summary analysis.
                if result.analysis_summary:
                    report_lines.extend([
                        "#### 📝 종합 분석",
                        result.analysis_summary,
                        "",
                    ])
                
                # Risk warning.
                if hasattr(result, 'risk_warning') and result.risk_warning:
                    report_lines.extend([
                        f"⚠️ **리스크 경고**: {result.risk_warning}",
                        "",
                    ])
                
                # Data source note.
                if hasattr(result, 'search_performed') and result.search_performed:
                    report_lines.append("*🔍 웹 검색 실행됨*")
                if hasattr(result, 'data_sources') and result.data_sources:
                    report_lines.append(f"*📋 데이터 출처: {result.data_sources}*")

                # Error details, if present.
                if not result.success and result.error_message:
                    report_lines.extend([
                        "",
                        f"❌ **분석 오류**: {result.error_message[:100]}",
                    ])
                
                report_lines.extend([
                    "",
                    "---",
                    "",
                ])
        
        # Footer.
        report_lines.extend([
            "",
            f"*리포트 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])
        
        return "\n".join(report_lines)
    
    @staticmethod
    def _escape_md(name: str) -> str:
        """Escape markdown special characters in stock names (e.g. *ST → \\*ST)."""
        return name.replace('*', r'\*') if name else name

    @staticmethod
    def _clean_sniper_value(value: Any) -> str:
        """Normalize sniper point values and remove redundant label prefixes."""
        if value is None:
            return 'N/A'
        if isinstance(value, (int, float)):
            return str(value)
        if not isinstance(value, str):
            return str(value)
        if not value or value == 'N/A':
            return value
        prefixes = [
            '이상 매수가:',
            '차선 매수가:',
            '손절가:',
            '목표가:',
        ]
        for prefix in prefixes:
            if value.startswith(prefix):
                return value[len(prefix):]
        return value

    def _get_signal_level(self, result: AnalysisResult) -> tuple:
        """
        Get signal level and color based on operation advice.

        Priority: advice string takes precedence over score.
        Score-based fallback is used only when advice doesn't match
        any known value.

        Returns:
            (signal_text, emoji, color_tag)
        """
        advice = result.operation_advice
        score = result.sentiment_score

        # Advice-first lookup (exact match takes priority)
        advice_map = {
            '강력 매수': ('강력 매수', '💚', '강매수'),
            '매수': ('매수', '🟢', '매수'),
            '추가매수': ('매수', '🟢', '매수'),
            '보유': ('보유', '🟡', '보유'),
            '관망': ('관망', '⚪', '관망'),
            '비중축소': ('비중축소', '🟠', '비중축소'),
            '매도': ('매도', '🔴', '매도'),
            '강력 매도': ('매도', '🔴', '매도'),
        }
        if advice in advice_map:
            return advice_map[advice]

        # Score-based fallback when advice is unrecognized
        if score >= 80:
            return ('강력 매수', '💚', '강매수')
        elif score >= 65:
            return ('매수', '🟢', '매수')
        elif score >= 55:
            return ('보유', '🟡', '보유')
        elif score >= 45:
            return ('관망', '⚪', '관망')
        elif score >= 35:
            return ('비중축소', '🟠', '비중축소')
        elif score < 35:
            return ('매도', '🔴', '매도')
        else:
            return ('관망', '⚪', '관망')
    
    def generate_dashboard_report(
        self,
        results: List[AnalysisResult],
        report_date: Optional[str] = None
    ) -> str:
        """
        Generate a detailed decision-dashboard daily report.

        Format: market overview, key information, core conclusion, data view,
        and trading plan.

        Args:
            results: Analysis result list.
            report_date: Report date. Defaults to today.

        Returns:
            Markdown decision-dashboard report.
        """
        if report_date is None:
            report_date = datetime.now().strftime('%Y-%m-%d')

        # Sort by score descending.
        sorted_results = sorted(results, key=lambda x: x.sentiment_score, reverse=True)

        # Summary statistics based on decision_type.
        buy_count = sum(1 for r in results if getattr(r, 'decision_type', '') == 'buy')
        sell_count = sum(1 for r in results if getattr(r, 'decision_type', '') == 'sell')
        hold_count = sum(1 for r in results if getattr(r, 'decision_type', '') in ('hold', ''))

        report_lines = [
            f"# 🎯 {report_date} 의사결정 대시보드",
            "",
            (
                f"> 총 **{len(results)}**개 종목 분석 | "
                f"🟢매수:{buy_count} 🟡관망:{hold_count} 🔴매도:{sell_count}"
            ),
            "",
        ]

        # === Analysis result summary (Issue #112) ===
        if results:
            report_lines.extend([
                "## 📊 분석 결과 요약",
                "",
            ])
            for r in sorted_results:
                _, signal_emoji, _ = self._get_signal_level(r)
                display_name = self._escape_md(r.name)
                report_lines.append(
                    f"{signal_emoji} **{display_name}({r.code})**: {r.operation_advice} | "
                    f"점수 {r.sentiment_score} | {r.trend_prediction}"
                )
            report_lines.extend([
                "",
                "---",
                "",
            ])

        # Per-stock decision dashboard. Issue #262 skips details in summary_only mode.
        if not self._report_summary_only:
            for result in sorted_results:
                signal_text, signal_emoji, signal_tag = self._get_signal_level(result)
                dashboard = result.dashboard if hasattr(result, 'dashboard') and result.dashboard else {}
                
                # Prefer dashboard/result names and escape Markdown-sensitive characters.
                if result.name and not result.name.startswith('종목'):
                    raw_name = result.name
                else:
                    raw_name = f'종목{result.code}'
                stock_name = self._escape_md(raw_name)
                
                report_lines.extend([
                    f"## {signal_emoji} {stock_name} ({result.code})",
                    "",
                ])
                
                # ========== Sentiment and fundamentals overview ==========
                intel = dashboard.get('intelligence', {}) if dashboard else {}
                if intel:
                    report_lines.extend([
                        "### 📰 핵심 정보",
                        "",
                    ])
                    # Sentiment summary.
                    if intel.get('sentiment_summary'):
                        report_lines.append(f"**💭 여론/심리**: {intel['sentiment_summary']}")
                    # Earnings outlook.
                    if intel.get('earnings_outlook'):
                        report_lines.append(f"**📊 실적 전망**: {intel['earnings_outlook']}")
                    # Risk alerts.
                    risk_alerts = intel.get('risk_alerts', [])
                    if risk_alerts:
                        report_lines.append("")
                        report_lines.append("**🚨 리스크 경고**:")
                        for alert in risk_alerts:
                            report_lines.append(f"- {alert}")
                    # Positive catalysts.
                    catalysts = intel.get('positive_catalysts', [])
                    if catalysts:
                        report_lines.append("")
                        report_lines.append("**✨ 긍정 촉매**:")
                        for cat in catalysts:
                            report_lines.append(f"- {cat}")
                    # Latest news.
                    if intel.get('latest_news'):
                        report_lines.append("")
                        report_lines.append(f"**📢 최신 동향**: {intel['latest_news']}")
                    report_lines.append("")

                # ========== Core conclusion ==========
                core = dashboard.get('core_conclusion', {}) if dashboard else {}
                one_sentence = core.get('one_sentence', result.analysis_summary)
                time_sense = core.get('time_sensitivity', '이번 주')
                pos_advice = core.get('position_advice', {})

                report_lines.extend([
                    "### 📌 핵심 결론",
                    "",
                    f"**{signal_emoji} {signal_text}** | {result.trend_prediction}",
                    "",
                    f"> **한 줄 판단**: {one_sentence}",
                    "",
                    f"⏰ **유효 기간**: {time_sense}",
                    "",
                ])
                # Position-aware advice.
                if pos_advice:
                    report_lines.extend([
                        "| 보유 상황 | 운용 제안 |",
                        "|---------|---------|",
                        f"| 🆕 **미보유자** | {pos_advice.get('no_position', result.operation_advice)} |",
                        f"| 💼 **보유자** | {pos_advice.get('has_position', '계속 보유')} |",
                        "",
                    ])

                self._append_market_snapshot(report_lines, result)
                
                # ========== Data view ==========
                data_persp = dashboard.get('data_perspective', {}) if dashboard else {}
                if data_persp:
                    trend_data = data_persp.get('trend_status', {})
                    price_data = data_persp.get('price_position', {})
                    vol_data = data_persp.get('volume_analysis', {})
                    chip_data = data_persp.get('chip_structure', {})
                    
                    report_lines.extend([
                        "### 📊 데이터 요약",
                        "",
                    ])
                    # Trend state.
                    if trend_data:
                        is_bullish = "✅ 예" if trend_data.get('is_bullish', False) else "❌ 아니오"
                        report_lines.extend([
                            f"**이동평균 배열**: {trend_data.get('ma_alignment', 'N/A')} | "
                            f"정배열: {is_bullish} | 추세 강도: {trend_data.get('trend_score', 'N/A')}/100",
                            "",
                        ])
                    # Price position.
                    if price_data:
                        bias_status = price_data.get('bias_status', 'N/A')
                        if bias_status == "안전":
                            bias_emoji = "✅"
                        elif bias_status == "주의":
                            bias_emoji = "⚠️"
                        else:
                            bias_emoji = "🚨"
                        report_lines.extend([
                            "| 가격 지표 | 값 |",
                            "|---------|------|",
                            f"| 현재가 | {price_data.get('current_price', 'N/A')} |",
                            f"| MA5 | {price_data.get('ma5', 'N/A')} |",
                            f"| MA10 | {price_data.get('ma10', 'N/A')} |",
                            f"| MA20 | {price_data.get('ma20', 'N/A')} |",
                            f"| 이격도(MA5) | {price_data.get('bias_ma5', 'N/A')}% {bias_emoji}{bias_status} |",
                            f"| 지지선 | {price_data.get('support_level', 'N/A')} |",
                            f"| 저항선 | {price_data.get('resistance_level', 'N/A')} |",
                            "",
                        ])
                    # Volume analysis.
                    if vol_data:
                        report_lines.extend([
                            f"**거래량**: 거래량 비율 {vol_data.get('volume_ratio', 'N/A')} "
                            f"({vol_data.get('volume_status', '')}) | "
                            f"회전율 {vol_data.get('turnover_rate', 'N/A')}%",
                            f"💡 *{vol_data.get('volume_meaning', '')}*",
                            "",
                        ])
                    # Cost distribution.
                    if chip_data:
                        chip_health = chip_data.get('chip_health', 'N/A')
                        if chip_health == "양호":
                            chip_emoji = "✅"
                        elif chip_health == "보통":
                            chip_emoji = "⚠️"
                        else:
                            chip_emoji = "🚨"
                        report_lines.extend([
                            f"**비용 분포**: 수익 비율 {chip_data.get('profit_ratio', 'N/A')} | "
                            f"평균 비용 {chip_data.get('avg_cost', 'N/A')} | "
                            f"집중도 {chip_data.get('concentration', 'N/A')} {chip_emoji}{chip_health}",
                            "",
                        ])

                # ========== Trading plan ==========
                battle = dashboard.get('battle_plan', {}) if dashboard else {}
                if battle:
                    report_lines.extend([
                        "### 🎯 운용 계획",
                        "",
                    ])
                    # Entry and exit levels.
                    sniper = battle.get('sniper_points', {})
                    if sniper:
                        secondary_buy = self._clean_sniper_value(sniper.get('secondary_buy', 'N/A'))
                        report_lines.extend([
                            "**📍 운용 가격대**",
                            "",
                            "| 유형 | 가격 |",
                            "|---------|------|",
                            f"| 🎯 이상 매수가 | {self._clean_sniper_value(sniper.get('ideal_buy', 'N/A'))} |",
                            f"| 🔵 차선 매수가 | {secondary_buy} |",
                            f"| 🛑 손절가 | {self._clean_sniper_value(sniper.get('stop_loss', 'N/A'))} |",
                            f"| 🎊 목표가 | {self._clean_sniper_value(sniper.get('take_profit', 'N/A'))} |",
                            "",
                        ])
                    # Position strategy.
                    position = battle.get('position_strategy', {})
                    if position:
                        report_lines.extend([
                            f"**💰 포지션 제안**: {position.get('suggested_position', 'N/A')}",
                            f"- 진입 전략: {position.get('entry_plan', 'N/A')}",
                            f"- 리스크 관리: {position.get('risk_control', 'N/A')}",
                            "",
                        ])
                    # Checklist.
                    checklist = battle.get('action_checklist', []) if battle else []
                    if checklist:
                        report_lines.extend([
                            "**✅ 체크리스트**",
                            "",
                        ])
                        for item in checklist:
                            report_lines.append(f"- {item}")
                        report_lines.append("")
                
                # Fallback format when dashboard data is missing.
                if not dashboard:
                    # Operation rationale.
                    if result.buy_reason:
                        report_lines.extend([
                            f"**💡 판단 근거**: {result.buy_reason}",
                            "",
                        ])
                    # Risk warning.
                    if result.risk_warning:
                        report_lines.extend([
                            f"**⚠️ 리스크 경고**: {result.risk_warning}",
                            "",
                        ])
                    # Technical analysis.
                    if result.ma_analysis or result.volume_analysis:
                        report_lines.extend([
                            "### 📊 기술적 분석",
                            "",
                        ])
                        if result.ma_analysis:
                            report_lines.append(f"**이동평균**: {result.ma_analysis}")
                        if result.volume_analysis:
                            report_lines.append(f"**거래량**: {result.volume_analysis}")
                        report_lines.append("")
                    # News.
                    if result.news_summary:
                        report_lines.extend([
                            "### 📰 뉴스",
                            f"{result.news_summary}",
                            "",
                        ])
                
                report_lines.extend([
                    "---",
                    "",
                ])
        
        # Footer.
        report_lines.extend([
            "",
            f"*리포트 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])
        
        return "\n".join(report_lines)
    
    def generate_single_stock_report(self, result: AnalysisResult) -> str:
        """
        Generate a single-stock report for single-stock push mode.

        The format is compact but includes the key information needed for
        immediate per-stock notifications.

        Args:
            result: Single-stock analysis result.

        Returns:
            Markdown single-stock report.
        """
        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        signal_text, signal_emoji, _ = self._get_signal_level(result)
        dashboard = result.dashboard if hasattr(result, 'dashboard') and result.dashboard else {}
        core = dashboard.get('core_conclusion', {}) if dashboard else {}
        battle = dashboard.get('battle_plan', {}) if dashboard else {}
        intel = dashboard.get('intelligence', {}) if dashboard else {}
        
        # Escape Markdown-sensitive characters in stock names.
        raw_name = result.name if result.name and not result.name.startswith('종목') else f'종목{result.code}'
        stock_name = self._escape_md(raw_name)
        
        lines = [
            f"## {signal_emoji} {stock_name} ({result.code})",
            "",
            f"> {report_date} | 점수: **{result.sentiment_score}** | {result.trend_prediction}",
            "",
        ]

        self._append_market_snapshot(lines, result)
        
        # Core decision.
        one_sentence = core.get('one_sentence', result.analysis_summary) if core else result.analysis_summary
        if one_sentence:
            lines.extend([
                "### 📌 핵심 결론",
                "",
                f"**{signal_text}**: {one_sentence}",
                "",
            ])

        # Key information: sentiment and fundamentals.
        info_added = False
        if intel:
            if intel.get('earnings_outlook'):
                if not info_added:
                    lines.append("### 📰 핵심 정보")
                    lines.append("")
                    info_added = True
                lines.append(f"📊 **실적 전망**: {intel['earnings_outlook'][:100]}")

            if intel.get('sentiment_summary'):
                if not info_added:
                    lines.append("### 📰 핵심 정보")
                    lines.append("")
                    info_added = True
                lines.append(f"💭 **여론/심리**: {intel['sentiment_summary'][:80]}")

            # Risk alerts.
            risks = intel.get('risk_alerts', [])
            if risks:
                if not info_added:
                    lines.append("### 📰 핵심 정보")
                    lines.append("")
                    info_added = True
                lines.append("")
                lines.append("🚨 **리스크 경고**:")
                for risk in risks[:3]:
                    lines.append(f"- {risk[:60]}")

            # Positive catalysts.
            catalysts = intel.get('positive_catalysts', [])
            if catalysts:
                lines.append("")
                lines.append("✨ **긍정 촉매**:")
                for cat in catalysts[:3]:
                    lines.append(f"- {cat[:60]}")
        
        if info_added:
            lines.append("")
        
        # Entry and exit levels.
        sniper = battle.get('sniper_points', {}) if battle else {}
        if sniper:
            lines.extend([
                "### 🎯 운용 가격대",
                "",
                "| 매수가 | 손절가 | 목표가 |",
                "|------|------|------|",
            ])
            ideal_buy = sniper.get('ideal_buy', '-')
            stop_loss = sniper.get('stop_loss', '-')
            take_profit = sniper.get('take_profit', '-')
            lines.append(f"| {ideal_buy} | {stop_loss} | {take_profit} |")
            lines.append("")
        
        # Position advice.
        pos_advice = core.get('position_advice', {}) if core else {}
        if pos_advice:
            lines.extend([
                "### 💼 보유 상황별 제안",
                "",
                f"- 🆕 **미보유자**: {pos_advice.get('no_position', result.operation_advice)}",
                f"- 💼 **보유자**: {pos_advice.get('has_position', '계속 보유')}",
                "",
            ])
        
        lines.append("---")
        model_used = normalize_model_used(getattr(result, "model_used", None))
        if model_used:
            lines.append(f"*분석 모델: {model_used}*")
        lines.append("*AI 생성 결과이며 참고용입니다. 투자 조언이 아닙니다.*")

        return "\n".join(lines)

    # Display name mapping for realtime data sources
    _SOURCE_DISPLAY_NAMES = {
        "pykrx": "PyKRX",
        "naver": "Naver Finance",
        "yfinance": "Yahoo Finance",
        "fallback": "보조 데이터",
    }

    def _append_market_snapshot(self, lines: List[str], result: AnalysisResult) -> None:
        snapshot = getattr(result, 'market_snapshot', None)
        if not snapshot:
            return

        lines.extend([
            "### 📈 당일 시세",
            "",
            "| 종가 | 전일 종가 | 시가 | 고가 | 저가 | 등락률 | "
            "등락액 | 변동폭 | 거래량 | 거래대금 |",
            "|------|------|------|------|------|-------|-------|------|--------|--------|",
            f"| {snapshot.get('close', 'N/A')} | {snapshot.get('prev_close', 'N/A')} | "
            f"{snapshot.get('open', 'N/A')} | {snapshot.get('high', 'N/A')} | "
            f"{snapshot.get('low', 'N/A')} | {snapshot.get('pct_chg', 'N/A')} | "
            f"{snapshot.get('change_amount', 'N/A')} | {snapshot.get('amplitude', 'N/A')} | "
            f"{snapshot.get('volume', 'N/A')} | {snapshot.get('amount', 'N/A')} |",
        ])

        if "price" in snapshot:
            raw_source = snapshot.get('source', 'N/A')
            display_source = self._SOURCE_DISPLAY_NAMES.get(raw_source, raw_source)
            lines.extend([
                "",
                "| 현재가 | 거래량 비율 | 회전율 | 시세 출처 |",
                "|-------|------|--------|----------|",
                f"| {snapshot.get('price', 'N/A')} | {snapshot.get('volume_ratio', 'N/A')} | "
                f"{snapshot.get('turnover_rate', 'N/A')} | {display_source} |",
            ])

        lines.append("")

    def _should_use_image_for_channel(
        self, channel: NotificationChannel, image_bytes: Optional[bytes]
    ) -> bool:
        """
        Decide whether to send as image for the given channel (Issue #289).

        Fallback rules (send as Markdown text instead of image):
        - image_bytes is None: conversion failed / imgkit not installed / content over max_chars
        """
        if channel.value not in self._markdown_to_image_channels or image_bytes is None:
            return False
        return True

    def send(
        self,
        content: str,
        email_stock_codes: Optional[List[str]] = None,
        email_send_to_all: bool = False
    ) -> bool:
        """
        Send content to all configured channels.

        Iterates through configured channels and sends the message to each one.

        Fallback rules (Markdown-to-image, Issue #289):
        - When image_bytes is None (conversion failed / imgkit not installed /
          content over max_chars): all channels configured for image will send
          as Markdown text instead.

        Args:
            content: Message content in Markdown format.
            email_stock_codes: Optional stock code list for email-group routing.
            email_send_to_all: Whether to send email to every configured recipient.

        Returns:
            Whether at least one channel was sent successfully.
        """
        context_success = self.send_to_context(content)

        if not self._available_channels:
            if context_success:
                logger.info("Sent through the message context channel with no other channels configured")
                return True
            logger.warning("Notification service is unavailable; skipping send")
            return False

        # Markdown to image (Issue #289): convert once if any channel needs it.
        # Per-channel decision via _should_use_image_for_channel (see send() docstring for fallback rules).
        image_bytes = None
        channels_needing_image = {
            ch for ch in self._available_channels
            if ch.value in self._markdown_to_image_channels
        }
        if channels_needing_image:
            from src.md2img import markdown_to_image
            image_bytes = markdown_to_image(
                content, max_chars=self._markdown_to_image_max_chars
            )
            if image_bytes:
                logger.info("Markdown was converted to an image; sending image to %s",
                            [ch.value for ch in channels_needing_image])
            elif channels_needing_image:
                try:
                    from src.config import get_config
                    engine = getattr(get_config(), "md2img_engine", "wkhtmltoimage")
                except Exception:
                    engine = "wkhtmltoimage"
                hint = (
                    "npm i -g markdown-to-file" if engine == "markdown-to-file"
                    else "wkhtmltopdf (apt install wkhtmltopdf / brew install wkhtmltopdf)"
                )
                logger.warning(
                    "Markdown-to-image conversion failed; falling back to text. "
                    "Check MARKDOWN_TO_IMAGE_CHANNELS and install %s",
                    hint,
                )

        channel_names = self.get_channel_names()
        logger.info(f"Sending notification to {len(self._available_channels)} channel(s): {channel_names}")

        success_count = 0
        fail_count = 0

        for channel in self._available_channels:
            channel_name = ChannelDetector.get_channel_name(channel)
            use_image = self._should_use_image_for_channel(channel, image_bytes)
            try:
                if channel == NotificationChannel.TELEGRAM:
                    if use_image:
                        result = self._send_telegram_photo(image_bytes)
                    else:
                        result = self.send_to_telegram(content)
                elif channel == NotificationChannel.EMAIL:
                    receivers = None
                    if email_send_to_all and self._stock_email_groups:
                        receivers = self.get_all_email_receivers()
                    elif email_stock_codes and self._stock_email_groups:
                        receivers = self.get_receivers_for_stocks(email_stock_codes)
                    if use_image:
                        result = self._send_email_with_inline_image(
                            image_bytes, receivers=receivers
                        )
                    else:
                        result = self.send_to_email(content, receivers=receivers)
                elif channel == NotificationChannel.PUSHOVER:
                    result = self.send_to_pushover(content)
                elif channel == NotificationChannel.CUSTOM:
                    if use_image:
                        result = self._send_custom_webhook_image(
                            image_bytes, fallback_content=content
                        )
                    else:
                        result = self.send_to_custom(content)
                elif channel == NotificationChannel.DISCORD:
                    result = self.send_to_discord(content)
                elif channel == NotificationChannel.ASTRBOT:
                    result = self.send_to_astrbot(content)
                else:
                    logger.warning(f"Unsupported notification channel: {channel}")
                    result = False

                if result:
                    success_count += 1
                else:
                    fail_count += 1

            except Exception as e:
                logger.error(f"{channel_name} send failed: {e}")
                fail_count += 1

        logger.info(f"Notification send completed: success={success_count}, failed={fail_count}")
        return success_count > 0 or context_success
   
    def save_report_to_file(
        self, 
        content: str, 
        filename: Optional[str] = None
    ) -> str:
        """
        Save a report to a local file.

        Args:
            content: Report content.
            filename: Optional filename. Defaults to a date-based name.

        Returns:
            Saved file path.
        """
        from pathlib import Path
        
        if filename is None:
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"report_{date_str}.md"
        
        # Ensure the project reports directory exists.
        reports_dir = Path(__file__).parent.parent / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Report saved to: {filepath}")
        return str(filepath)


class NotificationBuilder:
    """
    Notification message builder.

    Provides convenience methods for common notification formats.
    """
    
    @staticmethod
    def build_simple_alert(
        title: str,
        content: str,
        alert_type: str = "info"
    ) -> str:
        """
        Build a simple alert message.

        Args:
            title: Alert title.
            content: Alert content.
            alert_type: Alert type: info, warning, error, or success.
        """
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
        }
        emoji = emoji_map.get(alert_type, "📢")
        
        return f"{emoji} **{title}**\n\n{content}"
    
    @staticmethod
    def build_stock_summary(results: List[AnalysisResult]) -> str:
        """
        Build a compact stock summary.

        Intended for quick notifications.
        """
        lines = ["📊 **오늘 관심 종목 요약**", ""]
        
        for r in sorted(results, key=lambda x: x.sentiment_score, reverse=True):
            emoji = r.get_emoji()
            lines.append(f"{emoji} {r.name}({r.code}): {r.operation_advice} | 점수 {r.sentiment_score}")
        
        return "\n".join(lines)


# Convenience helpers.
def get_notification_service() -> NotificationService:
    """Return a notification service instance."""
    return NotificationService()


def send_daily_report(results: List[AnalysisResult]) -> bool:
    """
    Send a daily report.

    Detects configured channels and pushes the generated report.
    """
    service = get_notification_service()
    
    # Generate report.
    report = service.generate_daily_report(results)
    
    # Save locally.
    service.save_report_to_file(report)
    
    # Send to configured channels.
    return service.send(report)


if __name__ == "__main__":
    # Manual test code.
    logging.basicConfig(level=logging.DEBUG)
    
    # Sample analysis results.
    test_results = [
        AnalysisResult(
            code='005930',
            name='삼성전자',
            sentiment_score=75,
            trend_prediction='강세',
            analysis_summary='기술 지표가 강하고 뉴스 흐름도 긍정적입니다.',
            operation_advice='매수',
            technical_analysis=(
                '거래량을 동반해 MA20을 돌파했고 '
                'MACD 골든크로스가 발생했습니다.'
            ),
            news_summary='실적과 주주환원 관련 긍정 뉴스가 확인되었습니다.',
        ),
        AnalysisResult(
            code='035720',
            name='카카오',
            sentiment_score=45,
            trend_prediction='횡보',
            analysis_summary='박스권 흐름으로 방향성 확인이 필요합니다.',
            operation_advice='보유',
            technical_analysis='이동평균선이 수렴하고 거래량이 줄었습니다.',
            news_summary='최근 중대한 뉴스는 확인되지 않았습니다.',
        ),
        AnalysisResult(
            code='MSFT',
            name='Microsoft',
            sentiment_score=35,
            trend_prediction='약세',
            analysis_summary='기술 흐름이 약해져 리스크 관리가 필요합니다.',
            operation_advice='매도',
            technical_analysis='MA10 지지선을 이탈했고 거래량 모멘텀이 부족합니다.',
            news_summary='업종 경쟁 심화와 마진 압박 우려가 있습니다.',
        ),
    ]
    
    service = NotificationService()
    
    # Show detected channels.
    print("=== 알림 채널 점검 ===")
    print(f"현재 채널: {service.get_channel_names()}")
    print(f"채널 목록: {service.get_available_channels()}")
    print(f"서비스 사용 가능: {service.is_available()}")

    # Generate daily report.
    print("\n=== 일일 리포트 생성 테스트 ===")
    report = service.generate_daily_report(test_results)
    print(report)
    
    # Save to file.
    print("\n=== 리포트 저장 ===")
    filepath = service.save_report_to_file(report)
    print(f"저장 성공: {filepath}")

    # Send test.
    if service.is_available():
        print(f"\n=== 발송 테스트({service.get_channel_names()}) ===")
        success = service.send(report)
        print(f"발송 결과: {'성공' if success else '실패'}")
    else:
        print("\n알림 채널이 설정되지 않아 발송 테스트를 건너뜁니다.")
