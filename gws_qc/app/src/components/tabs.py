from functools import partial

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from . import ids, tab_overview, tab_qc
from ..data.source import DataSource


def render():
    return dcc.Tabs(
        id=ids.TAB_CONTAINER,
        value=ids.TAB_QC,
        children=[
            tab_overview.render(),
            tab_qc.render(),
        ],
    )
