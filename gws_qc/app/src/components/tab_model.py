from typing import List

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..data.source import DataSource
from . import ids, model_buttons, model_dropdown, model_plots


def render():
    return dcc.Tab(
        label="Time Series Model",
        value=ids.TAB_MODEL,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_content(data: DataSource, selected_data: List):
    return dbc.Container(
        [
            dbc.Row(
                children=[
                    dbc.Col([model_dropdown.render(data, selected_data)], width=4),
                    dbc.Col([model_buttons.render_generate_button()], width="auto"),
                    dbc.Col([model_buttons.render_save_button()], width="auto"),
                    dbc.Col(
                        [
                            html.P(
                                [
                                    "Powered by ",
                                    html.A(
                                        "Pastas",
                                        href="https://pastas.dev",
                                        target="_blank",
                                    ),
                                ]
                            )
                        ],
                        width="auto",
                    ),
                ],
            ),
            dbc.Row(
                [
                    # Column 1: Model results plot
                    dbc.Col(
                        children=[
                            model_plots.render_results(),
                        ],
                        width=6,
                    ),
                    # Column 2: Model diagnostics plot
                    dbc.Col(
                        children=[
                            model_plots.render_diagnostics(),
                        ],
                        width=6,
                    ),
                ]
            ),
        ],
        fluid=True,
    )
