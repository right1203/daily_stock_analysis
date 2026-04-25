# -*- coding: utf-8 -*-
"""Scheduled task runner for stock analysis and market reviews."""

import logging
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """Graceful shutdown handler for SIGTERM/SIGINT."""
    
    def __init__(self):
        self.shutdown_requested = False
        self._lock = threading.Lock()
        
        # Register signal handlers.
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle process signals."""
        with self._lock:
            if not self.shutdown_requested:
                logger.info("Received shutdown signal (%s); waiting for current task to finish", signum)
                self.shutdown_requested = True
    
    @property
    def should_shutdown(self) -> bool:
        """Return whether shutdown was requested."""
        with self._lock:
            return self.shutdown_requested


class Scheduler:
    """Schedule-based daily task runner with graceful shutdown."""
    
    def __init__(self, schedule_time: str = "18:00"):
        """Initialize the scheduler."""
        try:
            import schedule
            self.schedule = schedule
        except ImportError:
            logger.error("schedule package is not installed. Run: pip install schedule")
            raise ImportError("Install schedule package: pip install schedule")
        
        self.schedule_time = schedule_time
        self.shutdown_handler = GracefulShutdown()
        self._task_callback: Optional[Callable] = None
        self._running = False
        
    def set_daily_task(self, task: Callable, run_immediately: bool = True):
        """Set the daily task callback."""
        self._task_callback = task
        
        # Schedule daily task.
        self.schedule.every().day.at(self.schedule_time).do(self._safe_run_task)
        logger.info("Daily task scheduled at %s", self.schedule_time)
        
        if run_immediately:
            logger.info("Running task immediately")
            self._safe_run_task()
    
    def _safe_run_task(self):
        """Run the task with exception handling."""
        if self._task_callback is None:
            return
        
        try:
            logger.info("=" * 50)
            logger.info("Scheduled task started - %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            logger.info("=" * 50)
            
            self._task_callback()
            
            logger.info("Scheduled task completed - %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
        except Exception as e:
            logger.exception("Scheduled task failed: %s", e)
    
    def run(self):
        """Run the scheduler loop until shutdown is requested."""
        self._running = True
        logger.info("Scheduler started")
        logger.info("Next run time: %s", self._get_next_run_time())
        
        while self._running and not self.shutdown_handler.should_shutdown:
            self.schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds.
            
            # Log a heartbeat once per hour.
            if datetime.now().minute == 0 and datetime.now().second < 30:
                logger.info("Scheduler running; next run: %s", self._get_next_run_time())
        
        logger.info("Scheduler stopped")
    
    def _get_next_run_time(self) -> str:
        """Return the next run time."""
        jobs = self.schedule.get_jobs()
        if jobs:
            next_run = min(job.next_run for job in jobs)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        return "Not scheduled"
    
    def stop(self):
        """Stop the scheduler."""
        self._running = False


def run_with_schedule(
    task: Callable,
    schedule_time: str = "18:00",
    run_immediately: bool = True
):
    """Convenience wrapper to run a task with daily scheduling."""
    scheduler = Scheduler(schedule_time=schedule_time)
    scheduler.set_daily_task(task, run_immediately=run_immediately)
    scheduler.run()


if __name__ == "__main__":
    # Scheduler smoke test.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )
    
    def test_task():
        print(f"작업 실행 중... {datetime.now()}")
        time.sleep(2)
        print("작업 완료!")
    
    print("테스트 스케줄러를 시작합니다. 종료하려면 Ctrl+C를 누르세요.")
    run_with_schedule(test_task, schedule_time="23:59", run_immediately=True)
