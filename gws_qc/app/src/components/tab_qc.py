from typing import List

import dash_bootstrap_components as dbc
from dash import dcc

from ..data.source import DataInterface
from . import ids, qc_chart, qc_dropdowns, qc_rules_form, qc_traval_buttons


def render():
    return dcc.Tab(
        label="QC",
        value=ids.TAB_QC,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_content(data: DataInterface, selected_data: List):
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            qc_dropdowns.render_selection_series_dropdown(
                                data, selected_data
                            )
                        ],
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
            # dbc.Row(
            #     [
            #         dbc.Col([qc_rules.render(data)], width=6),
            #         dbc.Col([qc_table.render()], width=6),
            #     ]
            # ),
            dbc.Row(
                [
                    qc_rules_form.render_traval_form(data),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col([qc_dropdowns.render_add_rule_dropdown()], width="4"),
                    dbc.Col([qc_traval_buttons.render_add_rule_button()], width="auto"),
                    dbc.Col(
                        [qc_traval_buttons.render_load_ruleset_button()], width="auto"
                    ),
                    dbc.Col(
                        [qc_traval_buttons.render_run_traval_button()], width="auto"
                    ),
                ]
            ),
            # NOTE: use below for showing JSON of current traval ruleset
            # dbc.Row(
            #     [
            #         html.Pre(id=ids.TRAVAL_OUTPUT, lang="JSON", style={"fontSize": 8}),
            #     ]
            # ),
        ],
        fluid=True,
    )
