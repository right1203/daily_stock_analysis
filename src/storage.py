# -*- coding: utf-8 -*-
"""
===================================
Daily stock analysis system - storage layer
===================================

Responsibilities:
1. Manage SQLite database connections as a singleton.
2. Define ORM data models.
3. Provide data access operations.
4. Support resumable data update logic.
"""

import atexit
from contextlib import contextmanager
import hashlib
import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, TYPE_CHECKING, Tuple

import pandas as pd
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    UniqueConstraint,
    Text,
    select,
    and_,
    delete,
    desc,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    Session,
)
from sqlalchemy.exc import IntegrityError

from src.config import get_config

logger = logging.getLogger(__name__)

# SQLAlchemy ORM base class.
Base = declarative_base()

if TYPE_CHECKING:
    from src.search_service import SearchResponse


# === Data model definitions ===

class StockDaily(Base):
    """
    Daily stock price data model.

    Stores daily price data and calculated technical indicators. Supports a
    unique constraint per stock and date.
    """
    __tablename__ = 'stock_daily'
    
    # Primary key.
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Stock code, such as 005930 or 035720.
    code = Column(String(10), nullable=False, index=True)
    
    # Trading date.
    date = Column(Date, nullable=False, index=True)
    
    # OHLC data.
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    
    # Volume and turnover data.
    volume = Column(Float)  # Volume.
    amount = Column(Float)  # Turnover amount.
    pct_chg = Column(Float)  # Change percentage.

    # Technical indicators.
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    volume_ratio = Column(Float)  # Volume ratio.

    # Data source.
    data_source = Column(String(50))  # Data source name, such as pykrx or YfinanceFetcher.
    
    # Update timestamps.
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # One row per stock and date.
    __table_args__ = (
        UniqueConstraint('code', 'date', name='uix_code_date'),
        Index('ix_code_date', 'code', 'date'),
    )
    
    def __repr__(self):
        return f"<StockDaily(code={self.code}, date={self.date}, close={self.close})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dict."""
        return {
            'code': self.code,
            'date': self.date,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'amount': self.amount,
            'pct_chg': self.pct_chg,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'volume_ratio': self.volume_ratio,
            'data_source': self.data_source,
        }


class NewsIntel(Base):
    """
    News intelligence data model.

    Stores searched news intelligence entries for later analysis and lookup.
    """
    __tablename__ = 'news_intel'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Linked user query operation.
    query_id = Column(String(64), index=True)

    # Stock information.
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50))

    # Search context.
    dimension = Column(String(32), index=True)  # latest_news / risk_check / earnings / market_analysis / industry
    query = Column(String(255))
    provider = Column(String(32), index=True)

    # News content.
    title = Column(String(300), nullable=False)
    snippet = Column(Text)
    url = Column(String(1000), nullable=False)
    source = Column(String(100))
    published_date = Column(DateTime, index=True)

    # Ingestion time.
    fetched_at = Column(DateTime, default=datetime.now, index=True)
    query_source = Column(String(32), index=True)  # bot/web/cli/system
    requester_platform = Column(String(20))
    requester_user_id = Column(String(64))
    requester_user_name = Column(String(64))
    requester_chat_id = Column(String(64))
    requester_message_id = Column(String(64))
    requester_query = Column(String(255))

    __table_args__ = (
        UniqueConstraint('url', name='uix_news_url'),
        Index('ix_news_code_pub', 'code', 'published_date'),
    )

    def __repr__(self) -> str:
        return f"<NewsIntel(code={self.code}, title={self.title[:20]}...)>"


class AnalysisHistory(Base):
    """
    Analysis result history model.

    Stores analysis results and supports lookup by query_id or stock code.
    """
    __tablename__ = 'analysis_history'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Linked query trace.
    query_id = Column(String(64), index=True)

    # Stock information.
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50))
    report_type = Column(String(16), index=True)

    # Core conclusion.
    sentiment_score = Column(Integer)
    operation_advice = Column(String(20))
    trend_prediction = Column(String(50))
    analysis_summary = Column(Text)

    # Detailed data.
    raw_result = Column(Text)
    news_content = Column(Text)
    context_snapshot = Column(Text)

    # Entry and exit levels used by backtests.
    ideal_buy = Column(Float)
    secondary_buy = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)

    created_at = Column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index('ix_analysis_code_time', 'code', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dict."""
        return {
            'id': self.id,
            'query_id': self.query_id,
            'code': self.code,
            'name': self.name,
            'report_type': self.report_type,
            'sentiment_score': self.sentiment_score,
            'operation_advice': self.operation_advice,
            'trend_prediction': self.trend_prediction,
            'analysis_summary': self.analysis_summary,
            'raw_result': self.raw_result,
            'news_content': self.news_content,
            'context_snapshot': self.context_snapshot,
            'ideal_buy': self.ideal_buy,
            'secondary_buy': self.secondary_buy,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class BacktestResult(Base):
    """Backtest result for a single analysis record."""

    __tablename__ = 'backtest_results'

    id = Column(Integer, primary_key=True, autoincrement=True)

    analysis_history_id = Column(
        Integer,
        ForeignKey('analysis_history.id'),
        nullable=False,
        index=True,
    )

    # Denormalized fields for stock filtering.
    code = Column(String(10), nullable=False, index=True)
    analysis_date = Column(Date, index=True)

    # Backtest parameters.
    eval_window_days = Column(Integer, nullable=False, default=10)
    engine_version = Column(String(16), nullable=False, default='v1')

    # Status.
    eval_status = Column(String(16), nullable=False, default='pending')
    evaluated_at = Column(DateTime, default=datetime.now, index=True)

    # Advice snapshot so future analysis schema changes do not affect explainability.
    operation_advice = Column(String(20))
    position_recommendation = Column(String(8))  # long/cash

    # Prices and returns.
    start_price = Column(Float)
    end_close = Column(Float)
    max_high = Column(Float)
    min_low = Column(Float)
    stock_return_pct = Column(Float)

    # Direction and outcome.
    direction_expected = Column(String(16))  # up/down/flat/not_down
    direction_correct = Column(Boolean, nullable=True)
    outcome = Column(String(16))  # win/loss/neutral

    # Target hits; meaningful only for long positions with stop/take-profit levels.
    stop_loss = Column(Float)
    take_profit = Column(Float)
    hit_stop_loss = Column(Boolean)
    hit_take_profit = Column(Boolean)
    first_hit = Column(String(16))  # take_profit/stop_loss/ambiguous/neither/not_applicable
    first_hit_date = Column(Date)
    first_hit_trading_days = Column(Integer)

    # Simulated execution for long-only mode.
    simulated_entry_price = Column(Float)
    simulated_exit_price = Column(Float)
    simulated_exit_reason = Column(String(24))  # stop_loss/take_profit/window_end/cash/ambiguous_stop_loss
    simulated_return_pct = Column(Float)

    __table_args__ = (
        UniqueConstraint(
            'analysis_history_id',
            'eval_window_days',
            'engine_version',
            name='uix_backtest_analysis_window_version',
        ),
        Index('ix_backtest_code_date', 'code', 'analysis_date'),
    )


class BacktestSummary(Base):
    """Backtest summary metrics by stock or globally."""

    __tablename__ = 'backtest_summaries'

    id = Column(Integer, primary_key=True, autoincrement=True)

    scope = Column(String(16), nullable=False, index=True)  # overall/stock
    code = Column(String(16), index=True)

    eval_window_days = Column(Integer, nullable=False, default=10)
    engine_version = Column(String(16), nullable=False, default='v1')
    computed_at = Column(DateTime, default=datetime.now, index=True)

    # Counts.
    total_evaluations = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)
    insufficient_count = Column(Integer, default=0)
    long_count = Column(Integer, default=0)
    cash_count = Column(Integer, default=0)

    win_count = Column(Integer, default=0)
    loss_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)

    # Accuracy and win-rate metrics.
    direction_accuracy_pct = Column(Float)
    win_rate_pct = Column(Float)
    neutral_rate_pct = Column(Float)

    # Return metrics.
    avg_stock_return_pct = Column(Float)
    avg_simulated_return_pct = Column(Float)

    # Target trigger stats for long positions with stop/take-profit levels.
    stop_loss_trigger_rate = Column(Float)
    take_profit_trigger_rate = Column(Float)
    ambiguous_rate = Column(Float)
    avg_days_to_first_hit = Column(Float)

    # Diagnostic fields stored as JSON strings.
    advice_breakdown_json = Column(Text)
    diagnostics_json = Column(Text)

    __table_args__ = (
        UniqueConstraint(
            'scope',
            'code',
            'eval_window_days',
            'engine_version',
            name='uix_backtest_summary_scope_code_window_version',
        ),
    )


class ConversationMessage(Base):
    """
    Agent conversation history table.
    """
    __tablename__ = 'conversation_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, index=True)


class DatabaseManager:
    """
    Database manager singleton.

    Responsibilities:
    1. Manage the database connection pool.
    2. Provide Session context management.
    3. Encapsulate data access operations.
    """
    
    _instance: Optional['DatabaseManager'] = None
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton construction."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize the database manager.

        Args:
            db_url: Optional database URL. Defaults to configuration value.
        """
        if getattr(self, '_initialized', False):
            return
        
        if db_url is None:
            config = get_config()
            db_url = config.get_db_url()
        
        # Create database engine.
        self._engine = create_engine(
            db_url,
            echo=False,  # Set True to inspect SQL statements.
            pool_pre_ping=True,  # Connection health check.
        )
        
        # Create Session factory.
        self._SessionLocal = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
        )
        
        # Create all tables.
        Base.metadata.create_all(self._engine)

        self._initialized = True
        logger.info(f"Database initialized: {db_url}")

        # Register an exit hook to close database connections.
        atexit.register(DatabaseManager._cleanup_engine, self._engine)
    
    @classmethod
    def get_instance(cls) -> 'DatabaseManager':
        """Return the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton for tests."""
        if cls._instance is not None:
            if hasattr(cls._instance, '_engine') and cls._instance._engine is not None:
                cls._instance._engine.dispose()
            cls._instance._initialized = False
            cls._instance = None

    @classmethod
    def _cleanup_engine(cls, engine) -> None:
        """
        Clean up the database engine from the atexit hook.

        Ensures all database connections are closed when the program exits.

        Args:
            engine: SQLAlchemy engine object.
        """
        try:
            if engine is not None:
                engine.dispose()
                logger.debug("Database engine cleaned up")
        except Exception as e:
            logger.warning(f"Error while cleaning up database engine: {e}")
    
    def get_session(self) -> Session:
        """
        Return a database Session.

        Example:
            with db.get_session() as session:
                # Execute queries.
                session.commit()
        """
        if not getattr(self, '_initialized', False) or not hasattr(self, '_SessionLocal'):
            raise RuntimeError(
                "DatabaseManager is not initialized correctly. "
                "Use DatabaseManager.get_instance() to get an instance."
            )
        session = self._SessionLocal()
        try:
            return session
        except Exception:
            session.close()
            raise

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def has_today_data(self, code: str, target_date: Optional[date] = None) -> bool:
        """
        Return whether data for a target date already exists.

        Used by resumable update logic to skip network requests when data exists.

        Args:
            code: Stock code.
            target_date: Target date. Defaults to today.

        Returns:
            Whether data exists.
        """
        if target_date is None:
            target_date = date.today()
        # target_date means calendar date, not latest trading date. This behavior
        # is retained intentionally because callers rely on it.
        
        with self.get_session() as session:
            result = session.execute(
                select(StockDaily).where(
                    and_(
                        StockDaily.code == code,
                        StockDaily.date == target_date
                    )
                )
            ).scalar_one_or_none()
            
            return result is not None
    
    def get_latest_data(
        self, 
        code: str, 
        days: int = 2
    ) -> List[StockDaily]:
        """
        Return the most recent N rows.

        Used to compute changes relative to the previous available trading day.

        Args:
            code: Stock code.
            days: Number of rows to fetch.

        Returns:
            StockDaily list in descending date order.
        """
        with self.get_session() as session:
            results = session.execute(
                select(StockDaily)
                .where(StockDaily.code == code)
                .order_by(desc(StockDaily.date))
                .limit(days)
            ).scalars().all()
            
            return list(results)

    def save_news_intel(
        self,
        code: str,
        name: str,
        dimension: str,
        query: str,
        response: 'SearchResponse',
        query_context: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Save news intelligence records to the database.

        Deduplication strategy:
        - Prefer URL-based deduplication through the unique constraint.
        - When URL is missing, use title + source + published_date fallback.

        Linking strategy:
        - query_context records user query metadata such as platform, user,
          session, and original request text.
        """
        if not response or not response.results:
            return 0

        saved_count = 0
        query_ctx = query_context or {}
        current_query_id = (query_ctx.get("query_id") or "").strip()

        with self.get_session() as session:
            try:
                for item in response.results:
                    title = (item.title or '').strip()
                    url = (item.url or '').strip()
                    source = (item.source or '').strip()
                    snippet = (item.snippet or '').strip()
                    published_date = self._parse_published_date(item.published_date)

                    if not title and not url:
                        continue

                    url_key = url or self._build_fallback_url_key(
                        code=code,
                        title=title,
                        source=source,
                        published_date=published_date
                    )

                    # Deduplicate by URL or fallback key first.
                    existing = session.execute(
                        select(NewsIntel).where(NewsIntel.url == url_key)
                    ).scalar_one_or_none()

                    if existing:
                        existing.name = name or existing.name
                        existing.dimension = dimension or existing.dimension
                        existing.query = query or existing.query
                        existing.provider = response.provider or existing.provider
                        existing.snippet = snippet or existing.snippet
                        existing.source = source or existing.source
                        existing.published_date = published_date or existing.published_date
                        existing.fetched_at = datetime.now()

                        if query_context:
                            # Keep the first query_id to avoid overwriting historical links.
                            if not existing.query_id and current_query_id:
                                existing.query_id = current_query_id
                            existing.query_source = (
                                query_context.get("query_source") or existing.query_source
                            )
                            existing.requester_platform = (
                                query_context.get("requester_platform") or existing.requester_platform
                            )
                            existing.requester_user_id = (
                                query_context.get("requester_user_id") or existing.requester_user_id
                            )
                            existing.requester_user_name = (
                                query_context.get("requester_user_name") or existing.requester_user_name
                            )
                            existing.requester_chat_id = (
                                query_context.get("requester_chat_id") or existing.requester_chat_id
                            )
                            existing.requester_message_id = (
                                query_context.get("requester_message_id") or existing.requester_message_id
                            )
                            existing.requester_query = (
                                query_context.get("requester_query") or existing.requester_query
                            )
                    else:
                        try:
                            with session.begin_nested():
                                record = NewsIntel(
                                    code=code,
                                    name=name,
                                    dimension=dimension,
                                    query=query,
                                    provider=response.provider,
                                    title=title,
                                    snippet=snippet,
                                    url=url_key,
                                    source=source,
                                    published_date=published_date,
                                    fetched_at=datetime.now(),
                                    query_id=current_query_id or None,
                                    query_source=query_ctx.get("query_source"),
                                    requester_platform=query_ctx.get("requester_platform"),
                                    requester_user_id=query_ctx.get("requester_user_id"),
                                    requester_user_name=query_ctx.get("requester_user_name"),
                                    requester_chat_id=query_ctx.get("requester_chat_id"),
                                    requester_message_id=query_ctx.get("requester_message_id"),
                                    requester_query=query_ctx.get("requester_query"),
                                )
                                session.add(record)
                                session.flush()
                            saved_count += 1
                        except IntegrityError:
                            # Skip only this row on unique URL conflicts, preserving the rest of the batch.
                            logger.debug("Duplicate news intelligence skipped: %s %s", code, url_key)

                session.commit()
                logger.info(f"News intelligence saved: {code}, inserted={saved_count}")

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save news intelligence: {e}")
                raise

        return saved_count

    def get_recent_news(self, code: str, days: int = 7, limit: int = 20) -> List[NewsIntel]:
        """
        Return recent news intelligence for a stock.
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        with self.get_session() as session:
            results = session.execute(
                select(NewsIntel)
                .where(
                    and_(
                        NewsIntel.code == code,
                        NewsIntel.fetched_at >= cutoff_date
                    )
                )
                .order_by(desc(NewsIntel.fetched_at))
                .limit(limit)
            ).scalars().all()

            return list(results)

    def get_news_intel_by_query_id(self, query_id: str, limit: int = 20) -> List[NewsIntel]:
        """
        Return news intelligence records by query_id.

        Args:
            query_id: Analysis query identifier.
            limit: Maximum number of records.

        Returns:
            NewsIntel list sorted by published or fetched time descending.
        """
        from sqlalchemy import func

        with self.get_session() as session:
            results = session.execute(
                select(NewsIntel)
                .where(NewsIntel.query_id == query_id)
                .order_by(
                    desc(func.coalesce(NewsIntel.published_date, NewsIntel.fetched_at)),
                    desc(NewsIntel.fetched_at)
                )
                .limit(limit)
            ).scalars().all()

            return list(results)

    def save_analysis_history(
        self,
        result: Any,
        query_id: str,
        report_type: str,
        news_content: Optional[str],
        context_snapshot: Optional[Dict[str, Any]] = None,
        save_snapshot: bool = True
    ) -> int:
        """
        Save an analysis result history record.
        """
        if result is None:
            return 0

        sniper_points = self._extract_sniper_points(result)
        raw_result = self._build_raw_result(result)
        context_text = None
        if save_snapshot and context_snapshot is not None:
            context_text = self._safe_json_dumps(context_snapshot)

        record = AnalysisHistory(
            query_id=query_id,
            code=result.code,
            name=result.name,
            report_type=report_type,
            sentiment_score=result.sentiment_score,
            operation_advice=result.operation_advice,
            trend_prediction=result.trend_prediction,
            analysis_summary=result.analysis_summary,
            raw_result=self._safe_json_dumps(raw_result),
            news_content=news_content,
            context_snapshot=context_text,
            ideal_buy=sniper_points.get("ideal_buy"),
            secondary_buy=sniper_points.get("secondary_buy"),
            stop_loss=sniper_points.get("stop_loss"),
            take_profit=sniper_points.get("take_profit"),
            created_at=datetime.now(),
        )

        with self.get_session() as session:
            try:
                session.add(record)
                session.commit()
                return 1
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save analysis history: {e}")
                return 0

    def get_analysis_history(
        self,
        code: Optional[str] = None,
        query_id: Optional[str] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[AnalysisHistory]:
        """
        Query analysis history records.

        Notes:
        - If query_id is provided, perform exact lookup and ignore days window.
        - If query_id is not provided, apply days-based time filtering.
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        with self.get_session() as session:
            conditions = []

            if query_id:
                conditions.append(AnalysisHistory.query_id == query_id)
            else:
                conditions.append(AnalysisHistory.created_at >= cutoff_date)

            if code:
                conditions.append(AnalysisHistory.code == code)

            results = session.execute(
                select(AnalysisHistory)
                .where(and_(*conditions))
                .order_by(desc(AnalysisHistory.created_at))
                .limit(limit)
            ).scalars().all()

            return list(results)
    
    def get_analysis_history_paginated(
        self,
        code: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Tuple[List[AnalysisHistory], int]:
        """
        Query paginated analysis history with total count.

        Args:
            code: Optional stock code filter.
            start_date: Inclusive start date.
            end_date: Inclusive end date.
            offset: Number of records to skip.
            limit: Page size.

        Returns:
            Tuple[List[AnalysisHistory], int]: records and total count.
        """
        from sqlalchemy import func
        
        with self.get_session() as session:
            conditions = []
            
            if code:
                conditions.append(AnalysisHistory.code == code)
            if start_date:
                # created_at >= start_date 00:00:00
                conditions.append(AnalysisHistory.created_at >= datetime.combine(start_date, datetime.min.time()))
            if end_date:
                # created_at < end_date+1 00:00:00.
                end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
                conditions.append(AnalysisHistory.created_at < end_datetime)

            # Build where clause.
            where_clause = and_(*conditions) if conditions else True

            # Query total count.
            total_query = select(func.count(AnalysisHistory.id)).where(where_clause)
            total = session.execute(total_query).scalar() or 0

            # Query page data.
            data_query = (
                select(AnalysisHistory)
                .where(where_clause)
                .order_by(desc(AnalysisHistory.created_at))
                .offset(offset)
                .limit(limit)
            )
            results = session.execute(data_query).scalars().all()
            
            return list(results), total
    
    def get_analysis_history_by_id(self, record_id: int) -> Optional[AnalysisHistory]:
        """
        Return a single analysis history record by primary key.

        query_id can be shared by multiple batch-analysis rows, so primary key
        lookup is used for exact record retrieval.

        Args:
            record_id: Analysis history primary key.

        Returns:
            AnalysisHistory object, or None when absent.
        """
        with self.get_session() as session:
            result = session.execute(
                select(AnalysisHistory).where(AnalysisHistory.id == record_id)
            ).scalars().first()
            return result

    def get_latest_analysis_by_query_id(self, query_id: str) -> Optional[AnalysisHistory]:
        """
        Return the latest analysis history record for a query_id.

        query_id may repeat in batch analysis, so the most recent row is returned.

        Args:
            query_id: Analysis query identifier.

        Returns:
            AnalysisHistory object, or None when absent.
        """
        with self.get_session() as session:
            result = session.execute(
                select(AnalysisHistory)
                .where(AnalysisHistory.query_id == query_id)
                .order_by(desc(AnalysisHistory.created_at))
                .limit(1)
            ).scalars().first()
            return result
    
    def get_data_range(
        self, 
        code: str, 
        start_date: date, 
        end_date: date
    ) -> List[StockDaily]:
        """
        Return data in the requested date range.

        Args:
            code: Stock code.
            start_date: Start date.
            end_date: End date.

        Returns:
            StockDaily list.
        """
        with self.get_session() as session:
            results = session.execute(
                select(StockDaily)
                .where(
                    and_(
                        StockDaily.code == code,
                        StockDaily.date >= start_date,
                        StockDaily.date <= end_date
                    )
                )
                .order_by(StockDaily.date)
            ).scalars().all()
            
            return list(results)
    
    def save_daily_data(
        self, 
        df: pd.DataFrame, 
        code: str,
        data_source: str = "Unknown"
    ) -> int:
        """
        Save daily data into the database.

        Strategy:
        - Use UPSERT-like logic: update existing rows, insert new rows.
        - Avoid duplicate rows.

        Args:
            df: DataFrame containing daily data.
            code: Stock code.
            data_source: Data source name.

        Returns:
            Number of inserted records.
        """
        if df is None or df.empty:
            logger.warning(f"Daily data is empty; skipping {code}")
            return 0
        
        saved_count = 0
        
        with self.get_session() as session:
            try:
                for _, row in df.iterrows():
                    # Parse date.
                    row_date = row.get('date')
                    if isinstance(row_date, str):
                        row_date = datetime.strptime(row_date, '%Y-%m-%d').date()
                    elif isinstance(row_date, datetime):
                        row_date = row_date.date()
                    elif isinstance(row_date, pd.Timestamp):
                        row_date = row_date.date()
                    
                    # Check whether the row already exists.
                    existing = session.execute(
                        select(StockDaily).where(
                            and_(
                                StockDaily.code == code,
                                StockDaily.date == row_date
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if existing:
                        # Update existing row.
                        existing.open = row.get('open')
                        existing.high = row.get('high')
                        existing.low = row.get('low')
                        existing.close = row.get('close')
                        existing.volume = row.get('volume')
                        existing.amount = row.get('amount')
                        existing.pct_chg = row.get('pct_chg')
                        existing.ma5 = row.get('ma5')
                        existing.ma10 = row.get('ma10')
                        existing.ma20 = row.get('ma20')
                        existing.volume_ratio = row.get('volume_ratio')
                        existing.data_source = data_source
                        existing.updated_at = datetime.now()
                    else:
                        # Create a new row.
                        record = StockDaily(
                            code=code,
                            date=row_date,
                            open=row.get('open'),
                            high=row.get('high'),
                            low=row.get('low'),
                            close=row.get('close'),
                            volume=row.get('volume'),
                            amount=row.get('amount'),
                            pct_chg=row.get('pct_chg'),
                            ma5=row.get('ma5'),
                            ma10=row.get('ma10'),
                            ma20=row.get('ma20'),
                            volume_ratio=row.get('volume_ratio'),
                            data_source=data_source,
                        )
                        session.add(record)
                        saved_count += 1
                
                session.commit()
                logger.info(f"Saved daily data for {code}, inserted={saved_count}")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save daily data for {code}: {e}")
                raise
        
        return saved_count
    
    def get_analysis_context(
        self, 
        code: str,
        target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Return context data needed for analysis.

        Includes the latest row plus comparison information against the previous
        available row.

        Args:
            code: Stock code.
            target_date: Target date. Defaults to today.

        Returns:
            Dict containing latest data and previous-row comparison details.
        """
        if target_date is None:
            target_date = date.today()
        # Although target_date is accepted, current behavior uses the latest two
        # rows. This is retained intentionally to avoid changing behavior.

        # Fetch the latest two rows.
        recent_data = self.get_latest_data(code, days=2)
        
        if not recent_data:
            logger.warning(f"No data found for {code}")
            return None
        
        today_data = recent_data[0]
        yesterday_data = recent_data[1] if len(recent_data) > 1 else None
        
        context = {
            'code': code,
            'date': today_data.date.isoformat(),
            'today': today_data.to_dict(),
        }
        
        if yesterday_data:
            context['yesterday'] = yesterday_data.to_dict()
            
            # Compute changes relative to the previous row.
            if yesterday_data.volume and yesterday_data.volume > 0:
                context['volume_change_ratio'] = round(
                    today_data.volume / yesterday_data.volume, 2
                )
            
            if yesterday_data.close and yesterday_data.close > 0:
                context['price_change_ratio'] = round(
                    (today_data.close - yesterday_data.close) / yesterday_data.close * 100, 2
                )
            
            # Moving-average pattern status.
            context['ma_status'] = self._analyze_ma_status(today_data)
        
        return context
    
    def _analyze_ma_status(self, data: StockDaily) -> str:
        """
        Analyze moving-average pattern status.

        Conditions:
        - Bullish alignment: close > ma5 > ma10 > ma20
        - Bearish alignment: close < ma5 < ma10 < ma20
        - Sideways: all other cases
        """
        # This static comparison does not account for MA slope, turning points,
        # or adjusted-price differences across data sources. Behavior is retained.
        close = data.close or 0
        ma5 = data.ma5 or 0
        ma10 = data.ma10 or 0
        ma20 = data.ma20 or 0
        
        if close > ma5 > ma10 > ma20 > 0:
            return "정배열 📈"
        elif close < ma5 < ma10 < ma20 and ma20 > 0:
            return "역배열 📉"
        elif close > ma5 and ma5 > ma10:
            return "단기 개선 🔼"
        elif close < ma5 and ma5 < ma10:
            return "단기 약화 🔽"
        else:
            return "횡보 정리 ↔️"

    @staticmethod
    def _parse_published_date(value: Optional[str]) -> Optional[datetime]:
        """
        Parse a published-date string, returning None on failure.
        """
        if not value:
            return None

        if isinstance(value, datetime):
            return value

        text = str(value).strip()
        if not text:
            return None

        # Try ISO format first.
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass

        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d",
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def _safe_json_dumps(data: Any) -> str:
        """
        Safely serialize data to a JSON string.
        """
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except Exception:
            return json.dumps(str(data), ensure_ascii=False)

    @staticmethod
    def _build_raw_result(result: Any) -> Dict[str, Any]:
        """
        Build the full analysis result dict.
        """
        data = result.to_dict() if hasattr(result, "to_dict") else {}
        data.update({
            'data_sources': getattr(result, 'data_sources', ''),
            'raw_response': getattr(result, 'raw_response', None),
        })
        return data

    @staticmethod
    def _parse_sniper_value(value: Any) -> Optional[float]:
        """
        Parse a sniper point value from various formats to float.

        Handles numeric types, plain number strings, KR/US price formats
        like "18.50원" or "$18.50", range formats like "18.50-19.00",
        and text with embedded numbers while filtering out MA indicators.
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            v = float(value)
            return v if v > 0 else None

        text = str(value).replace(',', '').replace('，', '').strip()
        if not text or text == '-' or text == '—' or text == 'N/A':
            return None

        # Try parsing plain number strings directly.
        try:
            return float(text)
        except ValueError:
            pass

        # Prefer the segment before an explicit currency marker to avoid MA indicator numbers.
        colon_pos = max(text.rfind("："), text.rfind(":"))
        marker_start = colon_pos + 1 if colon_pos != -1 else 0
        currency_positions = [
            pos for marker in ("원", "$", "USD", "usd") if (pos := text.find(marker, marker_start)) != -1
        ]
        currency_pos = min(currency_positions) if currency_positions else -1
        if currency_pos != -1:
            segment_start = colon_pos + 1 if colon_pos != -1 else 0
            segment = text[segment_start:currency_pos]
            
            # Use finditer and filter out numbers prefixed by MA.
            matches = list(re.finditer(r"-?\d+(?:\.\d+)?", segment))
            valid_numbers = []
            for m in matches:
                # Check whether the number is prefixed by MA, case-insensitively.
                start_idx = m.start()
                if start_idx >= 2:
                    prefix = segment[start_idx-2:start_idx].upper()
                    if prefix == "MA":
                        continue
                valid_numbers.append(m.group())
            
            if valid_numbers:
                try:
                    return abs(float(valid_numbers[-1]))
                except ValueError:
                    pass

        # Fallback: when no currency marker exists, remove parenthetical text first
        # to avoid extracting technical indicator numbers inside parentheses.
        paren_pos = len(text)
        for paren_char in ('(', '（'):
            pos = text.find(paren_char)
            if pos != -1:
                paren_pos = min(paren_pos, pos)
        search_text = text[:paren_pos].strip() or text

        valid_numbers = []
        for m in re.finditer(r"\d+(?:\.\d+)?", search_text):
            start_idx = m.start()
            if start_idx >= 2 and search_text[start_idx-2:start_idx].upper() == "MA":
                continue
            valid_numbers.append(m.group())
        if valid_numbers:
            try:
                return float(valid_numbers[-1])
            except ValueError:
                pass
        return None

    def _extract_sniper_points(self, result: Any) -> Dict[str, Optional[float]]:
        """
        Extract sniper point values from an AnalysisResult.

        Tries multiple extraction paths to handle different dashboard structures:
        1. result.get_sniper_points() (standard path)
        2. Direct dashboard dict traversal with various nesting levels
        3. Fallback from raw_result dict if available
        """
        raw_points = {}

        # Path 1: standard method
        if hasattr(result, "get_sniper_points"):
            raw_points = result.get_sniper_points() or {}

        # Path 2: direct dashboard traversal when standard path yields empty values
        if not any(raw_points.get(k) for k in ("ideal_buy", "secondary_buy", "stop_loss", "take_profit")):
            dashboard = getattr(result, "dashboard", None)
            if isinstance(dashboard, dict):
                raw_points = self._find_sniper_in_dashboard(dashboard) or raw_points

        # Path 3: try raw_result for agent mode results
        if not any(raw_points.get(k) for k in ("ideal_buy", "secondary_buy", "stop_loss", "take_profit")):
            raw_response = getattr(result, "raw_response", None)
            if isinstance(raw_response, dict):
                raw_points = self._find_sniper_in_dashboard(raw_response) or raw_points

        return {
            "ideal_buy": self._parse_sniper_value(raw_points.get("ideal_buy")),
            "secondary_buy": self._parse_sniper_value(raw_points.get("secondary_buy")),
            "stop_loss": self._parse_sniper_value(raw_points.get("stop_loss")),
            "take_profit": self._parse_sniper_value(raw_points.get("take_profit")),
        }

    @staticmethod
    def _find_sniper_in_dashboard(d: dict) -> Optional[Dict[str, Any]]:
        """
        Recursively search for sniper_points in a dashboard dict.
        Handles various nesting: dashboard.battle_plan.sniper_points,
        dashboard.dashboard.battle_plan.sniper_points, etc.
        """
        if not isinstance(d, dict):
            return None

        # Direct: d has sniper_points keys at top level
        if "ideal_buy" in d:
            return d

        # d.sniper_points
        sp = d.get("sniper_points")
        if isinstance(sp, dict) and sp:
            return sp

        # d.battle_plan.sniper_points
        bp = d.get("battle_plan")
        if isinstance(bp, dict):
            sp = bp.get("sniper_points")
            if isinstance(sp, dict) and sp:
                return sp

        # d.dashboard.battle_plan.sniper_points (double-nested)
        inner = d.get("dashboard")
        if isinstance(inner, dict):
            bp = inner.get("battle_plan")
            if isinstance(bp, dict):
                sp = bp.get("sniper_points")
                if isinstance(sp, dict) and sp:
                    return sp

        return None

    @staticmethod
    def _build_fallback_url_key(
        code: str,
        title: str,
        source: str,
        published_date: Optional[datetime]
    ) -> str:
        """
        Build a stable, short deduplication key for items without URLs.
        """
        date_str = published_date.isoformat() if published_date else ""
        raw_key = f"{code}|{title}|{source}|{date_str}"
        digest = hashlib.md5(raw_key.encode("utf-8")).hexdigest()
        return f"no-url:{code}:{digest}"

    def save_conversation_message(self, session_id: str, role: str, content: str) -> None:
        """
        Save an Agent conversation message.
        """
        with self.session_scope() as session:
            msg = ConversationMessage(
                session_id=session_id,
                role=role,
                content=content
            )
            session.add(msg)

    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Return Agent conversation history.
        """
        with self.session_scope() as session:
            stmt = select(ConversationMessage).filter(
                ConversationMessage.session_id == session_id
            ).order_by(ConversationMessage.created_at.desc()).limit(limit)
            messages = session.execute(stmt).scalars().all()

            # Reverse to preserve chronological order.
            return [{"role": msg.role, "content": msg.content} for msg in reversed(messages)]

    def get_chat_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Return chat sessions aggregated from conversation_messages.

        Returns:
            Sessions sorted by recent activity. Each item includes session_id,
            title, message_count, and last_active.
        """
        from sqlalchemy import func

        with self.session_scope() as session:
            # Aggregate message count and last active time per session.
            stmt = (
                select(
                    ConversationMessage.session_id,
                    func.count(ConversationMessage.id).label("message_count"),
                    func.min(ConversationMessage.created_at).label("created_at"),
                    func.max(ConversationMessage.created_at).label("last_active"),
                )
                .group_by(ConversationMessage.session_id)
                .order_by(desc(func.max(ConversationMessage.created_at)))
                .limit(limit)
            )
            rows = session.execute(stmt).all()

            results = []
            for row in rows:
                sid = row.session_id
                # Use the first user message as the session title.
                first_user_msg = session.execute(
                    select(ConversationMessage.content)
                    .where(
                        and_(
                            ConversationMessage.session_id == sid,
                            ConversationMessage.role == "user",
                        )
                    )
                    .order_by(ConversationMessage.created_at)
                    .limit(1)
                ).scalar()
                title = (first_user_msg or "새 대화")[:60]

                results.append({
                    "session_id": sid,
                    "title": title,
                    "message_count": row.message_count,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "last_active": row.last_active.isoformat() if row.last_active else None,
                })
            return results

    def get_conversation_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Return messages for one session, used by the frontend to restore history.
        """
        with self.session_scope() as session:
            stmt = (
                select(ConversationMessage)
                .where(ConversationMessage.session_id == session_id)
                .order_by(ConversationMessage.created_at)
                .limit(limit)
            )
            messages = session.execute(stmt).scalars().all()
            return [
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                for msg in messages
            ]

    def delete_conversation_session(self, session_id: str) -> int:
        """
        Delete all messages in a session.

        Returns:
            Number of deleted messages.
        """
        with self.session_scope() as session:
            result = session.execute(
                delete(ConversationMessage).where(
                    ConversationMessage.session_id == session_id
                )
            )
            return result.rowcount


# Convenience helper.
def get_db() -> DatabaseManager:
    """Return the database manager singleton."""
    return DatabaseManager.get_instance()


if __name__ == "__main__":
    # Manual test code.
    logging.basicConfig(level=logging.DEBUG)
    
    db = get_db()
    
    print("=== Database test ===")
    print("Database initialized")
    
    # Check today's data.
    has_data = db.has_today_data('005930')
    print(f"삼성전자 has data today: {has_data}")
    
    # Save test data.
    test_df = pd.DataFrame({
        'date': [date.today()],
        'open': [1800.0],
        'high': [1850.0],
        'low': [1780.0],
        'close': [1820.0],
        'volume': [10000000],
        'amount': [18200000000],
        'pct_chg': [1.5],
        'ma5': [1810.0],
        'ma10': [1800.0],
        'ma20': [1790.0],
        'volume_ratio': [1.2],
    })
    
    saved = db.save_daily_data(test_df, '005930', 'TestSource')
    print(f"Saved test rows: {saved}")
    
    # Fetch context.
    context = db.get_analysis_context('005930')
    print(f"Analysis context: {context}")
