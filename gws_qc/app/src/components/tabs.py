from dash import dcc

from . import ids, tab_overview, tab_qc


def render():
    return dcc.Tabs(
        id=ids.TAB_CONTAINER,
        value=ids.TAB_QC,
        children=[
            tab_overview.render(),
            tab_qc.render(),
        ],
    )
