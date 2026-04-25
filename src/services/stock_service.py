# -*- coding: utf-8 -*-
"""Stock data service layer for realtime quotes and historical data."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from src.repositories.stock_repo import StockRepository

logger = logging.getLogger(__name__)


class StockService:
    """Business logic wrapper for stock data access."""
    
    def __init__(self):
        """Initialize the stock data service."""
        self.repo = StockRepository()
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """Return realtime quote data for a stock."""
        try:
            # Fetch realtime quote from the data provider manager.
            from data_provider.base import DataFetcherManager
            
            manager = DataFetcherManager()
            quote = manager.get_realtime_quote(stock_code)
            
            if quote is None:
                logger.warning("Failed to fetch realtime quote for %s", stock_code)
                return None
            
            # UnifiedRealtimeQuote is a dataclass, so use getattr for safe field access.
            # Field mapping: UnifiedRealtimeQuote -> API response.
            # - code -> stock_code
            # - name -> stock_name
            # - price -> current_price
            # - change_amount -> change
            # - change_pct -> change_percent
            # - open_price -> open
            # - high -> high
            # - low -> low
            # - pre_close -> prev_close
            # - volume -> volume
            # - amount -> amount
            return {
                "stock_code": getattr(quote, "code", stock_code),
                "stock_name": getattr(quote, "name", None),
                "current_price": getattr(quote, "price", 0.0) or 0.0,
                "change": getattr(quote, "change_amount", None),
                "change_percent": getattr(quote, "change_pct", None),
                "open": getattr(quote, "open_price", None),
                "high": getattr(quote, "high", None),
                "low": getattr(quote, "low", None),
                "prev_close": getattr(quote, "pre_close", None),
                "volume": getattr(quote, "volume", None),
                "amount": getattr(quote, "amount", None),
                "update_time": datetime.now().isoformat(),
            }
            
        except ImportError:
            logger.warning("DataFetcherManager not found; using placeholder quote")
            return self._get_placeholder_quote(stock_code)
        except Exception as e:
            logger.error("Failed to fetch realtime quote: %s", e, exc_info=True)
            return None
    
    def get_history_data(
        self,
        stock_code: str,
        period: str = "daily",
        days: int = 30
    ) -> Dict[str, Any]:
        """Return historical price data for a stock."""
        # Validate period; only daily is currently supported.
        if period != "daily":
            raise ValueError(
                f"'{period}' 기간은 아직 지원하지 않습니다. 현재는 'daily'만 지원합니다. "
                "weekly/monthly 집계는 이후 버전에서 제공될 예정입니다."
            )
        
        try:
            # Fetch historical data from the data provider manager.
            from data_provider.base import DataFetcherManager
            
            manager = DataFetcherManager()
            df, source = manager.get_daily_data(stock_code, days=days)
            
            if df is None or df.empty:
                logger.warning("Failed to fetch historical data for %s", stock_code)
                return {"stock_code": stock_code, "period": period, "data": []}
            
            # Fetch stock name.
            stock_name = manager.get_stock_name(stock_code)
            
            # Convert to response format.
            data = []
            for _, row in df.iterrows():
                date_val = row.get("date")
                if hasattr(date_val, "strftime"):
                    date_str = date_val.strftime("%Y-%m-%d")
                else:
                    date_str = str(date_val)
                
                data.append({
                    "date": date_str,
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": float(row.get("volume", 0)) if row.get("volume") else None,
                    "amount": float(row.get("amount", 0)) if row.get("amount") else None,
                    "change_percent": float(row.get("pct_chg", 0)) if row.get("pct_chg") else None,
                })
            
            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "period": period,
                "data": data,
            }
            
        except ImportError:
            logger.warning("DataFetcherManager not found; returning empty data")
            return {"stock_code": stock_code, "period": period, "data": []}
        except Exception as e:
            logger.error("Failed to fetch historical data: %s", e, exc_info=True)
            return {"stock_code": stock_code, "period": period, "data": []}
    
    def _get_placeholder_quote(self, stock_code: str) -> Dict[str, Any]:
        """Return placeholder quote data for tests or unavailable providers."""
        return {
            "stock_code": stock_code,
            "stock_name": f"Stock {stock_code}",
            "current_price": 0.0,
            "change": None,
            "change_percent": None,
            "open": None,
            "high": None,
            "low": None,
            "prev_close": None,
            "volume": None,
            "amount": None,
            "update_time": datetime.now().isoformat(),
        }
