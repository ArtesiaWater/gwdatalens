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
    index=["test1", "test2", "test3"],
    columns=["x", "y"],
    data=999.0,
)
data.index.name = "name"
data = data.reset_index()

def render(app: Dash):
    return html.Div(
        id="table-div",
        children=[
            dash_table.DataTable(
                id=ids.OVERVIEW_TABLE,
                data=data.to_dict("records"),
                columns=[
                    {
                        "id": "name",
                        "name": "Naam",
                        "type": "text",
                    },
                    {
                        "id": "x",
                        "name": "X",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=5),
                    },
                    {
                        "id": "y",
                        "name": "Y",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=5),
                    },
                ],
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
