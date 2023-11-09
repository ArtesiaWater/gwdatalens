from functools import partial

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go

from . import ids
from ..data.source import DataSource


def render(app: Dash, data: DataSource):
    @app.callback(
        Output(ids.QC_CHART, "figure"),
        [Input(ids.QC_RULES, "active_cell")],
        # prevent_initial_call=True,
        allow_duplicate=True,
    )
    def plot_qc_series(selectedData):
        # print("point=", selectedData)
        print("hoho")
        if hasattr(data, "df"):
            df = data.df
            traces = []
            # plot different qualifiers
            for qualifier in df[data.qualifier_column].unique():
                if qualifier == "goedgekeurd":
                    color = "green"
                elif qualifier == "nogNietBeoordeeld":
                    color = "orange"
                else:
                    color = "blue"
                mask = df[data.qualifier_column] == qualifier
                ts = df.loc[mask, data.value_column]
                trace_i = go.Scattergl(
                    x=ts.index,
                    y=ts.values,
                    mode="markers",
                    marker={"color": color, "size": 3},
                    name=qualifier,
                    legendgroup="0",
                    showlegend=True,
                )
                traces.append(trace_i)

            layout = {
                # "xaxis": {"range": [sim.index[0], sim.index[-1]]},
                "yaxis": {"title": "(m NAP)"},
                "legend": {
                    "traceorder": "reversed+grouped",
                    "orientation": "h",
                    "xanchor": "left",
                    "yanchor": "bottom",
                    "x": 0.0,
                    "y": 1.02,
                },
                "dragmode": "pan",
                # "margin": dict(t=70, b=40, l=40, r=10),
            }
            return dict(data=traces, layout=layout)
        else:
            return {"layout": {"title": "No series selected."}}

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
                        id=ids.QC_CHART,
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
