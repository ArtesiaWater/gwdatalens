from functools import partial

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from . import ids, tab_overview, tab_qc


def render(app: Dash):
    @app.callback(
        Output(ids.TAB_CONTENT, "children"),
        Input(ids.TAB_CONTAINER, "value"),
    )
    def render_tab_content(tab):
        if tab == ids.TAB_OVERVIEW:
            return tab_overview.render_content(app)
        elif tab ==  ids.TAB_QC:
            return tab_qc.render_content(app)
        else:
            raise PreventUpdate
    return dcc.Tabs(
        id=ids.TAB_CONTAINER,
        value=ids.TAB_OVERVIEW,
        children=[
            tab_overview.render(app),
            tab_qc.render(app),
        ],
    )
