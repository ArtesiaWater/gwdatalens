import logging

import dash_bootstrap_components as dbc
from dash import Dash
from waitress import serve

try:
    from .src.cache import cache
    from .src.components.layout import create_layout
except ImportError:  # if running app.py directly
    from src.cache import cache
    from src.components.layout import create_layout

logger = logging.getLogger("waitress")
logger.setLevel(logging.ERROR)

# set to True to run app in debug mode
DEBUG = True

# %% set some variables
external_stylesheets = [
    dbc.themes.FLATLY,
    "https://use.fontawesome.com/releases/v6.2.1/css/all.css",
]

# %% main app


def main():
    # load the data
    # data = DataSource()

    # create app
    app = Dash(
        __name__,
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
    )
    app.title = "QC Grondwaterstanden"
    app.layout = create_layout(app)

    # initialize cache
    cache.init_app(
        app.server, config={"CACHE_TYPE": "filesystem", "CACHE_DIR": ".cache"}
    )
    return app


def run(debug=False):
    app = main()
    if debug:
        app.run_server(debug=debug)
    else:
        print(
            "\nRunning PyGolf Dashboard on http://127.0.0.1:8050/\nPress Ctrl+C to quit."
        )
        serve(app.server, host="127.0.0.1", port=8050)
    cache.clear()


# define alias
run_dashboard = run


# %% Run app

if __name__ == "__main__":
    if DEBUG:
        app = main()
        app.run_server(debug=True)
    else:
        run()
