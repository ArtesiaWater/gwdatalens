from functools import partial

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go
import pandas as pd

from . import ids
from ..data.source import DataSource


def render(app: Dash, data: DataSource):
    @app.callback(
        Output(ids.SERIES_CHART, "figure"),
        [Input(ids.OVERVIEW_MAP, "selectedData")],
        # prevent_initial_call=True,
        allow_duplicate=True,
    )
    def plot_series(selectedData):
        # print("point=", selectedData)

        if selectedData is not None:
            
            pts = pd.DataFrame(selectedData["points"])

            # get selected points
            if not pts.empty:
                names = pts["text"].tolist()
            else:
                names = None
            return plot_obs(names, data)
        else:
            # print("no update")
            return {"layout": {"title": "No series selected."}}

    return html.Div(
        id="series-chart-div",
        children=[
            dcc.Loading(
                id=ids.LOADING_SERIES_CHART,
                type="dot",
                style={"position": "absolute", "align-self": "center"},
                parent_className="loading-wrapper",
                children=[
                    dcc.Graph(
                        id=ids.SERIES_CHART,
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


def plot_obs(names, data):
    
    hasobs = [i for i, _ in data.list_locations()]

    if names is None:
        return {"layout": {"title": "No series to plot"}}

    traces = []
    for name in names:
        # no obs
        if name not in hasobs:
            print("no data", name)
            return {"layout": {"title": "No series to plot"}}
        
        ts = data.get_timeseries(gmw_id=name, tube_id=1, column="field_value")
        print("time series", name)
        if ts is None:
            continue
        trace_i = go.Scattergl(
            x=ts.index,
            y=ts.values,
            mode="markers",
            marker={"color": "blue", "size": 3},
            name=name,
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
