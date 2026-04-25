# -*- coding: utf-8 -*-
"""
Trend trading analyzer based on the configured trading principles.

Core principles:
1. Strict entry discipline: avoid chasing overextended moves.
2. Trend following: prefer MA5 > MA10 > MA20 alignment.
3. Efficiency first: favor stocks with healthy volume and positioning.
4. Entry preference: buy pullbacks near MA5/MA10 support.

Technical standards:
- Bullish alignment: MA5 > MA10 > MA20.
- Bias: (Close - MA5) / MA5 < 5%.
- Volume pattern: lower-volume pullbacks are preferred.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum

import pandas as pd
import numpy as np

from src.config import get_config

logger = logging.getLogger(__name__)


class TrendStatus(Enum):
    """Trend status values."""
    STRONG_BULL = "강한 상승 추세"      # MA5 > MA10 > MA20 with widening spread.
    BULL = "상승 배열"                  # MA5 > MA10 > MA20.
    WEAK_BULL = "약한 상승 추세"        # MA5 > MA10 but MA10 <= MA20.
    CONSOLIDATION = "횡보"              # Moving averages are tangled.
    WEAK_BEAR = "약한 하락 추세"        # MA5 < MA10 but MA10 >= MA20.
    BEAR = "하락 배열"                  # MA5 < MA10 < MA20.
    STRONG_BEAR = "강한 하락 추세"      # MA5 < MA10 < MA20 with widening spread.


class VolumeStatus(Enum):
    """Volume status values."""
    HEAVY_VOLUME_UP = "거래량 증가 상승"       # Price and volume rise together.
    HEAVY_VOLUME_DOWN = "거래량 증가 하락"     # Heavy-volume selloff.
    SHRINK_VOLUME_UP = "거래량 감소 상승"      # Low-volume advance.
    SHRINK_VOLUME_DOWN = "거래량 감소 조정"    # Lower-volume pullback.
    NORMAL = "거래량 정상"


class BuySignal(Enum):
    """Trading signal values."""
    STRONG_BUY = "강력 매수"       # Multiple conditions are satisfied.
    BUY = "매수"                  # Core conditions are satisfied.
    HOLD = "보유"                 # Existing positions can continue.
    WAIT = "관망"                 # Wait for a better setup.
    SELL = "매도"                 # Trend is weakening.
    STRONG_SELL = "강력 매도"      # Trend structure is broken.


class MACDStatus(Enum):
    """MACD status values."""
    GOLDEN_CROSS_ZERO = "0선 위 골든크로스"      # DIF crosses above DEA above zero.
    GOLDEN_CROSS = "골든크로스"                 # DIF crosses above DEA.
    BULLISH = "상승 우위"                       # DIF > DEA > 0.
    CROSSING_UP = "0선 상향 돌파"               # DIF crosses above zero.
    CROSSING_DOWN = "0선 하향 이탈"             # DIF crosses below zero.
    BEARISH = "하락 우위"                       # DIF < DEA < 0.
    DEATH_CROSS = "데드크로스"                  # DIF crosses below DEA.


class RSIStatus(Enum):
    """RSI status values."""
    OVERBOUGHT = "과매수"        # RSI > 70.
    STRONG_BUY = "강세 매수권"   # 50 < RSI < 70.
    NEUTRAL = "중립"            # 40 <= RSI <= 60.
    WEAK = "약세"               # 30 < RSI < 40.
    OVERSOLD = "과매도"         # RSI < 30.


@dataclass
class TrendAnalysisResult:
    """Trend analysis result."""
    code: str
    
    # Trend assessment.
    trend_status: TrendStatus = TrendStatus.CONSOLIDATION
    ma_alignment: str = ""           # Moving-average alignment description.
    trend_strength: float = 0.0      # Trend strength, 0-100.
    
    # Moving average data.
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    current_price: float = 0.0
    
    # Bias from moving averages.
    bias_ma5: float = 0.0            # (Close - MA5) / MA5 * 100
    bias_ma10: float = 0.0
    bias_ma20: float = 0.0
    
    # Volume analysis.
    volume_status: VolumeStatus = VolumeStatus.NORMAL
    volume_ratio_5d: float = 0.0     # Current volume divided by 5-day average volume.
    volume_trend: str = ""           # Volume trend description.
    
    # Support and resistance.
    support_ma5: bool = False        # Whether MA5 acts as support.
    support_ma10: bool = False       # Whether MA10 acts as support.
    resistance_levels: List[float] = field(default_factory=list)
    support_levels: List[float] = field(default_factory=list)

    # MACD indicator.
    macd_dif: float = 0.0          # DIF fast line.
    macd_dea: float = 0.0          # DEA slow line.
    macd_bar: float = 0.0           # MACD histogram.
    macd_status: MACDStatus = MACDStatus.BULLISH
    macd_signal: str = ""            # MACD signal description.

    # RSI indicator.
    rsi_6: float = 0.0              # RSI(6), short term.
    rsi_12: float = 0.0             # RSI(12), medium term.
    rsi_24: float = 0.0             # RSI(24), long term.
    rsi_status: RSIStatus = RSIStatus.NEUTRAL
    rsi_signal: str = ""              # RSI signal description.

    # Trading signal.
    buy_signal: BuySignal = BuySignal.WAIT
    signal_score: int = 0            # Composite score, 0-100.
    signal_reasons: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'trend_status': self.trend_status.value,
            'ma_alignment': self.ma_alignment,
            'trend_strength': self.trend_strength,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'ma60': self.ma60,
            'current_price': self.current_price,
            'bias_ma5': self.bias_ma5,
            'bias_ma10': self.bias_ma10,
            'bias_ma20': self.bias_ma20,
            'volume_status': self.volume_status.value,
            'volume_ratio_5d': self.volume_ratio_5d,
            'volume_trend': self.volume_trend,
            'support_ma5': self.support_ma5,
            'support_ma10': self.support_ma10,
            'buy_signal': self.buy_signal.value,
            'signal_score': self.signal_score,
            'signal_reasons': self.signal_reasons,
            'risk_factors': self.risk_factors,
            'macd_dif': self.macd_dif,
            'macd_dea': self.macd_dea,
            'macd_bar': self.macd_bar,
            'macd_status': self.macd_status.value,
            'macd_signal': self.macd_signal,
            'rsi_6': self.rsi_6,
            'rsi_12': self.rsi_12,
            'rsi_24': self.rsi_24,
            'rsi_status': self.rsi_status.value,
            'rsi_signal': self.rsi_signal,
        }


class StockTrendAnalyzer:
    """
    Stock trend analyzer.

    Implements the configured trading principles:
    1. Trend assessment using MA5 > MA10 > MA20 alignment.
    2. Bias checks to avoid chasing moves far above MA5.
    3. Volume analysis that prefers lower-volume pullbacks.
    4. Entry recognition near MA5/MA10 support.
    5. MACD trend confirmation and crossover signals.
    6. RSI overbought/oversold assessment.
    """
    
    # Trading parameters. BIAS_THRESHOLD is read from Config in _generate_signal.
    VOLUME_SHRINK_RATIO = 0.7   # Low-volume threshold.
    VOLUME_HEAVY_RATIO = 1.5    # Heavy-volume threshold.
    MA_SUPPORT_TOLERANCE = 0.02  # MA support tolerance, 2%.

    # MACD parameters, standard 12/26/9.
    MACD_FAST = 12              # Fast-line period.
    MACD_SLOW = 26             # Slow-line period.
    MACD_SIGNAL = 9             # Signal-line period.

    # RSI parameters.
    RSI_SHORT = 6               # Short-term RSI period.
    RSI_MID = 12               # Medium-term RSI period.
    RSI_LONG = 24              # Long-term RSI period.
    RSI_OVERBOUGHT = 70        # Overbought threshold.
    RSI_OVERSOLD = 30          # Oversold threshold.
    
    def __init__(self):
        """Initialize the analyzer."""
        pass
    
    def analyze(self, df: pd.DataFrame, code: str) -> TrendAnalysisResult:
        """
        Analyze the stock trend.
        
        Args:
            df: DataFrame containing OHLCV data.
            code: Stock code.
            
        Returns:
            Trend analysis result.
        """
        result = TrendAnalysisResult(code=code)
        
        if df is None or df.empty or len(df) < 20:
            logger.warning("%s has insufficient data for trend analysis", code)
            result.risk_factors.append("데이터가 부족해 분석을 완료할 수 없습니다")
            return result
        
        # Ensure data is sorted by date.
        df = df.sort_values('date').reset_index(drop=True)
        
        # Calculate moving averages.
        df = self._calculate_mas(df)

        # Calculate MACD and RSI.
        df = self._calculate_macd(df)
        df = self._calculate_rsi(df)

        # Get the latest row.
        latest = df.iloc[-1]
        result.current_price = float(latest['close'])
        result.ma5 = float(latest['MA5'])
        result.ma10 = float(latest['MA10'])
        result.ma20 = float(latest['MA20'])
        result.ma60 = float(latest.get('MA60', 0))

        # 1. Trend assessment.
        self._analyze_trend(df, result)

        # 2. Bias calculation.
        self._calculate_bias(result)

        # 3. Volume analysis.
        self._analyze_volume(df, result)

        # 4. Support and resistance analysis.
        self._analyze_support_resistance(df, result)

        # 5. MACD analysis.
        self._analyze_macd(df, result)

        # 6. RSI analysis.
        self._analyze_rsi(df, result)

        # 7. Generate trading signal.
        self._generate_signal(result)

        return result
    
    def _calculate_mas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate moving averages."""
        df = df.copy()
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        if len(df) >= 60:
            df['MA60'] = df['close'].rolling(window=60).mean()
        else:
            df['MA60'] = df['MA20']  # Use MA20 as fallback when data is insufficient.
        return df

    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the MACD indicator.

        Formula:
- EMA(12): 12-day exponential moving average.
- EMA(26): 26-day exponential moving average.
        - DIF = EMA(12) - EMA(26)
        - DEA = EMA(DIF, 9)
        - MACD = (DIF - DEA) * 2
        """
        df = df.copy()

        # Calculate fast and slow EMA lines.
        ema_fast = df['close'].ewm(span=self.MACD_FAST, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.MACD_SLOW, adjust=False).mean()

        # Calculate the DIF line.
        df['MACD_DIF'] = ema_fast - ema_slow

        # Calculate the DEA signal line.
        df['MACD_DEA'] = df['MACD_DIF'].ewm(span=self.MACD_SIGNAL, adjust=False).mean()

        # Calculate the histogram.
        df['MACD_BAR'] = (df['MACD_DIF'] - df['MACD_DEA']) * 2

        return df

    def _calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the RSI indicator.

        Formula:
- RS = average gain / average loss.
        - RSI = 100 - (100 / (1 + RS))
        """
        df = df.copy()

        for period in [self.RSI_SHORT, self.RSI_MID, self.RSI_LONG]:
            # Calculate price changes.
            delta = df['close'].diff()

            # Separate gains and losses.
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # Calculate average gains and losses.
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()

            # Calculate RS and RSI.
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # Fill NaN values.
            rsi = rsi.fillna(50)  # Default neutral value.

            # Add to DataFrame.
            col_name = f'RSI_{period}'
            df[col_name] = rsi

        return df
    
    def _analyze_trend(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        Analyze trend status.
        
        Core logic: assess moving-average alignment and trend strength.
        """
        ma5, ma10, ma20 = result.ma5, result.ma10, result.ma20
        
        # Assess moving-average alignment.
        if ma5 > ma10 > ma20:
            # Check whether the spread is widening.
            prev = df.iloc[-5] if len(df) >= 5 else df.iloc[-1]
            prev_spread = (prev['MA5'] - prev['MA20']) / prev['MA20'] * 100 if prev['MA20'] > 0 else 0
            curr_spread = (ma5 - ma20) / ma20 * 100 if ma20 > 0 else 0
            
            if curr_spread > prev_spread and curr_spread > 5:
                result.trend_status = TrendStatus.STRONG_BULL
                result.ma_alignment = "강한 상승 배열, 이동평균선이 위로 벌어지는 중"
                result.trend_strength = 90
            else:
                result.trend_status = TrendStatus.BULL
                result.ma_alignment = "상승 배열 MA5>MA10>MA20"
                result.trend_strength = 75
                
        elif ma5 > ma10 and ma10 <= ma20:
            result.trend_status = TrendStatus.WEAK_BULL
            result.ma_alignment = "약한 상승 추세, MA5>MA10 이지만 MA10≤MA20"
            result.trend_strength = 55
            
        elif ma5 < ma10 < ma20:
            prev = df.iloc[-5] if len(df) >= 5 else df.iloc[-1]
            prev_spread = (prev['MA20'] - prev['MA5']) / prev['MA5'] * 100 if prev['MA5'] > 0 else 0
            curr_spread = (ma20 - ma5) / ma5 * 100 if ma5 > 0 else 0
            
            if curr_spread > prev_spread and curr_spread > 5:
                result.trend_status = TrendStatus.STRONG_BEAR
                result.ma_alignment = "강한 하락 배열, 이동평균선이 아래로 벌어지는 중"
                result.trend_strength = 10
            else:
                result.trend_status = TrendStatus.BEAR
                result.ma_alignment = "하락 배열 MA5<MA10<MA20"
                result.trend_strength = 25
                
        elif ma5 < ma10 and ma10 >= ma20:
            result.trend_status = TrendStatus.WEAK_BEAR
            result.ma_alignment = "약한 하락 추세, MA5<MA10 이지만 MA10≥MA20"
            result.trend_strength = 40
            
        else:
            result.trend_status = TrendStatus.CONSOLIDATION
            result.ma_alignment = "이동평균선이 얽혀 추세가 불명확합니다"
            result.trend_strength = 50
    
    def _calculate_bias(self, result: TrendAnalysisResult) -> None:
        """
        Calculate bias.
        
        Bias = (current price - moving average) / moving average * 100%.
        
        Strict entry rule: avoid chasing when bias is above 5%.
        """
        price = result.current_price
        
        if result.ma5 > 0:
            result.bias_ma5 = (price - result.ma5) / result.ma5 * 100
        if result.ma10 > 0:
            result.bias_ma10 = (price - result.ma10) / result.ma10 * 100
        if result.ma20 > 0:
            result.bias_ma20 = (price - result.ma20) / result.ma20 * 100
    
    def _analyze_volume(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        Analyze volume.
        
        Preference: low-volume pullback > high-volume advance > low-volume advance > high-volume decline.
        """
        if len(df) < 5:
            return
        
        latest = df.iloc[-1]
        vol_5d_avg = df['volume'].iloc[-6:-1].mean()
        
        if vol_5d_avg > 0:
            result.volume_ratio_5d = float(latest['volume']) / vol_5d_avg
        
        # Assess price change.
        prev_close = df.iloc[-2]['close']
        price_change = (latest['close'] - prev_close) / prev_close * 100
        
        # Assess volume status.
        if result.volume_ratio_5d >= self.VOLUME_HEAVY_RATIO:
            if price_change > 0:
                result.volume_status = VolumeStatus.HEAVY_VOLUME_UP
                result.volume_trend = "거래량 증가와 함께 상승해 매수세가 강합니다"
            else:
                result.volume_status = VolumeStatus.HEAVY_VOLUME_DOWN
                result.volume_trend = "거래량 증가 하락으로 리스크에 유의해야 합니다"
        elif result.volume_ratio_5d <= self.VOLUME_SHRINK_RATIO:
            if price_change > 0:
                result.volume_status = VolumeStatus.SHRINK_VOLUME_UP
                result.volume_trend = "거래량 감소 상승으로 상승 동력이 제한적입니다"
            else:
                result.volume_status = VolumeStatus.SHRINK_VOLUME_DOWN
                result.volume_trend = "거래량 감소 조정으로 건전한 눌림목 가능성이 있습니다"
        else:
            result.volume_status = VolumeStatus.NORMAL
            result.volume_trend = "거래량이 정상 범위입니다"
    
    def _analyze_support_resistance(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        Analyze support and resistance levels.
        
        Entry preference: pullback receives support near MA5/MA10.
        """
        price = result.current_price
        
        # Check whether MA5 provides support.
        if result.ma5 > 0:
            ma5_distance = abs(price - result.ma5) / result.ma5
            if ma5_distance <= self.MA_SUPPORT_TOLERANCE and price >= result.ma5:
                result.support_ma5 = True
                result.support_levels.append(result.ma5)
        
        # Check whether MA10 provides support.
        if result.ma10 > 0:
            ma10_distance = abs(price - result.ma10) / result.ma10
            if ma10_distance <= self.MA_SUPPORT_TOLERANCE and price >= result.ma10:
                result.support_ma10 = True
                if result.ma10 not in result.support_levels:
                    result.support_levels.append(result.ma10)
        
        # Treat MA20 as an important support level.
        if result.ma20 > 0 and price >= result.ma20:
            result.support_levels.append(result.ma20)
        
        # Treat recent highs as resistance.
        if len(df) >= 20:
            recent_high = df['high'].iloc[-20:].max()
            if recent_high > price:
                result.resistance_levels.append(recent_high)

    def _analyze_macd(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        Analyze the MACD indicator.

        Core signals:
- Golden cross above zero: strongest buy signal.
- Golden cross: DIF crosses above DEA.
- Death cross: DIF crosses below DEA.
        """
        if len(df) < self.MACD_SLOW:
            result.macd_signal = "데이터 부족"
            return

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # Get MACD data.
        result.macd_dif = float(latest['MACD_DIF'])
        result.macd_dea = float(latest['MACD_DEA'])
        result.macd_bar = float(latest['MACD_BAR'])

        # Detect MACD crosses.
        prev_dif_dea = prev['MACD_DIF'] - prev['MACD_DEA']
        curr_dif_dea = result.macd_dif - result.macd_dea

        # Golden cross: DIF crosses above DEA.
        is_golden_cross = prev_dif_dea <= 0 and curr_dif_dea > 0

        # Death cross: DIF crosses below DEA.
        is_death_cross = prev_dif_dea >= 0 and curr_dif_dea < 0

        # Zero-line cross.
        prev_zero = prev['MACD_DIF']
        curr_zero = result.macd_dif
        is_crossing_up = prev_zero <= 0 and curr_zero > 0
        is_crossing_down = prev_zero >= 0 and curr_zero < 0

        # Assess MACD status.
        if is_golden_cross and curr_zero > 0:
            result.macd_status = MACDStatus.GOLDEN_CROSS_ZERO
            result.macd_signal = "⭐ 0선 위 골든크로스로 강한 매수 신호입니다"
        elif is_crossing_up:
            result.macd_status = MACDStatus.CROSSING_UP
            result.macd_signal = "⚡ DIF가 0선을 상향 돌파해 추세가 강해지고 있습니다"
        elif is_golden_cross:
            result.macd_status = MACDStatus.GOLDEN_CROSS
            result.macd_signal = "✅ 골든크로스로 추세가 위를 향합니다"
        elif is_death_cross:
            result.macd_status = MACDStatus.DEATH_CROSS
            result.macd_signal = "❌ 데드크로스로 추세가 아래를 향합니다"
        elif is_crossing_down:
            result.macd_status = MACDStatus.CROSSING_DOWN
            result.macd_signal = "⚠️ DIF가 0선을 하향 이탈해 추세가 약해지고 있습니다"
        elif result.macd_dif > 0 and result.macd_dea > 0:
            result.macd_status = MACDStatus.BULLISH
            result.macd_signal = "✓ 상승 우위가 이어지고 있습니다"
        elif result.macd_dif < 0 and result.macd_dea < 0:
            result.macd_status = MACDStatus.BEARISH
            result.macd_signal = "⚠ 하락 우위가 이어지고 있습니다"
        else:
            result.macd_status = MACDStatus.BULLISH
            result.macd_signal = "MACD 중립 구간입니다"

    def _analyze_rsi(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        Analyze the RSI indicator.

        Core checks:
- RSI > 70: overbought, avoid chasing.
- RSI < 30: oversold, watch for rebounds.
- 40-60: neutral zone.
        """
        if len(df) < self.RSI_LONG:
            result.rsi_signal = "데이터 부족"
            return

        latest = df.iloc[-1]

        # Get RSI data.
        result.rsi_6 = float(latest[f'RSI_{self.RSI_SHORT}'])
        result.rsi_12 = float(latest[f'RSI_{self.RSI_MID}'])
        result.rsi_24 = float(latest[f'RSI_{self.RSI_LONG}'])

        # Use medium-term RSI(12) as the primary signal.
        rsi_mid = result.rsi_12

        # Assess RSI status.
        if rsi_mid > self.RSI_OVERBOUGHT:
            result.rsi_status = RSIStatus.OVERBOUGHT
            result.rsi_signal = f"⚠️ RSI 과매수({rsi_mid:.1f}>70)로 단기 조정 위험이 높습니다"
        elif rsi_mid > 60:
            result.rsi_status = RSIStatus.STRONG_BUY
            result.rsi_signal = f"✅ RSI 강세({rsi_mid:.1f})로 매수세가 충분합니다"
        elif rsi_mid >= 40:
            result.rsi_status = RSIStatus.NEUTRAL
            result.rsi_signal = f"RSI 중립({rsi_mid:.1f})으로 횡보 정리 중입니다"
        elif rsi_mid >= self.RSI_OVERSOLD:
            result.rsi_status = RSIStatus.WEAK
            result.rsi_signal = f"⚡ RSI 약세({rsi_mid:.1f})로 반등 여부를 확인해야 합니다"
        else:
            result.rsi_status = RSIStatus.OVERSOLD
            result.rsi_signal = f"⭐ RSI 과매도({rsi_mid:.1f}<30)로 반등 기회가 커졌습니다"

    def _generate_signal(self, result: TrendAnalysisResult) -> None:
        """
        Generate the trading signal.

        Composite score:
- Trend, 30 points: bullish alignment scores higher.
- Bias, 20 points: proximity to MA5 scores higher.
- Volume, 15 points: lower-volume pullback scores higher.
- Support, 10 points: moving-average support scores higher.
- MACD, 15 points: crosses and bullish states score higher.
- RSI, 10 points: oversold and strong states score higher.
        """
        score = 0
        reasons = []
        risks = []

        # Trend score, 30 points.
        trend_scores = {
            TrendStatus.STRONG_BULL: 30,
            TrendStatus.BULL: 26,
            TrendStatus.WEAK_BULL: 18,
            TrendStatus.CONSOLIDATION: 12,
            TrendStatus.WEAK_BEAR: 8,
            TrendStatus.BEAR: 4,
            TrendStatus.STRONG_BEAR: 0,
        }
        trend_score = trend_scores.get(result.trend_status, 12)
        score += trend_score

        if result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL]:
            reasons.append(f"✅ {result.trend_status.value}: 추세에 맞춘 매수 우위")
        elif result.trend_status in [TrendStatus.BEAR, TrendStatus.STRONG_BEAR]:
            risks.append(f"⚠️ {result.trend_status.value}: 매수 진입은 신중해야 합니다")

        # Bias score, 20 points, with strong-trend relief.
        bias = result.bias_ma5
        if bias != bias or bias is None:  # NaN or None defense
            bias = 0.0
        base_threshold = get_config().bias_threshold

        # Strong trend compensation: relax threshold for STRONG_BULL with high strength
        trend_strength = result.trend_strength if result.trend_strength == result.trend_strength else 0.0
        if result.trend_status == TrendStatus.STRONG_BULL and (trend_strength or 0) >= 70:
            effective_threshold = base_threshold * 1.5
            is_strong_trend = True
        else:
            effective_threshold = base_threshold
            is_strong_trend = False

        if bias < 0:
            # Price below MA5 (pullback)
            if bias > -3:
                score += 20
                reasons.append(f"✅ 가격이 MA5보다 약간 낮습니다({bias:.1f}%): 눌림목 매수 구간")
            elif bias > -5:
                score += 16
                reasons.append(f"✅ 가격이 MA5를 되돌림 중입니다({bias:.1f}%): 지지 확인 필요")
            else:
                score += 8
                risks.append(f"⚠️ 이격도가 큽니다({bias:.1f}%): 지지 이탈 가능성")
        elif bias < 2:
            score += 18
            reasons.append(f"✅ 가격이 MA5에 가깝습니다({bias:.1f}%): 진입 타이밍 양호")
        elif bias < base_threshold:
            score += 14
            reasons.append(f"⚡ 가격이 MA5보다 약간 높습니다({bias:.1f}%): 소규모 진입 가능")
        elif bias > effective_threshold:
            score += 4
            risks.append(
                f"❌ 이격도가 과도합니다({bias:.1f}%>{effective_threshold:.1f}%): 추격매수 금지"
            )
        elif bias > base_threshold and is_strong_trend:
            score += 10
            reasons.append(
                f"⚡ 강한 추세에서 이격도가 다소 높습니다({bias:.1f}%): 가벼운 추적 가능"
            )
        else:
            score += 4
            risks.append(
                f"❌ 이격도가 과도합니다({bias:.1f}%>{base_threshold:.1f}%): 추격매수 금지"
            )

        # Volume score, 15 points.
        volume_scores = {
            VolumeStatus.SHRINK_VOLUME_DOWN: 15,  # Lower-volume pullback is best.
            VolumeStatus.HEAVY_VOLUME_UP: 12,     # Heavy-volume advance is next best.
            VolumeStatus.NORMAL: 10,
            VolumeStatus.SHRINK_VOLUME_UP: 6,     # Low-volume advance is weaker.
            VolumeStatus.HEAVY_VOLUME_DOWN: 0,    # Heavy-volume decline is worst.
        }
        vol_score = volume_scores.get(result.volume_status, 8)
        score += vol_score

        if result.volume_status == VolumeStatus.SHRINK_VOLUME_DOWN:
            reasons.append("✅ 거래량 감소 조정으로 건전한 눌림목 가능성")
        elif result.volume_status == VolumeStatus.HEAVY_VOLUME_DOWN:
            risks.append("⚠️ 거래량 증가 하락으로 리스크 유의")

        # Support score, 10 points.
        if result.support_ma5:
            score += 5
            reasons.append("✅ MA5 지지가 유효합니다")
        if result.support_ma10:
            score += 5
            reasons.append("✅ MA10 지지가 유효합니다")

        # MACD score, 15 points.
        macd_scores = {
            MACDStatus.GOLDEN_CROSS_ZERO: 15,  # Golden cross above zero is strongest.
            MACDStatus.GOLDEN_CROSS: 12,      # Golden cross.
            MACDStatus.CROSSING_UP: 10,       # Crosses above zero.
            MACDStatus.BULLISH: 8,            # Bullish.
            MACDStatus.BEARISH: 2,            # Bearish.
            MACDStatus.CROSSING_DOWN: 0,       # Crosses below zero.
            MACDStatus.DEATH_CROSS: 0,        # Death cross.
        }
        macd_score = macd_scores.get(result.macd_status, 5)
        score += macd_score

        if result.macd_status in [MACDStatus.GOLDEN_CROSS_ZERO, MACDStatus.GOLDEN_CROSS]:
            reasons.append(f"✅ {result.macd_signal}")
        elif result.macd_status in [MACDStatus.DEATH_CROSS, MACDStatus.CROSSING_DOWN]:
            risks.append(f"⚠️ {result.macd_signal}")
        else:
            reasons.append(result.macd_signal)

        # RSI score, 10 points.
        rsi_scores = {
            RSIStatus.OVERSOLD: 10,       # Oversold is best.
            RSIStatus.STRONG_BUY: 8,     # Strong.
            RSIStatus.NEUTRAL: 5,        # Neutral.
            RSIStatus.WEAK: 3,            # Weak.
            RSIStatus.OVERBOUGHT: 0,       # Overbought is worst.
        }
        rsi_score = rsi_scores.get(result.rsi_status, 5)
        score += rsi_score

        if result.rsi_status in [RSIStatus.OVERSOLD, RSIStatus.STRONG_BUY]:
            reasons.append(f"✅ {result.rsi_signal}")
        elif result.rsi_status == RSIStatus.OVERBOUGHT:
            risks.append(f"⚠️ {result.rsi_signal}")
        else:
            reasons.append(result.rsi_signal)

        # Composite decision.
        result.signal_score = score
        result.signal_reasons = reasons
        result.risk_factors = risks

        # Generate trading signal with thresholds tuned for the 100-point score.
        if score >= 75 and result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL]:
            result.buy_signal = BuySignal.STRONG_BUY
        elif score >= 60 and result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL, TrendStatus.WEAK_BULL]:
            result.buy_signal = BuySignal.BUY
        elif score >= 45:
            result.buy_signal = BuySignal.HOLD
        elif score >= 30:
            result.buy_signal = BuySignal.WAIT
        elif result.trend_status in [TrendStatus.BEAR, TrendStatus.STRONG_BEAR]:
            result.buy_signal = BuySignal.STRONG_SELL
        else:
            result.buy_signal = BuySignal.SELL
    
    def format_analysis(self, result: TrendAnalysisResult) -> str:
        """
        Format the analysis result as text.

        Args:
            result: Analysis result.

        Returns:
            Formatted analysis text.
        """
        lines = [
            f"=== {result.code} 추세 분석 ===",
            f"",
            f"📊 추세 판단: {result.trend_status.value}",
            f"   이동평균 배열: {result.ma_alignment}",
            f"   추세 강도: {result.trend_strength}/100",
            f"",
            f"📈 이동평균 데이터:",
            f"   현재가: {result.current_price:.2f}",
            f"   MA5:  {result.ma5:.2f} (이격 {result.bias_ma5:+.2f}%)",
            f"   MA10: {result.ma10:.2f} (이격 {result.bias_ma10:+.2f}%)",
            f"   MA20: {result.ma20:.2f} (이격 {result.bias_ma20:+.2f}%)",
            f"",
            f"📊 거래량 분석: {result.volume_status.value}",
            f"   거래량 비율(vs 5일): {result.volume_ratio_5d:.2f}",
            f"   거래량 추세: {result.volume_trend}",
            f"",
            f"📈 MACD 지표: {result.macd_status.value}",
            f"   DIF: {result.macd_dif:.4f}",
            f"   DEA: {result.macd_dea:.4f}",
            f"   MACD: {result.macd_bar:.4f}",
            f"   신호: {result.macd_signal}",
            f"",
            f"📊 RSI 지표: {result.rsi_status.value}",
            f"   RSI(6): {result.rsi_6:.1f}",
            f"   RSI(12): {result.rsi_12:.1f}",
            f"   RSI(24): {result.rsi_24:.1f}",
            f"   신호: {result.rsi_signal}",
            f"",
            f"🎯 운용 의견: {result.buy_signal.value}",
            f"   종합 점수: {result.signal_score}/100",
        ]

        if result.signal_reasons:
            lines.append(f"")
            lines.append(f"✅ 매수 근거:")
            for reason in result.signal_reasons:
                lines.append(f"   {reason}")

        if result.risk_factors:
            lines.append(f"")
            lines.append(f"⚠️ 리스크 요인:")
            for risk in result.risk_factors:
                lines.append(f"   {risk}")

        return "\n".join(lines)


def analyze_stock(df: pd.DataFrame, code: str) -> TrendAnalysisResult:
    """
    Convenience wrapper for analyzing one stock.
    
    Args:
        df: DataFrame containing OHLCV data.
        code: Stock code.
        
    Returns:
        Trend analysis result.
    """
    analyzer = StockTrendAnalyzer()
    return analyzer.analyze(df, code)


if __name__ == "__main__":
    # Demo code.
    logging.basicConfig(level=logging.INFO)
    
    # Generate simulated data for a quick smoke test.
    import numpy as np
    
    dates = pd.date_range(start='2025-01-01', periods=60, freq='D')
    np.random.seed(42)
    
    # Simulate bullishly aligned data.
    base_price = 10.0
    prices = [base_price]
    for i in range(59):
        change = np.random.randn() * 0.02 + 0.003  # Mild upward trend.
        prices.append(prices[-1] * (1 + change))
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
        'low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000000, 5000000) for _ in prices],
    })
    
    analyzer = StockTrendAnalyzer()
    result = analyzer.analyze(df, '005930')
    print(analyzer.format_analysis(result))
