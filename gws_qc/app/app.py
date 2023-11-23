import logging

import dash_bootstrap_components as dbc
from dash import Dash
import pastastore as pst

try:
    from .src.cache import cache
    from .src.components.layout import create_layout
    from .src.data.source import DataSource
    from .src.data.source_hpd import DataSourceHydropandas
except ImportError:  # if running app.py directly
    from src.cache import cache
    from src.components.layout import create_layout
    from src.data.source import DataSource
    from src.data.source_hpd import DataSourceHydropandas

logger = logging.getLogger("waitress")
logger.setLevel(logging.ERROR)

# %% set some variables
external_stylesheets = [
    dbc.themes.FLATLY,
    "https://use.fontawesome.com/releases/v6.2.1/css/all.css",
]

# %% main app

# load the data
# data = DataSource()
data = DataSourceHydropandas(fname="obs_collection_dino.pickle")

# load pastastore
conn = pst.ArcticDBConnector(
    name="zeeland", uri="lmdb://../../traval_scripts/pastasdb/"
)
pstore = pst.PastaStore(conn)
data.attach_pastastore(pstore)


# create app
app = Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
)
app.title = "QC Grondwaterstanden"
app.layout = create_layout(app, data)

# initialize cache
cache.init_app(app.server, config={"CACHE_TYPE": "filesystem", "CACHE_DIR": ".cache"})
