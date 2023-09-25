import numpy as np
import pandas as pd
from dash import Dash, Input, Output, Patch, State, dash_table, html, no_update
from dash.dash_table.Format import Format
from dash.exceptions import PreventUpdate

from . import ids

# DATA_TABLE_HEADER_BGCOLOR = "rgb(245, 245, 245)"
# DATA_TABLE_ODD_ROW_BGCOLOR = "rgb(250, 250, 250)"
# DATA_TABLE_FALSE_BGCOLOR = "rgb(255, 238, 238)"
# DATA_TABLE_TRUE_BGCOLOR = "rgb(231, 255, 239)"
import pandas as pd

data = pd.DataFrame(
    index=["meting1", "meting2", "meting3"],
    columns=["value"],
    data=999.0,
)
data["comment"] = "ok"
data.loc["meting3", "comment"] = "suspect"
data.index.name = "index"
data = data.reset_index()

def render(app: Dash):
    return html.Div(
        id="qc-table-div",
        children=[
            dash_table.DataTable(
                id=ids.QC_TABLE,
                data=data.to_dict("records"),
                columns=[
                    {
                        "id": "index",
                        "name": "Datum",
                        "type": "text",
                        "editable": False,
                    },
                    {
                        "id": "value",
                        "name": "Meting",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=5),
                        "editable": False,
                    },
                    {
                        "id": "comment",
                        "name": "opmerking",
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
                # row_selectable="multi",
                # style_cell={"whiteSpace": "pre-line"},
                # style_cell_conditional=[
                #     {
                #         "if": {"column_id": c},
                #         "textAlign": "left",
                #     }
                #     for c in ["date", "gumbel"]
                # ]
                # + [
                #     {"if": {"column_id": "date"}, "width": "30%"},
                #     {"if": {"column_id": "T"}, "width": "25%"},
                #     {"if": {"column_id": "gumbel"}, "width": "35%"},
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
