# -*- coding: utf-8 -*-
"""
===================================
Realtime quote types and circuit breaker
===================================

Design goals:
1. Normalize realtime quote payloads across providers.
2. Avoid repeated requests after consecutive provider failures.
3. Support provider failover.

Usage:
- Fetchers return UnifiedRealtimeQuote from get_realtime_quote().
- CircuitBreaker tracks provider availability.
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ============================================
# Common type conversion helpers.
# ============================================
# Provider payloads use inconsistent raw types, so conversion is centralized here.

def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Safely convert a value to float.

    Handles:
    - None / empty string -> default
    - pandas NaN / numpy NaN → default
    - numeric string -> float
    - numeric value -> float

    Args:
        val: Value to convert.
        default: Default value when conversion fails.

    Returns:
        Converted float, or default.
    """
    try:
        if val is None:
            return default
        
        # Handle strings.
        if isinstance(val, str):
            val = val.strip()
            if val == "" or val == "-" or val == "--":
                return default
        
        # Handle pandas/numpy NaN without adding a hard pandas dependency.
        import math
        try:
            if math.isnan(float(val)):
                return default
        except (ValueError, TypeError):
            pass
        
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Safely convert a value to int.

    Converts to float first so values like "123.0" are handled.

    Args:
        val: Value to convert.
        default: Default value when conversion fails.

    Returns:
        Converted int, or default.
    """
    f_val = safe_float(val, default=None)
    if f_val is not None:
        return int(f_val)
    return default


class RealtimeSource(Enum):
    """Realtime quote source identifiers."""
    YFINANCE = "yfinance"
    FALLBACK = "fallback"


@dataclass
class UnifiedRealtimeQuote:
    """
    Unified realtime quote data structure.

    Principles:
    - Missing provider fields are represented as None.
    - Callers use getattr(quote, field, None) for compatibility.
    - The source field identifies the data provider for debugging.
    """
    code: str
    name: str = ""
    source: RealtimeSource = RealtimeSource.FALLBACK
    
    # === Core price fields available from most providers ===
    price: Optional[float] = None           # Latest price.
    change_pct: Optional[float] = None      # Change percentage.
    change_amount: Optional[float] = None   # Change amount.

    # === Volume and turnover fields that may be missing ===
    volume: Optional[int] = None            # Volume.
    amount: Optional[float] = None          # Turnover amount.
    volume_ratio: Optional[float] = None    # Volume ratio.
    turnover_rate: Optional[float] = None   # Turnover rate.
    amplitude: Optional[float] = None       # Amplitude.

    # === Price range ===
    open_price: Optional[float] = None      # Open.
    high: Optional[float] = None            # High.
    low: Optional[float] = None             # Low.
    pre_close: Optional[float] = None       # Previous close.
    
    # === Valuation fields that may be populated by provider-specific quote APIs ===
    pe_ratio: Optional[float] = None        # Dynamic PE ratio.
    pb_ratio: Optional[float] = None        # PB ratio.
    total_mv: Optional[float] = None        # Total market value.
    circ_mv: Optional[float] = None         # Free-float market value.

    # === Other fields ===
    change_60d: Optional[float] = None      # 60-day change percentage.
    high_52w: Optional[float] = None        # 52-week high.
    low_52w: Optional[float] = None         # 52-week low.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dict, omitting None values."""
        result = {
            'code': self.code,
            'name': self.name,
            'source': self.source.value,
        }
        # Include only non-None optional fields.
        optional_fields = [
            'price', 'change_pct', 'change_amount', 'volume', 'amount',
            'volume_ratio', 'turnover_rate', 'amplitude',
            'open_price', 'high', 'low', 'pre_close',
            'pe_ratio', 'pb_ratio', 'total_mv', 'circ_mv',
            'change_60d', 'high_52w', 'low_52w'
        ]
        for f in optional_fields:
            val = getattr(self, f, None)
            if val is not None:
                result[f] = val
        return result
    
    def has_basic_data(self) -> bool:
        """Return whether basic price data is present."""
        return self.price is not None and self.price > 0
    
    def has_volume_data(self) -> bool:
        """Return whether volume or turnover data is present."""
        return self.volume_ratio is not None or self.turnover_rate is not None


@dataclass
class ChipDistribution:
    """
    Cost distribution data.

    Represents holding cost distribution and profit ratio data.
    """
    code: str
    date: str = ""
    source: str = "unsupported"
    
    # Profit state.
    profit_ratio: float = 0.0     # Profit ratio from 0 to 1.
    avg_cost: float = 0.0         # Average cost.

    # Cost concentration.
    cost_90_low: float = 0.0      # Lower bound for 90% cost range.
    cost_90_high: float = 0.0     # Upper bound for 90% cost range.
    concentration_90: float = 0.0  # 90% cost concentration; lower means tighter.

    cost_70_low: float = 0.0      # Lower bound for 70% cost range.
    cost_70_high: float = 0.0     # Upper bound for 70% cost range.
    concentration_70: float = 0.0  # 70% cost concentration.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dict."""
        return {
            'code': self.code,
            'date': self.date,
            'source': self.source,
            'profit_ratio': self.profit_ratio,
            'avg_cost': self.avg_cost,
            'cost_90_low': self.cost_90_low,
            'cost_90_high': self.cost_90_high,
            'concentration_90': self.concentration_90,
            'concentration_70': self.concentration_70,
        }
    
    def get_chip_status(self, current_price: float) -> str:
        """
        Return a cost distribution status description.

        Args:
            current_price: Current stock price.

        Returns:
            Korean status description.
        """
        status_parts = []
        
        # Profit ratio analysis.
        if self.profit_ratio >= 0.9:
            status_parts.append("수익 구간 매우 높음(>90%)")
        elif self.profit_ratio >= 0.7:
            status_parts.append("수익 구간 높음(70-90%)")
        elif self.profit_ratio >= 0.5:
            status_parts.append("수익 구간 보통(50-70%)")
        elif self.profit_ratio >= 0.3:
            status_parts.append("손실 구간 비중 높음(>30%)")
        else:
            status_parts.append("손실 구간 비중 매우 높음(>70%)")

        # Cost concentration analysis.
        if self.concentration_90 < 0.08:
            status_parts.append("비용 분포 매우 집중")
        elif self.concentration_90 < 0.15:
            status_parts.append("비용 분포 집중")
        elif self.concentration_90 < 0.25:
            status_parts.append("비용 분포 보통")
        else:
            status_parts.append("비용 분포 분산")

        # Current price versus average cost.
        if current_price > 0 and self.avg_cost > 0:
            cost_diff = (current_price - self.avg_cost) / self.avg_cost * 100
            if cost_diff > 20:
                status_parts.append(f"현재가가 평균 비용보다 {cost_diff:.1f}% 높음")
            elif cost_diff > 5:
                status_parts.append(f"현재가가 평균 비용보다 {cost_diff:.1f}% 소폭 높음")
            elif cost_diff > -5:
                status_parts.append("현재가가 평균 비용에 근접")
            else:
                status_parts.append(f"현재가가 평균 비용보다 {abs(cost_diff):.1f}% 낮음")

        return ", ".join(status_parts)


class CircuitBreaker:
    """
    Circuit breaker for provider cooldown state.

    Strategy:
    - Enter open state after N consecutive failures.
    - Skip the provider while open.
    - Move to half-open after cooldown.
    - A half-open success closes the circuit; a failure reopens it.

    State machine:
    CLOSED --N failures--> OPEN --cooldown elapsed--> HALF_OPEN
    HALF_OPEN --success--> CLOSED
    HALF_OPEN --failure--> OPEN
    """
    
    # State constants.
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 300.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_calls = half_open_max_calls
        
        # Provider state: {source_name: {state, failures, last_failure_time, half_open_calls}}
        self._states: Dict[str, Dict[str, Any]] = {}
    
    def _get_state(self, source: str) -> Dict[str, Any]:
        """Return or initialize provider state."""
        if source not in self._states:
            self._states[source] = {
                'state': self.CLOSED,
                'failures': 0,
                'last_failure_time': 0.0,
                'half_open_calls': 0
            }
        return self._states[source]
    
    def is_available(self, source: str) -> bool:
        """
        Return whether a provider is available.

        True means the caller may attempt a request. False means the provider
        should be skipped.
        """
        state = self._get_state(source)
        current_time = time.time()
        
        if state['state'] == self.CLOSED:
            return True
        
        if state['state'] == self.OPEN:
            # Check cooldown.
            time_since_failure = current_time - state['last_failure_time']
            if time_since_failure >= self.cooldown_seconds:
                # Cooldown complete: move to half-open.
                state['state'] = self.HALF_OPEN
                state['half_open_calls'] = 0
                logger.info(f"[CircuitBreaker] {source} cooldown complete; entering half-open")
                return True
            else:
                remaining = self.cooldown_seconds - time_since_failure
                logger.debug(f"[CircuitBreaker] {source} is open; remaining cooldown: {remaining:.0f}s")
                return False

        if state['state'] == self.HALF_OPEN:
            # Limit requests in half-open state.
            if state['half_open_calls'] < self.half_open_max_calls:
                return True
            return False
        
        return True
    
    def record_success(self, source: str) -> None:
        """Record a successful request."""
        state = self._get_state(source)
        
        if state['state'] == self.HALF_OPEN:
            # Half-open success closes the circuit.
            logger.info(f"[CircuitBreaker] {source} half-open request succeeded; closing circuit")

        # Reset state.
        state['state'] = self.CLOSED
        state['failures'] = 0
        state['half_open_calls'] = 0
    
    def record_failure(self, source: str, error: Optional[str] = None) -> None:
        """Record a failed request."""
        state = self._get_state(source)
        current_time = time.time()
        
        state['failures'] += 1
        state['last_failure_time'] = current_time
        
        if state['state'] == self.HALF_OPEN:
            # Half-open failure reopens the circuit.
            state['state'] = self.OPEN
            state['half_open_calls'] = 0
            logger.warning(
                f"[CircuitBreaker] {source} half-open request failed; "
                f"reopening for {self.cooldown_seconds}s"
            )
        elif state['failures'] >= self.failure_threshold:
            # Failure threshold reached: open the circuit.
            state['state'] = self.OPEN
            logger.warning(
                f"[CircuitBreaker] {source} failed {state['failures']} consecutive time(s); "
                f"opening for {self.cooldown_seconds}s"
            )
            if error:
                logger.warning(f"[CircuitBreaker] Last error: {error}")
    
    def get_status(self) -> Dict[str, str]:
        """Return all provider states."""
        return {source: info['state'] for source, info in self._states.items()}
    
    def reset(self, source: Optional[str] = None) -> None:
        """Reset circuit-breaker state."""
        if source:
            if source in self._states:
                del self._states[source]
        else:
            self._states.clear()


# Global realtime quote circuit breaker.
_realtime_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    cooldown_seconds=300.0,
    half_open_max_calls=1
)

# Cost distribution circuit breaker. More conservative because this endpoint is unstable.
_chip_circuit_breaker = CircuitBreaker(
    failure_threshold=2,
    cooldown_seconds=600.0,
    half_open_max_calls=1
)


def get_realtime_circuit_breaker() -> CircuitBreaker:
    """Return the realtime quote circuit breaker."""
    return _realtime_circuit_breaker


def get_chip_circuit_breaker() -> CircuitBreaker:
    """Return the cost distribution circuit breaker."""
    return _chip_circuit_breaker
