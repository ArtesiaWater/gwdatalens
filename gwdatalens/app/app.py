import logging
import os

import dash_bootstrap_components as dbc
import i18n
import pastastore as pst
from dash import CeleryManager, Dash, DiskcacheManager

try:
    # DJANGO APP imports
    from gwdatalens.app.callbacks import register_callbacks
    from gwdatalens.app.settings import LOCALE_PATH, config, settings
    from gwdatalens.app.src.cache import cache
    from gwdatalens.app.src.components.layout import create_layout
    from gwdatalens.app.src.data.source import (
        DataInterface,
        DataSource,
        TravalInterface,
    )
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

# load pastastore
# name = "zeeland"
name = config["pastastore"]["name"]
pastastore_path = config["pastastore"]["path"]

if name.endswith(".zip"):
    pstore = pst.PastaStore.from_zip(pastastore_path / name)
else:
    conn = pst.ArcticDBConnector(name=name, uri=f"lmdb://{pastastore_path}")
    pstore = pst.PastaStore(conn)
    print(pstore)

# load ruleset
traval_interface = TravalInterface(db, pstore)

# add all components to our data interface object
data = DataInterface(db=db, pstore=pstore, traval=traval_interface, settings=settings)

# %% background callbacks (for cancelling workflows)
# NOTE: still some difficulty remaining with database engine with multiple processes,
# causing performance issues. It is currently recommended to not use background
# callbacks.

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
        "gwdatalens",
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
        add_bootstrap_links=True,
        background_callback_manager=background_callback_manager,
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
        "gwdatalens",
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

# %%

if 0:
    names = []
    for i in data.db.list_locations():
        gmw_id, tube_nr = i.split("-")
        tube_nr = int(tube_nr)
        s = data.db.get_timeseries(gmw_id, tube_nr, observation_type="controlemeting")
        if s.index.size > 0:
            names.append((gmw_id, tube_nr))


if 0:
    import matplotlib.pyplot as plt
    import traval

    gmw_id = "GMW000000050707"
    tube_nr = 2
    series = data.db.get_timeseries(gmw_id, tube_nr)[data.db.value_column]
    hp = data.db.get_timeseries(gmw_id, tube_nr, observation_type="controlemeting")[
        data.db.value_column
    ]
    detector = traval.Detector(series)

    ruleset = traval.RuleSet("manual_obs")
    ruleset.add_rule(
        "manual_obs",
        traval.rulelib.rule_shift_to_manual_obs,
        apply_to=0,
        kwargs={"hseries": hp},
    )
    detector.apply_ruleset(ruleset)
    cp = detector.comparisons[1]
    compare = traval.ComparisonPlots(cp)
    ax = compare.plot_series_comparison()
    ax.plot(hp.index, hp, marker="x", ms=10, color="b", ls="none")

    plt.show()