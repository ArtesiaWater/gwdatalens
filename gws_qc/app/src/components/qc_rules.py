import numpy as np
import pandas as pd
from dash import Dash, Input, Output, Patch, State, dash_table, html, no_update
from dash.dash_table.Format import Format
from dash.exceptions import PreventUpdate

from . import ids
from ..data.source import DataSource

import traval.rulelib as rules

rule_names = [
    irule.replace("rule_", "") for irule in dir(rules) if irule.startswith("rule_")
]
rule_table = pd.DataFrame(
    data=rule_names, columns=["rule_name"], index=range(len(rule_names))
)
rule_table["apply_to"] = 0
rule_table.index.name = "id"


def render(app: Dash, data: DataSource):
    return html.Div(
        id="qc-rules-div",
        children=[
            dash_table.DataTable(
                id=ids.QC_RULES,
                data=rule_table.to_dict("records"),
                columns=[
                    {
                        "id": "id",
                        "name": "Rule",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=1),
                        "editable": False,
                    },
                    {
                        "id": "rule_name",
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
                # style_cell={"whiteSpace": "pre-line"},
                style_cell_conditional=[
                    {"if": {"column_id": "id"}, "width": "10%"},
                    {"if": {"column_id": "rule_name"}, "width": "50%"},
                    {"if": {"column_id": "apply_to"}, "width": "40%"},
                ],
                # + [
                #     {
                #         "if": {"column_id": c},
                #         "textAlign": "left",
                #     }
                #     for c in ["date", "gumbel"]
                # ],
                # style_data_conditional=style_data_conditional,
                # style_header={
                #     "backgroundColor": DATA_TABLE_HEADER_BGCOLOR,
                #     "fontWeight": "bold",
                # },
            ),
        ],
        className="dbc dbc-row-selectable",
    )
