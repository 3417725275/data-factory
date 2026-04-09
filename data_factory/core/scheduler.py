"""Built-in scheduler using APScheduler."""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from data_factory.core.config import AppConfig, SchedulerJob

log = logging.getLogger(__name__)


class DataFactoryScheduler:
    def __init__(self, config: AppConfig, pipeline):
        self.config = config
        self.pipeline = pipeline
        self.scheduler = BlockingScheduler()
        self.job_configs = list(config.scheduler.jobs)

    def setup(self) -> None:
        for job in self.job_configs:
            trigger = CronTrigger.from_crontab(job.cron)
            self.scheduler.add_job(
                self._run_job,
                trigger=trigger,
                args=[job],
                id=job.name,
                name=job.name,
            )
            log.info("Scheduled job: %s [%s] cron=%s", job.name, job.platform, job.cron)

        self.scheduler.add_job(
            self._refresh_all_comments,
            CronTrigger.from_crontab("0 */6 * * *"),
            id="comment_refresh_scan",
            name="comment_refresh_scan",
        )
        log.info("Scheduled comment refresh scan every 6 hours")

    def start(self) -> None:
        self.setup()
        log.info("Scheduler starting with %d jobs", len(self.job_configs))
        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.shutdown(wait=False)

    def list_jobs(self) -> list[dict]:
        return [
            {
                "name": j.name,
                "platform": j.platform,
                "query": j.query,
                "cron": j.cron,
                "next_run": str(self.scheduler.get_job(j.name).next_run_time)
                if self.scheduler.get_job(j.name) else "not scheduled",
            }
            for j in self.job_configs
        ]

    def _run_job(self, job: SchedulerJob) -> None:
        log.info("Running job: %s", job.name)
        try:
            from data_factory.core.pipeline import get_adapter
            adapter = get_adapter(job.platform, self.config)
            urls = adapter.search(job.query, limit=job.limit)
            for url in urls:
                self.pipeline.run_full(url, job.platform)
        except Exception as e:
            log.error("Job %s failed: %s", job.name, e)

    def _refresh_all_comments(self) -> None:
        log.info("Starting comment refresh scan")
        from data_factory.core.storage import load_json
        from data_factory.core.refresh import needs_comment_refresh

        output_dir = self.config.output_dir
        if not output_dir.exists():
            return
        for platform_dir in output_dir.iterdir():
            if not platform_dir.is_dir():
                continue
            for item_dir in platform_dir.iterdir():
                meta_path = item_dir / "meta.json"
                meta = load_json(meta_path)
                if not meta:
                    continue
                if needs_comment_refresh(meta):
                    try:
                        self.pipeline.run_refresh(meta["url"], platform_dir.name)
                    except Exception as e:
                        log.error("Refresh failed for %s/%s: %s", platform_dir.name, item_dir.name, e)
