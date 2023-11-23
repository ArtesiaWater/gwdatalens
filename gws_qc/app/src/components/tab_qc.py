from typing import List

import dash_bootstrap_components as dbc
from dash import dcc

from ..data.source import DataSource
from . import ids, qc_chart, qc_dropdowns, qc_rules, qc_table, qc_traval_button


def render():
    return dcc.Tab(
        label="QC",
        value=ids.TAB_QC,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_content(data: DataSource, selected_data: List):
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [qc_dropdowns.render_selection_series_dropdown(data, selected_data)],
                        width=4,
                    ),
                    dbc.Col(
                        [qc_dropdowns.render_additional_series_dropdown(data)],
                        width=4,
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col([qc_chart.render()], width=12),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col([qc_rules.render(data)], width=6),
                    dbc.Col([qc_table.render()], width=6),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col([qc_traval_button.render()], width=6),
                ]
            ),
        ],
        fluid=True,
    )
