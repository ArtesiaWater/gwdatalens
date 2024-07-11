import i18n
import pandas as pd
from dash import dash_table, html
from dash.dash_table.Format import Format

from ..data.qc_definitions import qc_categories
from . import ids
from .styling import DATA_TABLE_HEADER_BGCOLOR


def render(data):
    if data.traval.traval_result is None:
        df = pd.DataFrame(
            columns=["id", "value", "comment", "reliable", "category"],
        )
        df.index.name = "datetime"
        df = df.reset_index(names="datetime")
        df_records = df.to_dict("records")
    else:
        df = data.traval.traval_result.copy()
        df_records = df.reset_index(names="datetime").to_dict("records")

    options = [
        {"label": v + f" ({k})", "value": v + f"({k})"}
        for k, v in qc_categories.items()
    ]
    # options = [{"label": i18n.t("general.clear_qc_label"), "value": ""}] + options

    return html.Div(
        id="qc-table-div",
        children=[
            dash_table.DataTable(
                id=ids.QC_RESULT_TABLE,
                data=df_records,
                columns=[
                    {
                        "id": "datetime",
                        "name": i18n.t("general.datetime"),
                        "type": "text",
                        "editable": False,
                    },
                    {
                        "id": "values",
                        "name": i18n.t("general.observations"),
                        "type": "numeric",
                        "format": Format(scheme="r", precision=5),
                        "editable": False,
                    },
                    {
                        "id": "comment",
                        "name": i18n.t("general.comment"),
                        "type": "text",
                        "editable": False,
                    },
                    {
                        "id": "reliable",
                        "name": i18n.t("general.reliable"),
                        "type": "numeric",
                        "editable": False,
                        # "on_change": {"action": "validate", "failure": "accept"},
                        # "validation": {"default": 1},
                    },
                    {
                        "id": "category",
                        "name": i18n.t("general.qc_label"),
                        "editable": False,
                        "type": "text",
                        "presentation": "dropdown",
                    },
                ],
                editable=False,
                fixed_rows={"headers": True},
                dropdown={"category": {"options": options}},
                page_action="none",
                filter_action="native",
                filter_query='{comment} != ""',
                virtualization=True,
                style_table={
                    "height": "35vh",
                    # "overflowY": "auto",
                    # "margin-top": 15,
                    "maxHeight": "37vh",
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
                    {"if": {"column_id": "reliable"}, "width": "20%"},
                    {"if": {"column_id": "category"}, "width": "20%"},
                ],
                style_data_conditional=[
                    {
                        "if": {"state": "selected"},  # 'active' | 'selected'
                        "border": "1px solid #006f92",
                    },
                ],
                style_header={
                    "backgroundColor": DATA_TABLE_HEADER_BGCOLOR,
                    "fontWeight": "bold",
                },
                style_header_conditional=[
                    {
                        "if": {"column_id": ["reliable", "category"]},
                        "textDecoration": "underline",
                        "textDecorationStyle": "dotted",
                    }
                ],
                tooltip_header={
                    "reliable": {
                        # "use_with": "both",
                        "type": "markdown",
                        "value": (
                            f"{i18n.t('general.reliable')} = 1 \n"
                            f"{i18n.t('general.unreliable')} = 0 \n"
                            f"{i18n.t('general.unknown')} = -1"
                        ),
                    },
                    "category": {
                        # "use_with": "both",
                        "type": "markdown",
                        "value": i18n.t("general.category"),
                    },
                },
            ),
        ],
        className="dbc dbc-row-selectable",
    )
