from functools import partial

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from . import ids, overview_chart, overview_map, overview_table


def render(app: Dash):
    return dcc.Tab(
        label="Overview",
        value=ids.TAB_OVERVIEW,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_content(app: Dash):
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            overview_map.render(app),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            overview_table.render(app),
                        ],
                        width=6,
                    ),
                ],
                style={"height": "45vh"},
            ),
            dbc.Row(
                [
                    overview_chart.render(app),
                ],
            ),
        ],
        fluid=True,
    )
