from functools import partial

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from . import ids, qc_chart, qc_rules, qc_table
from ..data.source import DataSource

def render(app: Dash):
    return dcc.Tab(
        label="QC",
        value=ids.TAB_QC,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_content(app: Dash, data: DataSource):
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col([qc_chart.render(app)], width=12),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col([qc_rules.render(app)], width=6),
                    dbc.Col([qc_table.render(app)], width=6),
                ]
            ),
        ],
        fluid=True,
    )
