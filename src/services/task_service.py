# -*- coding: utf-8 -*-
"""
===================================
Asynchronous task service layer
===================================

Responsibilities:
1. Manage asynchronous analysis tasks with a thread pool.
2. Run stock analysis and push notifications.
3. Query task status and history.

Migrated from the AnalysisService class in web/services.py.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

from src.enums import ReportType
from src.storage import get_db
from bot.models import BotMessage

logger = logging.getLogger(__name__)


class TaskService:
    """
    Asynchronous task service.

    Responsibilities:
    1. Manage asynchronous analysis tasks.
    2. Run stock analysis.
    3. Trigger notification delivery.
    """

    _instance: Optional['TaskService'] = None
    _lock = threading.Lock()

    def __init__(self, max_workers: int = 3):
        self._executor: Optional[ThreadPoolExecutor] = None
        self._max_workers = max_workers
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._tasks_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'TaskService':
        """Return the task service singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def executor(self) -> ThreadPoolExecutor:
        """Return or create the thread pool."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="analysis_"
            )
        return self._executor

    def submit_analysis(
        self,
        code: str,
        report_type: Union[ReportType, str] = ReportType.SIMPLE,
        source_message: Optional[BotMessage] = None,
        save_context_snapshot: Optional[bool] = None,
        query_source: str = "bot"
    ) -> Dict[str, Any]:
        """
        Submit an asynchronous analysis task.

        Args:
            code: Stock code.
            report_type: Report type enum.
            source_message: Source message used for replies.
            save_context_snapshot: Whether to save a context snapshot.
            query_source: Task source identifier, such as bot/api/cli/system.

        Returns:
            Task information dict.
        """
        # Ensure report_type is an enum.
        if isinstance(report_type, str):
            report_type = ReportType.from_str(report_type)

        task_id = f"{code}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Submit to thread pool.
        self.executor.submit(
            self._run_analysis,
            code,
            task_id,
            report_type,
            source_message,
            save_context_snapshot,
            query_source
        )

        logger.info(
            f"[TaskService] Submitted analysis task for {code}, "
            f"task_id={task_id}, report_type={report_type.value}"
        )

        return {
            "success": True,
            "message": "분석 작업이 제출되었습니다. 비동기로 실행하고 알림을 전송합니다.",
            "code": code,
            "task_id": task_id,
            "report_type": report_type.value
        }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Return task status."""
        with self._tasks_lock:
            return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent tasks."""
        with self._tasks_lock:
            tasks = list(self._tasks.values())
        # Sort by start time descending.
        tasks.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        return tasks[:limit]

    def get_analysis_history(
        self,
        code: Optional[str] = None,
        query_id: Optional[str] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Return analysis history records."""
        db = get_db()
        records = db.get_analysis_history(code=code, query_id=query_id, days=days, limit=limit)
        return [r.to_dict() for r in records]

    def _run_analysis(
        self,
        code: str,
        task_id: str,
        report_type: ReportType = ReportType.SIMPLE,
        source_message: Optional[BotMessage] = None,
        save_context_snapshot: Optional[bool] = None,
        query_source: str = "bot"
    ) -> Dict[str, Any]:
        """
        Run analysis for a single stock.

        Internal method executed in the thread pool.
        """
        # Initialize task status.
        with self._tasks_lock:
            self._tasks[task_id] = {
                "task_id": task_id,
                "code": code,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "result": None,
                "error": None,
                "report_type": report_type.value
        }

        try:
            # Delay imports to avoid circular dependencies.
            from src.config import get_config
            from main import StockAnalysisPipeline

            logger.info(f"[TaskService] Starting stock analysis: {code}")

            # Create analysis pipeline.
            config = get_config()
            pipeline = StockAnalysisPipeline(
                config=config,
                max_workers=1,
                source_message=source_message,
                query_id=task_id,
                query_source=query_source,
                save_context_snapshot=save_context_snapshot
            )

            # Run single-stock analysis with single-stock notifications enabled.
            result = pipeline.process_single_stock(
                code=code,
                skip_analysis=False,
                single_stock_notify=True,
                report_type=report_type
            )

            if result:
                result_data = {
                    "code": result.code,
                    "name": result.name,
                    "sentiment_score": result.sentiment_score,
                    "operation_advice": result.operation_advice,
                    "trend_prediction": result.trend_prediction,
                    "analysis_summary": result.analysis_summary,
                }

                with self._tasks_lock:
                    self._tasks[task_id].update({
                        "status": "completed",
                        "end_time": datetime.now().isoformat(),
                        "result": result_data
                    })

                logger.info(f"[TaskService] Stock {code} analysis completed: {result.operation_advice}")
                return {"success": True, "task_id": task_id, "result": result_data}
            else:
                with self._tasks_lock:
                    self._tasks[task_id].update({
                        "status": "failed",
                        "end_time": datetime.now().isoformat(),
                        "error": "분석 결과가 비어 있습니다."
                    })

                logger.warning(f"[TaskService] Stock {code} analysis failed: empty result")
                return {"success": False, "task_id": task_id, "error": "분석 결과가 비어 있습니다."}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[TaskService] Stock {code} analysis exception: {error_msg}")

            with self._tasks_lock:
                self._tasks[task_id].update({
                    "status": "failed",
                    "end_time": datetime.now().isoformat(),
                    "error": error_msg
                })

            return {"success": False, "task_id": task_id, "error": error_msg}


# ============================================================
# Convenience function.
# ============================================================

def get_task_service() -> TaskService:
    """Return the task service singleton."""
    return TaskService.get_instance()
