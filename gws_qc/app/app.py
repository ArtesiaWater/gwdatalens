import logging
import os

import dash_bootstrap_components as dbc
import i18n
import pastastore as pst
from dash import CeleryManager, Dash, DiskcacheManager

try:
    # DJANGO APP imports
    from datalens.app.callbacks import register_callbacks
    from datalens.app.settings import LOCALE_PATH, config, settings

    # from datalens.app.src.cache import cache
    from datalens.app.src.components.layout import create_layout
    from datalens.app.src.data.source import DataInterface, DataSource, TravalInterface
except ImportError:  # if running app.py directly
    # Stand-alone imports
    from app.callbacks import register_callbacks
    from app.settings import LOCALE_PATH, config, settings

    from app.src.cache import cache
    from app.src.components.layout import create_layout
    from app.src.data.source import DataInterface, DataSource, TravalInterface

logger = logging.getLogger("waitress")
logger.setLevel(logging.ERROR)

# %% set some variables
external_stylesheets = [
    dbc.themes.FLATLY,
    "https://use.fontawesome.com/releases/v6.5.1/css/all.css",
]

# %% main app

# %% set the locale and load the translations
i18n.set("locale", settings["LOCALE"])
i18n.load_path.append(LOCALE_PATH)

# %% Set up backend

# connect to database
db = DataSource()
# data = DataSourceHydropandas(fname="obs_collection_dino.pickle")

# load pastastore
# name = "zeeland"
name = config["pastastore"]["name"]
pastastore_path = os.path.join(
    os.path.dirname(__file__),
    config["pastastore"]["path"],
)
conn = pst.ArcticDBConnector(name=name, uri=f"lmdb://{pastastore_path}")
pstore = pst.PastaStore(conn)
print(pstore)

# load ruleset
traval_interface = TravalInterface(db, pstore)

# add all components to our data interface object
data = DataInterface(db=db, pstore=pstore, traval=traval_interface)

# %% background callbacks (for cancelling workflows)
# NOTE: still some difficulty remaining with database engine with multiple processes,
# causing performance issues.

if settings["BACKGROUND_CALLBACKS"]:
    if "REDIS_URL" in os.environ:
        # Use Redis & Celery if REDIS_URL set as an env variable
        from celery import Celery

        celery_app = Celery(
            __name__,
            broker=os.environ["REDIS_URL"],
            backend=os.environ["REDIS_URL"],
        )
        background_callback_manager = CeleryManager(celery_app)

    else:
        # Diskcache for non-production apps when developing locally
        import diskcache

        callback_cache = diskcache.Cache("./.cache")
        background_callback_manager = DiskcacheManager(callback_cache)
else:
    background_callback_manager = None

# %% build app


if settings["DJANGO_APP"]:
    from django_plotly_dash import DjangoDash

    # create app
    app = DjangoDash(
        "datalens",
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
        add_bootstrap_links=True,
        # background_callback_manager=background_callback_manager,
    )
    app.title = i18n.t("general.app_title")
    app.layout = create_layout(app, data)
    app.css.append_css(
        {
            "external_url": "/static/assets/dash/custom.css",  # TODO: partially working?
        }
    )

    # register callbacks
    register_callbacks(app, data)
else:
    # create app
    app = Dash(
        "datalens",
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
        background_callback_manager=background_callback_manager,
    )
    app.title = i18n.t("general.app_title")
    app.layout = create_layout(app, data)

    # register callbacks
    register_callbacks(app, data)

    # initialize cache
    cache.init_app(
        app.server,
        config={
            "CACHE_TYPE": "filesystem",
            "CACHE_DIR": ".cache",
        },
    )
