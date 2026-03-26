"""Background scheduler for daily data collection."""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from collector.data_processor import collect_all
from config import SCRAPE_HOUR, SCRAPE_MINUTE

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler():
    """Start the background scheduler for daily collection."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        collect_all,
        "cron",
        hour=SCRAPE_HOUR,
        minute=SCRAPE_MINUTE,
        id="daily_collect",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"Scheduler started. Daily collection at {SCRAPE_HOUR:02d}:{SCRAPE_MINUTE:02d}")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        _scheduler = None


def get_next_run():
    """Get the next scheduled run time."""
    if _scheduler and _scheduler.running:
        job = _scheduler.get_job("daily_collect")
        if job:
            return job.next_run_time
    return None
