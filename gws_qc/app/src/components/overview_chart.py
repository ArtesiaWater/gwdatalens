import i18n
import plotly.graph_objs as go
from dash import dcc, html

from . import ids


def render(data, selected_data):
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
                        figure=plot_obs(selected_data, data),
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
    hasobs = [i for i in data.db.list_locations()]

    if names is None:
        return {"layout": {"title": i18n.t("general.no_plot")}}

    title = None

    traces = []
    for name in names:
        # split into monitoringwell and tube_number
        monitoring_well, tube_nr = name.split("-")
        tube_nr = int(tube_nr)

        # no obs
        if name not in hasobs:
            title = i18n.t("general.no_plot")
            continue

        df = data.db.get_timeseries(gmw_id=monitoring_well, tube_id=tube_nr)

        if df is None:
            continue

        df.loc[:, data.db.qualifier_column] = df.loc[
            :, data.db.qualifier_column
        ].fillna("")

        if len(names) == 1:
            title = name
            # plot different qualifiers
            for qualifier in df[data.db.qualifier_column].unique():
                mask = df[data.db.qualifier_column] == qualifier
                ts = df.loc[mask, data.db.value_column]
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
            title = None
            ts = df[data.db.value_column]
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
        "title": title,
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
