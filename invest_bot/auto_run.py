"""Entry point used by Windows Task Scheduler for the monthly investment run."""
from dataclasses import replace

from .cli import run
from .config import Settings
from .preferences import auto_trading_enabled


def main() -> None:
    settings = Settings.from_env()
    enabled = auto_trading_enabled()
    # The dashboard toggle is the explicit monthly automation consent. The normal
    # CLI --live safety gate remains unchanged for manual command-line use.
    run(replace(settings, dry_run=not enabled), live=enabled)


if __name__ == '__main__':
    main()
