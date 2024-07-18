import sys

from gwdatalens.app.main import run_dashboard
from gwdatalens.app.settings import settings


def cli_main():
    """GW DataLens dashboard command-line interface.
    
    Usage
    -----
    Run Dashboard with::

        gwdatalens [--debug BOOL] [--port PORT]
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Run GW DataLens dashboard on localhost.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

    args = vars(parser.parse_args())
    try:
        run_dashboard(**args)
    except (EOFError, KeyboardInterrupt):
        sys.exit(f" cancelling '{sys.argv[0]}'")


# %%
if __name__ == "__main__":
    """Run command-line interface, if run as a script."""
    cli_main()
