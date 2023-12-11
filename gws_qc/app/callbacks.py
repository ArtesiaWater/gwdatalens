import json

import numpy as np
import pandas as pd
import pastas as ps
from app import app, data
from dash import Input, Output, State, no_update, ctx, ALL
from dash.exceptions import PreventUpdate
from icecream import ic
from pastas.extensions import register_plotly
from pastas.io.pas import PastasEncoder
from pyproj import Transformer

try:
    from .src.components import ids, tab_model, tab_overview, tab_qc, tab_traval
    from .src.components.overview_chart import plot_obs
    from .src.components.overview_map import EPSG_28992, WGS84
except ImportError:
    from src.components import ids, tab_model, tab_overview, tab_qc, tab_traval
    from src.components.overview_chart import plot_obs
    from src.components.overview_map import EPSG_28992, WGS84

register_plotly()


@app.callback(
    Output(ids.HELP_MODAL, "is_open"),
    Input(ids.HELP_BUTTON_OPEN, "n_clicks"),
    Input(ids.HELP_BUTTON_CLOSE, "n_clicks"),
    State(ids.HELP_MODAL, "is_open"),
)
def toggle_modal(n1, n2, is_open):
    """Toggle help modal window.

    Parameters
    ----------
    n1 : int
        button open help n_clicks
    n2 : int
        button close help n_clicks
    is_open : bool
        remember state of modal

    Returns
    -------
    bool
        whether window is open or closed
    """
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    Output(ids.TAB_CONTENT, "children"),
    Input(ids.TAB_CONTAINER, "value"),
    State(ids.SELECTED_OSERIES_STORE, "data"),
)
def render_tab_content(tab, selected_data):
    if tab == ids.TAB_OVERVIEW:
        return tab_overview.render_content(data)
    elif tab == ids.TAB_QC:
        return tab_qc.render_content(data, selected_data)
    elif tab == ids.TAB_MODEL:
        return tab_model.render_content(data, selected_data)
    elif tab == ids.TAB_TRAVAL:
        return tab_traval.render_content(data)
    else:
        raise PreventUpdate


@app.callback(
    Output(ids.SELECTED_OSERIES_STORE, "data"),
    Input(ids.OVERVIEW_MAP, "selectedData"),
)
def store_modeldetails_dropdown_value(selected_data):
    """Store model results tab dropdown value.

    Parameters
    ----------
    selected_data : list of dict
        selected data points from map

    Returns
    -------
    names : list of str
        list of selected names
    """
    if selected_data is not None:
        pts = pd.DataFrame(selected_data["points"])
        if not pts.empty:
            names = pts["text"].tolist()
        return names
    else:
        return None


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


# %% MODEL TAB
@app.callback(
    Output(ids.MODEL_RESULTS_CHART, "figure"),
    Output(ids.MODEL_DIAGNOSTICS_CHART, "figure"),
    Output(ids.PASTAS_MODEL_STORE, "data"),
    Output(ids.MODEL_SAVE_BUTTON, "disabled"),
    Output(ids.ALERT, "is_open", allow_duplicate=True),
    Output(ids.ALERT, "color", allow_duplicate=True),
    Output(ids.ALERT_BODY, "children", allow_duplicate=True),
    Input(ids.MODEL_GENERATE_BUTTON, "n_clicks"),
    State(ids.MODEL_DROPDOWN_SELECTION, "value"),
    prevent_initial_call=True,
)
def generate_model(_, value):
    if value is not None:
        try:
            ml = data.pstore.create_model(value, add_recharge=True)
            ml.solve(freq="D", report=False, noise=False)
            ml.solve(freq="D", noise=True, report=False, initial=False)
            mljson = json.dumps(ml.to_dict(), cls=PastasEncoder)
            return (
                ml.plotly.results(),
                ml.plotly.diagnostics(),
                mljson,
                False,  # enable save button
                False,  # show alert
                "danger",  # alert color
                "",  # empty alert message
            )
        except Exception as e:
            return (
                no_update,
                no_update,
                None,
                True,  # disable save button
                True,  # show alert
                "danger"  # alert color
                f"Error {e}",  # empty alert message
            )
    else:
        raise PreventUpdate


@app.callback(
    Output(ids.ALERT, "is_open", allow_duplicate=True),
    Output(ids.ALERT, "color", allow_duplicate=True),
    Output(ids.ALERT_BODY, "children", allow_duplicate=True),
    Input(ids.MODEL_SAVE_BUTTON, "n_clicks"),
    State(ids.PASTAS_MODEL_STORE, "data"),
    prevent_initial_call=True,
)
def save_model(n_clicks, mljson):
    if n_clicks is None:
        raise PreventUpdate
    if mljson is not None:
        with open("temp.pas", "w") as f:
            f.write(mljson)
        ml = ps.io.load("temp.pas")
        # data.pstore.add_model(ml)
        ic(f"Pretending to save {ml}!")
        return (
            True,
            "success",
            f"Success! I pretend-saved the model for {ml.oseries.name}!",
        )
    else:
        raise PreventUpdate


# %% TRAVAL TAB
@app.callback(
    Output(ids.TRAVAL_OUTPUT, "children"),
    Input({"type": "rule_input", "index": ALL}, "value"),
    # prevent_initial_call=True,
)
def update_ruleset(val):
    if val and ctx.triggered_id is not None:
        (idx, rule, param) = ctx.triggered_id["index"].split("-")
        ruledict = data.ruleset.get_rule(stepname=rule)
        ruledict["kwargs"][param] = val[int(idx)]
        data.ruleset.update_rule(**ruledict)
    return data.ruleset.to_json()
