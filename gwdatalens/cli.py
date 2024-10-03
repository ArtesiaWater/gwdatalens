import argparse
import logging
import sys

from gwdatalens.app.main import run_dashboard
from gwdatalens.app.settings import settings
from gwdatalens.django_copy import copy_gwdatalens_to_django_app


def cli_main():
    """GW DataLens dashboard command-line interface.

    Usage
    -----
    Run Dashboard with::

        gwdatalens [--debug BOOL] [--port PORT]
    """
    parser = argparse.ArgumentParser(
        description="Run GW DataLens dashboard on localhost.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Note: To configure the dashboard see the "
            "gwdatalens/app/config.toml file."
        ),
    )

    parser.add_argument(
        "--debug",
        type=bool,
        default=settings["DEBUG"],
        help=f"Run app in debug mode (default: {settings['DEBUG']})",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=settings["PORT"],
        help=f"Port to run the dashboard on (default: {settings['PORT']})",
    )

    kwargs = vars(parser.parse_args())

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

    kwargs = vars(parser.parse_args())

    try:
        logging.basicConfig()
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        copy_gwdatalens_to_django_app(**kwargs)
    except (EOFError, KeyboardInterrupt):
        sys.exit(f" cancelling '{sys.argv[0]}'")
