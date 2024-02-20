import numpy as np
import pandas as pd
from dash import dash_table, html
from dash.dash_table.Format import Format

from . import ids
from .styling import DATA_TABLE_HEADER_BGCOLOR


qc_categories = {
    "QC0i": "Verstopt filter",
    "QC0j": "Ijsvorming in buis",
    "QC2b": "Tijdsverschuiving",
    "QC2c": "Afwijking meetbereik",
    "QC2d": "Temperatuurafwijking",
    "QC2e": "Hysteresis",
    "QC2g": "Hapering sensor",
    "QC2h": "Falen sensor",
    "QC2i": "Sterke ruis",
    "QC2j": "Falen instrument",
    "QC3a": "Droogval buis",
    "QC3b": "Droogval filter",
    "QC3c": "Droogval sensor",
    "QC3d": "Vollopen buis",
    "QC3e": "Overlopen buis",
    "QC3g": "Onderschreiding minimum",
    "QC3h": "Overschreiding maximum	",
    "QC4a": "Onwaarschijnlijke waarde",
    "QC4b": "Filterverwisseling",
    "QC4c": "Onwaarschijnlijke sprong ",
    "QC4d": "Onvoldoende variatie",
    "QC4e": "Onvoldoende samenhang",
    "QC5a": "Betrouwbaarheid",
    "QC5b": "Nauwkeurigheid",
}


def render(data):
    if data.traval.traval_result is None:
        df = pd.DataFrame(
            columns=["value", "comment", "manual_check"],
        )
        df.index.name = "datetime"
        df = df.reset_index()
        df_records = df.to_dict("records")
    else:
        df = data.traval.traval_result.copy()
        df["manual_check"] = np.nan
        df_records = df.reset_index().to_dict("records")

    df["category"] = ""

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
                    {
                        "id": "category",
                        "name": "QC-label",
                        "editable": True,
                        "presentation": "dropdown",
                    },
                ],
                editable=True,
                fixed_rows={"headers": True},
                dropdown={
                    "category": {
                        "options": [
                            {"label": v + f" ({k})", "value": v + f"({k})"}
                            for k, v in qc_categories.items()
                        ]
                    },
                },
                page_action="none",
                virtualization=True,
                style_table={
                    "height": "40vh",
                    # "overflowY": "auto",
                    # "margin-top": 15,
                    "maxHeight": "40vh",
                },
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
                    {"if": {"column_id": "comment"}, "width": "20%"},
                    {"if": {"column_id": "manual_check"}, "width": "20%"},
                    {"if": {"column_id": "category"}, "width": "20%"},
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
