from app import app
from icecream import ic
from waitress import serve

try:
    from datalens.app.settings import settings
    from datalens.app.src.cache import cache
except ImportError:  # if running app.py directly
    from settings import settings
    from src.cache import cache

ic.configureOutput(includeContext=True)


def run(app, debug=False, port=8050):
    if debug:
        app.run_server(debug=debug)
    else:
        ic(
            f"\nRunning QC Grondwaterstanden on http://127.0.0.1:{port}/"
            "\nPress Ctrl+C to quit."
        )
        serve(app.server, host="127.0.0.1", port=port)
    cache.clear()


# define alias
run_dashboard = run

# %% Run app

if __name__ == "__main__":
    if settings["DEBUG"]:
        app.run_server(debug=True)
    else:
        # app.run_server(debug=False)
        run(app)
