import numpy as np
import pandas as pd
from dash import dash_table, html
from dash.dash_table.Format import Format

from . import ids
from .styling import DATA_TABLE_HEADER_BGCOLOR


def render(data):
    if data.traval_result is None:
        df = pd.DataFrame(
            columns=["value", "comment", "manual_check"],
        )
        df.index.name = "datetime"
        df = df.reset_index()
        df_records = df.to_dict("records")
    else:
        df = data.traval_result.copy()
        df["manual_check"] = np.nan
        df_records = df.reset_index().to_dict("records")

    return html.Div(
        id="qc-table-div",
        children=[
            dash_table.DataTable(
                id=ids.QC_RESULT_TABLE,
                data=df_records,
                columns=[
                    {
                        "id": "datetime",
                        "name": "Date",
                        "type": "text",
                        "editable": False,
                    },
                    {
                        "id": "values",
                        "name": "Meting",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=5),
                        "editable": False,
                    },
                    {
                        "id": "comment",
                        "name": "Comment",
                        "type": "text",
                        "editable": False,
                    },
                    {
                        "id": "manual_check",
                        "name": "Manual check",
                        "type": "numeric",
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
                style_cell={"whiteSpace": "pre-line", "fontSize": 12},
                style_cell_conditional=[
                    {
                        "if": {"column_id": c},
                        "textAlign": "left",
                    }
                    for c in ["datetime", "comment"]
                ]
                + [
                    {"if": {"column_id": "datetime"}, "width": "20%"},
                    {"if": {"column_id": "values"}, "width": "20%"},
                    {"if": {"column_id": "comment"}, "width": "40%"},
                    {"if": {"column_id": "manual_check"}, "width": "20%"},
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
