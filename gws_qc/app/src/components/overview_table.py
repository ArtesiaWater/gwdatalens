from dash import dash_table, html
from dash.dash_table.Format import Format

from ..data.source import DataSource
from . import ids
from .styling import DATA_TABLE_HEADER_BGCOLOR


def render(data: DataSource):
    df = data.gmw_to_gdf()

    df.sort_values(
        ["metingen", "nitg_code", "tube_number"], ascending=False, inplace=True
    )

    df["x"] = df.geometry.x
    df["y"] = df.geometry.y
    usecols = [
        "bro_id",
        # "nitg_code",
        "tube_number",
        "screen_top",
        "screen_bot",
        "x",
        "y",
        "metingen",
    ]

    return html.Div(
        id="table-div",
        children=[
            dash_table.DataTable(
                id=ids.OVERVIEW_TABLE,
                data=df.loc[:, usecols].to_dict("records"),
                columns=[
                    {
                        "id": "bro_id",
                        "name": "Naam",
                        "type": "text",
                    },
                    # {
                    #     "id": "nitg_code",
                    #     "name": "NITG-code",
                    #     "type": "text",
                    # },
                    {
                        "id": "tube_number",
                        "name": "Filternummer",
                        "type": "numeric",
                        # "format": Format(scheme="r", precision=1),
                    },
                    {
                        "id": "screen_top",
                        "name": "Bovenzijde filter\n[m NAP]",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "id": "screen_bot",
                        "name": "Onderzijde filter\n[m NAP]",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "id": "x",
                        "name": "X\n[m RD]",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=5),
                    },
                    {
                        "id": "y",
                        "name": "Y\n[m RD]",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=5),
                    },
                    {
                        "id": "metingen",
                        "name": "Metingen",
                        "type": "numeric",
                        "format": {"specifier": ".0f"},
                    },
                ],
                fixed_rows={"headers": True},
                page_action="none",
                style_table={
                    # "height": "70vh",
                    # "overflowY": "auto",
                    "margin-top": 15,
                    # "maxHeight": "70vh",
                },
                # row_selectable="multi",
                style_cell={"whiteSpace": "pre-line", "fontSize": 12},
                style_cell_conditional=[
                    {
                        "if": {"column_id": c},
                        "textAlign": "left",
                    }
                    for c in ["bro_id"]
                ]
                + [
                    {"if": {"column_id": "bro_id"}, "width": "15%"},
                    {"if": {"column_id": "nitg_code"}, "width": "10%"},
                    {"if": {"column_id": "tube_number"}, "width": "10%"},
                    {"if": {"column_id": "screen_top"}, "width": "15%"},
                    {"if": {"column_id": "screen_bot"}, "width": "15%"},
                    {"if": {"column_id": "x"}, "width": "10%"},
                    {"if": {"column_id": "y"}, "width": "10%"},
                    {"if": {"column_id": "metingen"}, "width": "15%"},
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
