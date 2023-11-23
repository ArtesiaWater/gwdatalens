import callbacks
from app import app
from icecream import ic
from waitress import serve

try:
    from .src.cache import cache
except ImportError:  # if running app.py directly
    from src.cache import cache

ic.configureOutput(includeContext=True)


def run(app, debug=False):
    if debug:
        app.run_server(debug=debug)
    else:
        ic(
            "\nRunning QC Grondwaterstanden on http://127.0.0.1:8050/\nPress Ctrl+C to quit."
        )
        serve(app.server, host="127.0.0.1", port=8050)
    cache.clear()


# define alias
run_dashboard = run

# set to True to run app in debug mode
DEBUG = False

# %% Run app

if __name__ == "__main__":
    if DEBUG:
        app.run_server(debug=True)
    else:
        run(app)