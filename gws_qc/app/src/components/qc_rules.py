import numpy as np
import pandas as pd
import traval
import traval.rulelib as rules
from dash import Dash, Input, Output, Patch, State, dash_table, html, no_update
from dash.dash_table.Format import Format
from dash.exceptions import PreventUpdate
from icecream import ic

from ..data.source import DataSource
from . import ids
from .styling import DATA_TABLE_HEADER_BGCOLOR


def render():
    return html.Div(
        id="qc-rules-div",
        children=[
            dash_table.DataTable(
                id=ids.QC_RULES_TABLE,
                data=rule_table.to_dict("records"),
                columns=[
                    {
                        "id": "step",
                        "name": "Rule",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=1),
                        "editable": False,
                    },
                    {
                        "id": "name",
                        "name": "Regel",
                        "type": "text",
                        "editable": False,
                    },
                    {
                        "id": "apply_to",
                        "name": "Toepassen op",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=1),
                        "editable": True,
                    },
                    {
                        "id": "kwargs",
                        "name": "Parameters",
                        "type": "text",
                        "editable": True,
                    },
                ],
                editable=True,
                fixed_rows={"headers": True},
                page_action="none",
                # style_table={
                #     # "height": "70vh",
                #     # "overflowY": "auto",
                #     # "margin-top": 15,
                #     # "maxHeight": "70vh",
                # },
                row_selectable="multi",
                style_cell={"whiteSpace": "pre-line", "fontSize": 12},
                style_cell_conditional=[
                    {"if": {"column_id": "step"}, "width": "10%"},
                    {"if": {"column_id": "name"}, "width": "20%"},
                    {"if": {"column_id": "apply_to"}, "width": "20%"},
                    {"if": {"column_id": "kwargs"}, "width": "50%"},
                ]
                + [
                    {
                        "if": {"column_id": c},
                        "textAlign": "left",
                    }
                    for c in ["name", "kwargs"]
                ],
                # style_data_conditional=style_data_conditional,
                style_header={
                    "backgroundColor": DATA_TABLE_HEADER_BGCOLOR,
                    "fontWeight": "bold",
                },
            ),
        ],
        className="dbc dbc-row-selectable",
    )

data.
rule_table = rset.to_dataframe().loc[:, ["name", "apply_to", "kwargs"]]
rule_table = rule_table.reset_index().astype(str)
# ic(rule_table)
