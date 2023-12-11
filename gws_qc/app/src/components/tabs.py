from dash import dcc

from . import ids, tab_overview, tab_qc, tab_model, tab_traval


def render():
    return dcc.Tabs(
        id=ids.TAB_CONTAINER,
        value=ids.TAB_TRAVAL,
        children=[
            tab_overview.render(),
            tab_qc.render(),
            tab_model.render(),
            tab_traval.render(),
        ],
    )
