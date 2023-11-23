import plotly.graph_objs as go
from dash import dcc, html
from icecream import ic

from . import ids


def render():
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
    # ic(names)
    hasobs = [i for i, _ in data.list_locations()]

    if names is None:
        return {"layout": {"title": "No series to plot"}}

    traces = []
    for name in names:
        # split into monitoringwell and tub_id
        if data.source == "dino":
            monitoring_well, tube_nr = name.split("-")
        else:
            monitoring_well = name
            tube_nr = 1

        # no obs
        if monitoring_well not in hasobs:
            ic("no data", monitoring_well)
            return {"layout": {"title": "No series to plot"}}

        df = data.get_timeseries(gmw_id=monitoring_well, tube_id=tube_nr)
        df.loc[:, data.qualifier_column] = df.loc[:, data.qualifier_column].fillna("")

        # ic("time series", monitoring_well, tube_nr)
        if df is None:
            continue
        if len(names) == 1:
            data.df = df
            # plot different qualifiers
            for qualifier in df[data.qualifier_column].unique():
                mask = df[data.qualifier_column] == qualifier
                ts = df.loc[mask, data.value_column]
                legendrank = 1000
                if qualifier == "goedgekeurd":
                    color = "green"
                elif qualifier == "nogNietBeoordeeld":
                    color = "orange"
                elif qualifier == "":
                    color = None
                    qualifier = f"{name}-{tube_nr}"
                    legendrank = 999
                else:
                    color = None
                trace_i = go.Scattergl(
                    x=ts.index,
                    y=ts.values,
                    mode="markers+lines",
                    line={"width": 1},
                    marker={"color": color, "size": 3},
                    name=qualifier,
                    legendgroup=qualifier,
                    showlegend=True,
                    legendrank=legendrank,
                )
                traces.append(trace_i)
        else:
            data.df = None
            # TODO: plot each series with its own color
            ts = df[data.value_column]
            trace_i = go.Scattergl(
                x=ts.index,
                y=ts.values,
                mode="markers+lines",
                line={"width": 1},
                marker={"size": 3},
                name=name,
                legendgroup=f"{name}-{tube_nr}",
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
