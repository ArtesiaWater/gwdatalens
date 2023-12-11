from typing import List

import dash_bootstrap_components as dbc
from dash import dcc

from ..data.source import DataSource
from . import ids, model_dropdown, model_plots, model_buttons


def render():
    return dcc.Tab(
        label="Pastas Model",
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
