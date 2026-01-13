import argparse
import logging
import sys

from gwdatalens.app.config import config
from gwdatalens.app.main import run_dashboard
from gwdatalens.django_copy import copy_gwdatalens_to_django_app


def cli_main():
    """GW DataLens dashboard command-line interface.

    Configuration priority (lowest to highest):
    1. config.toml defaults
    2. Environment variables (GWDATALENS_*)
    3. CLI arguments (override all)

    Usage
    -----
    Run Dashboard with::

        gwdatalens [--debug] [--port PORT] [--locale LOCALE]

    Environment Variables
    ---------------------
    GWDATALENS_DEBUG=true/false
    GWDATALENS_PORT=8050
    GWDATALENS_LOCALE=nl/en
    GWDATALENS_CACHING=true/false
    GWDATALENS_LOG_LEVEL=DEBUG/INFO/WARNING/ERROR
    GWDATALENS_DB_HOST=localhost
    GWDATALENS_DB_PORT=5432
    GWDATALENS_DB_NAME=database_name
    GWDATALENS_DB_USER=username
    GWDATALENS_DB_PASSWORD=password
    """
    parser = argparse.ArgumentParser(
        description="Run GW DataLens dashboard on localhost.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Configuration:\n"
            "  Edit gwdatalens/app/config.toml for application settings.\n"
            "  Copy gwdatalens/app/database.toml.template to database.toml\n"
            "  for database credentials (keep database.toml gitignored).\n\n"
            "Environment variables override config.toml (GWDATALENS_*).\n"
            "CLI arguments override both config.toml and environment variables."
        ),
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=None,
        help=f"Run app in debug mode (default: {config.get('DEBUG')})",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"Port to run the dashboard on (default: {config.get('PORT')})",
    )

    parser.add_argument(
        "--locale",
        type=str,
        choices=["nl", "en"],
        default=None,
        help=f"Application locale (default: {config.get('LOCALE')})",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help=f"Logging level (default: {config.get('LOG_LEVEL')})",
    )

    args = parser.parse_args()

    # Update configuration from CLI arguments (only if explicitly provided)
    cli_overrides = {
        "debug": args.debug,
        "port": args.port,
        "locale": args.locale,
        "log_level": args.log_level,
    }
    config.update_from_cli(**cli_overrides)

    # Prepare kwargs for run_dashboard
    kwargs = {
        "debug": config.get("DEBUG"),
        "port": config.get("PORT"),
    }

    try:
        run_dashboard(**kwargs)
    except (EOFError, KeyboardInterrupt):
        sys.exit(f" cancelling '{sys.argv[0]}'")


def cp_gwdatalens_to_broconnector():
    """GW DataLens dashboard command-line interface.

    Usage
    -----
    Copy GW DataLens to BRO-Connector with::

        cp_gwdatalens_to_broconnector [DJANGO_APP_PATH]
    """
    parser = argparse.ArgumentParser(
        description="Copy GW DataLens to BRO-Connector.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "See https://github.com/nens/bro-connector for more "
            "information about BRO-Connector."
        ),
    )

    parser.add_argument(
        "DJANGO_APP_PATH",
        type=str,
        help="BRO-Connector root directory.",
    )

    parser.add_argument(
        "--skip-config",
        action="store_true",
        help="Skip copying config.toml file to the Django app.",
    )

    kwargs = vars(parser.parse_args())

    try:
        logging.basicConfig()
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        copy_gwdatalens_to_django_app(**kwargs)
    except (EOFError, KeyboardInterrupt):
        sys.exit(f" cancelling '{sys.argv[0]}'")
