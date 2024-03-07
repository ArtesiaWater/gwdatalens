import logging
from callbacks import register_callbacks
import dash_bootstrap_components as dbc
import pastastore as pst
from dash import Dash

try:
    from .src.cache import cache
    from .src.components.layout import create_layout
    from .src.data.source import DataInterface
    from .src.data.source_hpd import DataSourceHydropandas
except ImportError:  # if running app.py directly
    from src.cache import cache
    from src.components.layout import create_layout
    from src.data.source import DataInterface, DataSource, TravalInterface
    from src.data.source_hpd import DataSourceHydropandas

logger = logging.getLogger("waitress")
logger.setLevel(logging.ERROR)

# %% set some variables
external_stylesheets = [
    dbc.themes.FLATLY,
    "https://use.fontawesome.com/releases/v6.5.1/css/all.css",
]

# %% main app

# connect to the database
db = DataSource()
# data = DataSourceHydropandas(fname="obs_collection_dino.pickle")

# load pastastore
# name = "zeeland"
name = "zeeland_bro"
conn = pst.ArcticDBConnector(name=name, uri="lmdb://../../traval_scripts/pastasdb/")
pstore = pst.PastaStore(conn)
print(pstore)

# load ruleset
traval_interface = TravalInterface(db, pstore)
traval_interface.load_ruleset()

# add all components to our data interface object
data = DataInterface(db=db, pstore=pstore, traval=traval_interface)

# create app
app = Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
)
app.title = "QC Grondwaterstanden"
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
