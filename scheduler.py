import logging

from apscheduler.schedulers.blocking import BlockingScheduler

import checker as checker_module
import notifier as notifier_module
from config_loader import Config

logger = logging.getLogger(__name__)


def start(config: Config) -> None:
    sched = BlockingScheduler()

    def job() -> None:
        logger.info("=== Award check run starting ===")
        results = checker_module.check_all(config)

        route_hits = {}
        for award in results:
            key = (award.route.origin, award.route.destination)
            route_hits.setdefault(key, []).append(award)

        for route in config.routes:
            key = (route.origin, route.destination)
            awards = route_hits.get(key, [])
            if awards:
                for award in awards:
                    notifier_module.send_available(config, award)
            else:
                notifier_module.send_empty(config, route, config.date_start, config.date_end, config.interval_hours)

        logger.info("=== Run complete — %d award(s) found ===", len(results))

    sched.add_job(job, "interval", hours=config.interval_hours)
    job()  # immediate check on startup
    logger.info("Scheduler running. Next check in %d hour(s). Ctrl+C to stop.", config.interval_hours)
    sched.start()
