# -*- coding: utf-8 -*-
"""
===================================
KR/US stock analysis system - asynchronous task queue
===================================

Responsibilities:
1. Manage asynchronous analysis task lifecycle
2. Prevent duplicate submissions for the same stock code
3. Provide SSE event broadcasting
4. Persist completed task results to the database
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Set, List, Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import Queue as AsyncQueue

from data_provider.base import canonical_stock_code

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enum"""
    PENDING = "pending"        # Pending execution
    PROCESSING = "processing"  # Processing
    COMPLETED = "completed"    # Completed
    FAILED = "failed"          # Failed


@dataclass
class TaskInfo:
    """
    Task information dataclass.

    Contains complete task status for API responses and internal management
    """
    task_id: str
    stock_code: str
    stock_name: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    report_type: str = "detailed"
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for API responses"""
        return {
            "task_id": self.task_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "report_type": self.report_type,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }
    
    def copy(self) -> 'TaskInfo':
        """Create a copy of task information"""
        return TaskInfo(
            task_id=self.task_id,
            stock_code=self.stock_code,
            stock_name=self.stock_name,
            status=self.status,
            progress=self.progress,
            message=self.message,
            result=self.result,
            error=self.error,
            report_type=self.report_type,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
        )


class DuplicateTaskError(Exception):
    """
    Duplicate submission exception.

    Raised when a stock is already being analyzed
    """
    def __init__(self, stock_code: str, existing_task_id: str):
        self.stock_code = stock_code
        self.existing_task_id = existing_task_id
        super().__init__(f"종목 {stock_code} 분석이 이미 진행 중입니다 (task_id: {existing_task_id})")


class AnalysisTaskQueue:
    """
    Asynchronous analysis task queue.

    Singleton instance for duplicate prevention, thread-pool execution,
    SSE event broadcasting, and result persistence
    """
    
    _instance: Optional['AnalysisTaskQueue'] = None
    _instance_lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, max_workers: int = 3):
        # Prevent duplicate initialization
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._max_workers = max_workers
        self._executor: Optional[ThreadPoolExecutor] = None
        
        # Core data structures
        self._tasks: Dict[str, TaskInfo] = {}           # task_id -> TaskInfo
        self._analyzing_stocks: Dict[str, str] = {}     # stock_code -> task_id
        self._futures: Dict[str, Future] = {}           # task_id -> Future
        
        # SSE subscriber list (asyncio.Queue instances)
        self._subscribers: List['AsyncQueue'] = []
        self._subscribers_lock = threading.Lock()
        
        # Main event loop reference for cross-thread broadcasting
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Thread-safe data lock
        self._data_lock = threading.RLock()
        
        # Number of historical tasks retained in memory
        self._max_history = 100
        
        self._initialized = True
        logger.info(f"[TaskQueue] initialized, max_workers: {max_workers}")
    
    @property
    def executor(self) -> ThreadPoolExecutor:
        """Lazily initialize the thread pool"""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="analysis_task_"
            )
        return self._executor
    
    # ========== Task submission and queries ==========
    
    def is_analyzing(self, stock_code: str) -> bool:
        """
        Check whether a stock is currently being analyzed.

        Args:
            stock_code: Stock code.

        Returns:
            True when analysis is in progress
        """
        with self._data_lock:
            return stock_code in self._analyzing_stocks
    
    def get_analyzing_task_id(self, stock_code: str) -> Optional[str]:
        """
        Get the task ID for a stock currently being analyzed.

        Args:
            stock_code: Stock code.

        Returns:
            Task ID, or None when no task is active
        """
        with self._data_lock:
            return self._analyzing_stocks.get(stock_code)
    
    def submit_task(
        self,
        stock_code: str,
        stock_name: Optional[str] = None,
        report_type: str = "detailed",
        force_refresh: bool = False,
    ) -> TaskInfo:
        """
        Submit an analysis task
        
        Args:
            stock_code: Stock code
            stock_name: Optional stock name
            report_type: Report type
            force_refresh: Whether to force refresh
            
        Returns:
            TaskInfo: Task information
            
        Raises:
            DuplicateTaskError: Stock is already being analyzed
        """
        stock_code = canonical_stock_code(stock_code)
        with self._data_lock:
            # Check duplicate submissions
            if stock_code in self._analyzing_stocks:
                existing_task_id = self._analyzing_stocks[stock_code]
                raise DuplicateTaskError(stock_code, existing_task_id)
            
            # Create task
            task_id = uuid.uuid4().hex
            task_info = TaskInfo(
                task_id=task_id,
                stock_code=stock_code,
                stock_name=stock_name,
                status=TaskStatus.PENDING,
                message="작업이 대기열에 추가되었습니다",
                report_type=report_type,
            )
            
            # Register task
            self._tasks[task_id] = task_info
            self._analyzing_stocks[stock_code] = task_id
            
            # Submit to the thread pool
            future = self.executor.submit(
                self._execute_task,
                task_id,
                stock_code,
                report_type,
                force_refresh,
            )
            self._futures[task_id] = future
            
            logger.info(f"[TaskQueue] task submitted: {stock_code} -> {task_id}")
        
        # Broadcast task creation outside the lock to avoid deadlocks
        self._broadcast_event("task_created", task_info.to_dict())
        
        return task_info
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        Get task information
        
        Args:
            task_id: Task ID
            
        Returns:
            TaskInfo or None
        """
        with self._data_lock:
            task = self._tasks.get(task_id)
            return task.copy() if task else None
    
    def list_pending_tasks(self) -> List[TaskInfo]:
        """
        Get all active tasks (pending + processing)
        
        Returns:
            Task list copies
        """
        with self._data_lock:
            return [
                task.copy() for task in self._tasks.values()
                if task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING)
            ]
    
    def list_all_tasks(self, limit: int = 50) -> List[TaskInfo]:
        """
        Get all tasks ordered by creation time descending
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            Task list copies
        """
        with self._data_lock:
            tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.created_at,
                reverse=True
            )
            return [t.copy() for t in tasks[:limit]]
    
    def get_task_stats(self) -> Dict[str, int]:
        """
        Get task statistics
        
        Returns:
            Statistics dictionary
        """
        with self._data_lock:
            stats = {
                "total": len(self._tasks),
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
            }
            for task in self._tasks.values():
                stats[task.status.value] = stats.get(task.status.value, 0) + 1
            return stats
    
    # ========== Task execution ==========
    
    def _execute_task(
        self,
        task_id: str,
        stock_code: str,
        report_type: str,
        force_refresh: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute an analysis task in the thread pool
        
        Args:
            task_id: Task ID
            stock_code: Stock code
            report_type: Report type
            force_refresh: Whether to force refresh
            
        Returns:
            Analysis result dictionary
        """
        # Mark as processing
        with self._data_lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now()
            task.message = "분석 중..."
            task.progress = 10
        
        self._broadcast_event("task_started", task.to_dict())
        
        try:
            # Import lazily to avoid circular dependencies
            from src.services.analysis_service import AnalysisService
            
            # Run analysis
            service = AnalysisService()
            result = service.analyze_stock(
                stock_code=stock_code,
                report_type=report_type,
                force_refresh=force_refresh,
                query_id=task_id,
            )
            
            if result:
                # Mark task completed
                with self._data_lock:
                    task = self._tasks.get(task_id)
                    if task:
                        task.status = TaskStatus.COMPLETED
                        task.progress = 100
                        task.completed_at = datetime.now()
                        task.result = result
                        task.message = "분석 완료"
                        task.stock_name = result.get("stock_name", task.stock_name)
                        
                        # Remove from active analysis set
                        if task.stock_code in self._analyzing_stocks:
                            del self._analyzing_stocks[task.stock_code]
                
                self._broadcast_event("task_completed", task.to_dict())
                logger.info(f"[TaskQueue] task completed: {task_id} ({stock_code})")
                
                # Clean up old tasks
                self._cleanup_old_tasks()
                
                return result
            else:
                # Analysis returned an empty result
                raise Exception("분석 결과가 비어 있습니다")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[TaskQueue] task failed: {task_id} ({stock_code}), error: {error_msg}")
            
            with self._data_lock:
                task = self._tasks.get(task_id)
                if task:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    task.error = error_msg[:200]  # Limit error message length
                    task.message = f"분석 실패: {error_msg[:50]}"
                    
                    # Remove from active analysis set
                    if task.stock_code in self._analyzing_stocks:
                        del self._analyzing_stocks[task.stock_code]
            
            self._broadcast_event("task_failed", task.to_dict())
            
            # Clean up old tasks
            self._cleanup_old_tasks()
            
            return None
    
    def _cleanup_old_tasks(self) -> int:
        """
        Clean up old completed tasks.

        Keep the latest _max_history tasks
        
        Returns:
            Number of removed tasks
        """
        with self._data_lock:
            if len(self._tasks) <= self._max_history:
                return 0
            
            # Sort by time and remove old completed tasks
            completed_tasks = sorted(
                [t for t in self._tasks.values()
                 if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)],
                key=lambda t: t.created_at
            )
            
            to_remove = len(self._tasks) - self._max_history
            removed = 0
            
            for task in completed_tasks[:to_remove]:
                del self._tasks[task.task_id]
                if task.task_id in self._futures:
                    del self._futures[task.task_id]
                removed += 1
            
            if removed > 0:
                logger.debug(f"[TaskQueue] cleaned {removed} old tasks")
            
            return removed
    
    # ========== SSE event broadcasting ==========
    
    def subscribe(self, queue: 'AsyncQueue') -> None:
        """
        Subscribe to task events
        
        Args:
            queue: asyncio.Queue instance for receiving events
        """
        with self._subscribers_lock:
            self._subscribers.append(queue)
            # Capture the current event loop from the main async context
            try:
                self._main_loop = asyncio.get_running_loop()
            except RuntimeError:
                # If not in an async context, try to get the event loop
                try:
                    self._main_loop = asyncio.get_event_loop()
                except RuntimeError:
                    pass
            logger.debug(f"[TaskQueue] new subscriber added, subscribers: {len(self._subscribers)}")
    
    def unsubscribe(self, queue: 'AsyncQueue') -> None:
        """
        Unsubscribe from task events.
        
        Args:
            queue: asyncio.Queue instance to unsubscribe
        """
        with self._subscribers_lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)
                logger.debug(f"[TaskQueue] subscriber removed, subscribers: {len(self._subscribers)}")
    
    def _broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Broadcast an event to all subscribers.

        Uses call_soon_threadsafe for cross-thread safety
        
        Args:
            event_type: Event type
            data: Event data
        """
        event = {"type": event_type, "data": data}
        
        with self._subscribers_lock:
            subscribers = self._subscribers.copy()
            loop = self._main_loop
        
        if not subscribers:
            return
        
        if loop is None:
            logger.warning("[TaskQueue] cannot broadcast event: main event loop is not set")
            return
        
        for queue in subscribers:
            try:
                # Put the event into the asyncio queue through call_soon_threadsafe.
                # This is safe when sending messages from worker threads to the main loop
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except RuntimeError as e:
                # Event loop is closed
                logger.debug(f"[TaskQueue] broadcast skipped because loop is closed: {e}")
            except Exception as e:
                logger.warning(f"[TaskQueue] broadcast failed: {e}")
    
    # ========== Cleanup ==========
    
    def shutdown(self) -> None:
        """Shut down the task queue"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
            logger.info("[TaskQueue] thread pool shut down")


# ========== Convenience functions ==========

def get_task_queue() -> AnalysisTaskQueue:
    """
    Get the task queue singleton
    
    Returns:
        AnalysisTaskQueue instance
    """
    return AnalysisTaskQueue()
