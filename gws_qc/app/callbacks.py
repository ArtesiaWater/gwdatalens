import numpy as np
import pandas as pd
from app import app, data
from dash import Input, Output, State, no_update
from dash.exceptions import PreventUpdate
from icecream import ic
from pyproj import Transformer

try:
    from .src.components import ids, tab_overview, tab_qc
    from .src.components.overview_chart import plot_obs
    from .src.components.overview_map import EPSG_28992, WGS84
except ImportError:
    from src.components import ids, tab_overview, tab_qc
    from src.components.overview_chart import plot_obs
    from src.components.overview_map import EPSG_28992, WGS84


@app.callback(
    Output(ids.TAB_CONTENT, "children"),
    Input(ids.TAB_CONTAINER, "value"),
)
def render_tab_content(tab):
    if tab == ids.TAB_OVERVIEW:
        return tab_overview.render_content(data)
    elif tab == ids.TAB_QC:
        return tab_qc.render_content(data)
    else:
        raise PreventUpdate


@app.callback(
    Output(ids.SERIES_CHART, "figure", allow_duplicate=True),
    Input(ids.OVERVIEW_MAP, "selectedData"),
    prevent_initial_call="initial_duplicate",
)
def plot_overview_time_series(selectedData):
    # ic("point=", selectedData)

    if selectedData is not None:
        pts = pd.DataFrame(selectedData["points"])

        # get selected points
        if not pts.empty:
            names = pts["text"].tolist()
        else:
            names = None
        return plot_obs(names, data)
    else:
        # ic("no update")
        return {"layout": {"title": "No series selected."}}


@app.callback(
    Output(ids.OVERVIEW_MAP, "selectedData"),
    Input(ids.OVERVIEW_TABLE, "active_cell"),
    # prevent_initial_call=True,
    allow_duplicate=True,
)
def select_point_on_map(active_cell):
    if active_cell is None:
        return None

    df = data.gmw_to_gdf()

    # has observations
    hasobs = [f"{i}-{j}" for i, j in data.list_locations()]
    mask = df.index.isin(hasobs)
    df["metingen"] = ""
    df.loc[mask, "metingen"] = "ja"

    df["x"] = df.geometry.x
    df["y"] = df.geometry.y

    transformer = Transformer.from_proj(EPSG_28992, WGS84, always_xy=False)
    df.loc[:, ["lon", "lat"]] = np.vstack(
        transformer.transform(df["x"].values, df["y"].values)
    ).T
    loc = df.iloc[active_cell["row"]]
    return {
        "points": [
            {
                "curveNumber": 0,
                "pointNumber": active_cell["row"],
                "pointIndex": active_cell["row"],
                "lon": loc["lon"],
                "lat": loc["lat"],
                "text": loc.name,
            }
        ]
    }


@app.callback(
    Output(ids.QC_CHART, "figure"),
    Input(ids.QC_DROPDOWN_SELECTION, "value"),
    Input(ids.QC_DROPDOWN_ADDITIONAL, "value"),
)
def plot_qc_time_series(value, additional_values):
    # ic(value, additional_values)
    if value is None:
        return {"layout": {"title": "No series selected."}}
    else:
        if data.source == "bro":
            name = value.split("-")[0]
        else:
            name = value
        if additional_values is not None:
            additional = [i for i in additional_values]
        else:
            additional = []
        return plot_obs([name] + additional, data)


@app.callback(
    Output(ids.QC_DROPDOWN_ADDITIONAL, "disabled"),
    Output(ids.QC_DROPDOWN_ADDITIONAL, "options"),
    Input(ids.QC_DROPDOWN_SELECTION, "value"),
)
def enable_additional_dropdown(value):
    if value is not None:
        locs = data.list_locations_sorted_by_distance(value)
        options = [
            {"label": i + f" ({row.distance / 1e3:.1f} km)", "value": i}
            for i, row in locs.iterrows()
        ]
        return False, options
    else:
        return True, no_update


@app.callback(
    Output(ids.QC_RESULT_TABLE, "data"),
    Output(ids.QC_CHART, "figure", allow_duplicate=True),
    Input(ids.QC_TRAVAL_BUTTON, "n_clicks"),
    State(ids.QC_DROPDOWN_SELECTION, "value"),
    prevent_initial_call=True,
)
def run_traval(n_clicks, name):
    if n_clicks:
        gmw_id, tube_id = name.split("-")
        result, figure = data.run_traval(gmw_id, tube_id)
        return result, figure
    else:
        raise PreventUpdate
