import dash_bootstrap_components as dbc
from dash import dcc, html

from ..data.source import DataInterface
from . import ids, qc_results_table


def render():
    return dcc.Tab(
        label="QC Result",
        value=ids.TAB_QC_RESULT,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_export_to_csv_button():
    return html.Div(
        [
            dbc.Button(
                html.Span(
                    [
                        html.I(className="fa-solid fa-file-csv"),
                        " Export CSV",
                    ],
                    id="span-export-csv",
                    n_clicks=0,
                ),
                style={
                    "margin-top": 10,
                    "margin-bottom": 10,
                },
                disabled=True,
                id=ids.QC_RESULT_EXPORT_CSV,
            ),
            dcc.Download(id=ids.DOWNLOAD_EXPORT_CSV),
        ]
    )


def render_export_to_database_button():
    return html.Div(
        dbc.Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-database"),
                    " Export to DB",
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
            },
            disabled=True,
            id=ids.QC_RESULT_EXPORT_DB,
        ),
    )


def render_qc_chart():
    return html.Div(
        id="series-chart-div",
        children=[
            dcc.Loading(
                id=ids.LOADING_QC_CHART,
                type="dot",
                style={"position": "absolute", "align-self": "center"},
                parent_className="loading-wrapper",
                children=[
                    dcc.Graph(
                        id=ids.QC_RESULT_CHART,
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                        },
                        style={
                            "height": "40vh",
                            # "margin-bottom": "10px",
                            # "margin-top": 5,
                        },
                    ),
                ],
            ),
        ],
        style={
            "position": "relative",
            "justify-content": "center",
            "margin-bottom": 10,
        },
    )


def render_content(data: DataInterface):
    return dbc.Container(
        [
            dbc.Row([render_qc_chart()]),
            dbc.Row([qc_results_table.render(data)]),
            dbc.Row(
                [
                    dbc.Col([render_export_to_csv_button()], width="auto"),
                    dbc.Col([render_export_to_database_button()], width="auto"),
                ]
            ),
        ],
        fluid=True,
    )
