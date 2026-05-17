import logging
import sys

from config_loader import load_config
from scheduler import start

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Loading configuration...")
    config = load_config("config.yaml")
    logger.info(
        "Monitoring %d route(s) from %s to %s, checking every %d hour(s).",
        len(config.routes),
        config.date_start,
        config.date_end,
        config.interval_hours,
    )
    start(config)


if __name__ == "__main__":
    main()
