import base64
import io
import json
import pickle

import numpy as np
import pandas as pd
import pastas as ps
import traval
from app import app, data
from dash import ALL, Input, Output, Patch, State, ctx, no_update
from dash.exceptions import PreventUpdate
from icecream import ic
from pastas.extensions import register_plotly
from pastas.io.pas import PastasEncoder
from src.components.qc_rules_form import (
    generate_kwargs_from_func,
    generate_traval_rule_components,
)
from traval import rulelib

try:
    from .src.components import ids, tab_model, tab_overview, tab_qc, tab_qc_result
    from .src.components.overview_chart import plot_obs
except ImportError:
    from src.components import ids, tab_model, tab_overview, tab_qc, tab_qc_result
    from src.components.overview_chart import plot_obs


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
    elif tab == ids.TAB_QC_RESULT:
        return tab_qc_result.render_content(data)
    else:
        raise PreventUpdate


@app.callback(
    Output(ids.SELECTED_OSERIES_STORE, "data"),
    Input(ids.OVERVIEW_MAP, "selectedData"),
    State(ids.SELECTED_OSERIES_STORE, "data"),
)
def store_modeldetails_dropdown_value(selected_data, current_value):
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
            return None if current_value is None else current_value
    else:
        return None if current_value is None else current_value


@app.callback(
    Output(ids.SERIES_CHART, "figure", allow_duplicate=True),
    Output(ids.ALERT, "is_open", allow_duplicate=True),
    Output(ids.ALERT, "color", allow_duplicate=True),
    Output(ids.ALERT_BODY, "children", allow_duplicate=True),
    Input(ids.OVERVIEW_MAP, "selectedData"),
    State(ids.SELECTED_OSERIES_STORE, "data"),
    prevent_initial_call="initial_duplicate",
)
def plot_overview_time_series(selectedData, selected_oseries):
    # ic(selectedData)

    if selectedData is not None:
        pts = pd.DataFrame(selectedData["points"])

        # get selected points
        if not pts.empty:
            names = pts["text"].tolist()
        else:
            names = None
        try:
            chart = plot_obs(names, data)
            if chart is not None:
                return (
                    chart,
                    False,
                    None,
                    None,
                )
            else:
                return (
                    {"layout": {"title": "No series selected."}},
                    True,
                    "warning",
                    f"No data to plot for: {names}.",
                )
        except Exception as e:
            raise e
            return (
                {"layout": {"title": "No series selected."}},
                True,  # show alert
                "danger",  # alert color
                f"Error! Something went wrong: {e}",  # alert message
            )
    elif selected_oseries is not None:
        chart = plot_obs(selected_oseries, data)
        return (
            chart,
            False,
            None,
            None,
        )
    else:
        # ic("no update")
        return (
            {"layout": {"title": "No series selected."}},
            False,
            None,
            None,
        )


@app.callback(
    Output(ids.OVERVIEW_MAP, "selectedData"),
    Output(ids.OVERVIEW_MAP, "selectedpoints"),
    Output(ids.OVERVIEW_MAP, "figure"),
    Input(ids.OVERVIEW_TABLE, "active_cell"),
    State(ids.OVERVIEW_MAP, "figure"),
    # prevent_initial_call=True,
)
def highlight_point_on_map_from_table(active_cell, figure):
    if active_cell is None:
        return None, [], no_update

    ic(active_cell)
    df = data.db.gmw_gdf.reset_index()
    loc = df.loc[active_cell["row"]]
    pts = [active_cell["row"]]

    uirevision = figure["layout"]["uirevision"]
    uirevision = True if uirevision is None else ~uirevision
    figure["layout"]["uirevision"] = uirevision
    
    return (
        {
            "points": [
                {
                    "curveNumber": 0,
                    "pointNumber": active_cell["row"],
                    "pointIndex": active_cell["row"],
                    "lon": loc["lon"],
                    "lat": loc["lat"],
                    "text": f"{loc.bro_id}-{loc.tube_number:03g}",
                }
            ]
        },
        pts,
        figure,
    )


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
        if data.db.source == "bro":
            name = value.split("-")[0]
        else:
            name = value
        if additional_values is not None:
            additional = [i for i in additional_values]
        else:
            additional = []
        return plot_obs([name] + additional, data)


# @app.callback(
#     Output(ids.QC_DROPDOWN_ADDITIONAL, "disabled"),
#     Output(ids.QC_DROPDOWN_ADDITIONAL, "options"),
#     Input(ids.QC_DROPDOWN_SELECTION, "value"),
# )
# def enable_additional_dropdown(value):
#     if value is not None:
#         ic(value)
#         # value = value.split("-")
#         # value[1] = int(value[1])
#         locs = data.db.list_locations_sorted_by_distance(value)
#         options = [
#             {"label": i + f" ({row.distance / 1e3:.1f} km)", "value": i}
#             for i, row in locs.iterrows()
#         ]
#         return False, options
#     else:
#         return True, no_update


@app.callback(
    # Output(ids.QC_RESULT_TABLE, "data"),
    Output(ids.QC_CHART, "figure", allow_duplicate=True),
    Input(ids.QC_RUN_TRAVAL_BUTTON, "n_clicks"),
    State(ids.QC_DROPDOWN_SELECTION, "value"),
    prevent_initial_call=True,
)
def run_traval(n_clicks, name):
    if n_clicks:
        gmw_id, tube_id = name.split("-")
        result, figure = data.traval.run_traval(gmw_id, tube_id)
        data.traval.traval_result = result
        data.traval.figure = figure
        # return result, figure
        return figure
    else:
        raise PreventUpdate


@app.callback(
    Output(ids.QC_RESULT_CHART, "figure"),
    Output(ids.QC_RESULT_EXPORT_CSV, "disabled"),
    Output(ids.QC_RESULT_EXPORT_DB, "disabled"),
    Input(ids.TAB_CONTAINER, "value"),
    State(ids.SELECTED_OSERIES_STORE, "value"),
)
def qc_result_traval_figure(tab, value):
    if tab == ids.TAB_QC_RESULT:
        if hasattr(data.traval, "figure"):
            return (data.traval.figure, False, False)
        else:
            return ({"layout": {"title": "No traval result."}}, True, True)
    else:
        raise PreventUpdate


# %% MODEL TAB
@app.callback(
    Output(ids.MODEL_RESULTS_CHART, "figure", allow_duplicate=True),
    Output(ids.MODEL_DIAGNOSTICS_CHART, "figure", allow_duplicate=True),
    Output(ids.PASTAS_MODEL_STORE, "data"),
    Output(ids.MODEL_SAVE_BUTTON, "disabled", allow_duplicate=True),
    Output(ids.ALERT, "is_open", allow_duplicate=True),
    Output(ids.ALERT, "color", allow_duplicate=True),
    Output(ids.ALERT_BODY, "children", allow_duplicate=True),
    Input(ids.MODEL_GENERATE_BUTTON, "n_clicks"),
    State(ids.MODEL_DROPDOWN_SELECTION, "value"),
    prevent_initial_call=True,
)
def generate_model(n_clicks, value):
    if n_clicks is not None:
        if value is not None:
            try:
                ml = data.pstore.create_model(value, add_recharge=True)
                ml.solve(freq="D", report=False, noise=False)
                ml.solve(freq="D", noise=True, report=False, initial=False)
                mljson = json.dumps(
                    ml.to_dict(), cls=PastasEncoder
                )  # store generated model
                return (
                    ml.plotly.results(),
                    ml.plotly.diagnostics(),
                    mljson,
                    False,  # enable save button
                    True,  # show alert
                    "success",  # alert color
                    f"Created time series model for {value}.",  # empty alert message
                )
            except Exception as e:
                return (
                    no_update,
                    no_update,
                    None,
                    True,  # disable save button
                    True,  # show alert
                    "danger",  # alert color
                    f"Error {e}",  # alert message
                )
        else:
            raise PreventUpdate
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
        os.remove("temp.pas")
        data.pstore.add_model(ml, overwrite=True)
        # ic(f"Pretending to save {ml}!")
        return (
            True,
            "success",
            f"Success! Saved model for {ml.oseries.name} in Pastastore!",
        )
    else:
        raise PreventUpdate


@app.callback(
    Output(ids.MODEL_RESULTS_CHART, "figure", allow_duplicate=True),
    Output(ids.MODEL_DIAGNOSTICS_CHART, "figure", allow_duplicate=True),
    Output(ids.MODEL_SAVE_BUTTON, "disabled", allow_duplicate=True),
    Output(ids.ALERT, "is_open", allow_duplicate=True),
    Output(ids.ALERT, "color", allow_duplicate=True),
    Output(ids.ALERT_BODY, "children", allow_duplicate=True),
    Input(ids.MODEL_DROPDOWN_SELECTION, "value"),
    prevent_initial_call=True,
)
def plot_model_results(value):
    if value is not None:
        try:
            ml = data.pstore.get_models(value)
            return (
                ml.plotly.results(),
                ml.plotly.diagnostics(),
                True,
                True,  # show alert
                "success",  # alert color
                f"Loaded time series model '{value}' from PastaStore.",  # empty alert message
            )
        except Exception as e:
            return (
                {"layout": {"title": "No model."}},
                {"layout": {"title": "No model."}},
                True,
                True,  # show alert
                "warning",  # alert color
                f"No model available for {value}. Click 'Generate Model' to create one.",
            )
    elif value is None:
        return (
            {"layout": {"title": "No model."}},
            {"layout": {"title": "No model."}},
            True,
            False,  # show alert
            "success",  # alert color
            "",  # empty message
        )

# %% TRAVAL TAB
@app.callback(
    Output(ids.TRAVAL_OUTPUT, "children"),
    Input({"type": "rule_input", "index": ALL}, "value"),
    # prevent_initial_call=True,
)
def update_ruleset_values(val):
    if val and ctx.triggered_id is not None:
        for i in range(len(val)):
            if ctx.inputs_list[0][i]["id"] == ctx.triggered_id:
                break
        (idx, rule, param) = ctx.triggered_id["index"].split("-")
        ruledict = data.traval.ruleset.get_rule(stepname=rule)
        ruledict["kwargs"][param] = val[i]
        data.traval.update_rule(**ruledict)
    return data.traval.to_json()


# @app.callback(
#     Output(ids.TRAVAL_OUTPUT, "children", allow_duplicate=True),
#     Input(ids.TRAVAL_RULES_FORM, "children"),
#     prevent_initial_call=True,
# )
# def update_ruleset(rules):
#     return data.traval.to_json()


@app.callback(
    Output(ids.TRAVAL_RULES_FORM, "children", allow_duplicate=True),
    Input({"type": "clear-button", "index": ALL}, "n_clicks"),
    State(ids.TRAVAL_RULES_FORM, "children"),
    prevent_initial_call=True,
)
def delete_rule(n_clicks, rules):
    if all(v is None for v in n_clicks):
        raise PreventUpdate
    keep = []
    for rule in rules:
        if rule["props"]["id"]["index"] != ctx.triggered_id["index"]:
            keep.append(rule)
        else:
            data.traval.ruleset.del_rule(ctx.triggered_id["index"].split("-")[0])

        data.traval.ruleset.del_rule("combine_results")
        data.traval.ruleset.add_rule(
            "combine_results",
            rulelib.rule_combine_nan_or,
            apply_to=tuple(range(1, len(keep) + 1)),
        )
    return keep


@app.callback(
    Output(ids.TRAVAL_RULES_FORM, "children", allow_duplicate=True),
    Input(ids.TRAVAL_ADD_RULE_BUTTON, "n_clicks"),
    State(ids.TRAVAL_ADD_RULE_DROPDOWN, "value"),
    State(ids.TRAVAL_RULES_FORM, "children"),
    prevent_initial_call=True,
)
def display_rules(n_clicks, rule_to_add, current_rules):
    try:
        rule_number = int(current_rules[-1]["props"]["id"]["index"].split("-")[-1]) + 1
    except IndexError:
        rule_number = 0
    func = getattr(rulelib, rule_to_add)
    rule = {"name": rule_to_add, "kwargs": generate_kwargs_from_func(func)}
    irow = generate_traval_rule_components(rule, rule_number)

    # add to ruleset
    data.traval.ruleset.del_rule("combine_results")
    data.traval.ruleset.add_rule(rule["name"], func, apply_to=0, kwargs=rule["kwargs"])
    data.traval.ruleset.add_rule(
        "combine_results",
        rulelib.rule_combine_nan_or,
        apply_to=tuple(range(1, len(current_rules) + 1)),
    )

    patched_children = Patch()
    patched_children.append(irow)
    return patched_children


@app.callback(
    Output({"type": "rule_input", "index": ALL}, "value"),
    Output({"type": "rule_input", "index": ALL}, "type"),
    Output({"type": "rule_input", "index": ALL}, "disabled"),
    Output({"type": "rule_input", "index": ALL}, "step"),
    Input(ids.QC_DROPDOWN_SELECTION, "value"),
    prevent_initial_call=False,
)
def display_rules_for_series(name):
    values = []
    input_types = []
    disableds = []
    steps = []
    nrules = len(data.traval.ruleset.rules) - 1

    for i in range(1, nrules + 1):
        irule = data.traval.ruleset.get_rule(istep=i)
        for _, v in irule["kwargs"].items():
            if callable(v):
                if name is not None:
                    v = v(name)
            v, input_type, disabled, step = derive_form_parameters(v)
            values.append(v)
            input_types.append(input_type)
            disableds.append(disabled)
            steps.append(step)
    return values, input_types, disableds, steps


@app.callback(
    Output(ids.TRAVAL_ADD_RULE_BUTTON, "disabled"),
    Input(ids.TRAVAL_ADD_RULE_DROPDOWN, "value"),
)
def activate_add_rule_button(value):
    if value is not None:
        return False
    return True


@app.callback(
    Output(ids.TRAVAL_RULES_FORM, "children", allow_duplicate=True),
    Output(ids.ALERT, "is_open", allow_duplicate=True),
    Output(ids.ALERT, "color", allow_duplicate=True),
    Output(ids.ALERT_BODY, "children", allow_duplicate=True),
    Input(ids.TRAVAL_LOAD_RULESET_BUTTON, "contents"),
    prevent_initial_call=True,
)
def load_ruleset(contents):
    """Get input timeseries data.

    Parameters
    ----------
    contents : str
        64bit encoded input data

    Returns
    -------
    series : pandas.Series
        input series data
    """
    if contents is not None:
        try:
            content_type, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)
            rules = pickle.load(io.BytesIO(decoded))

            ruleset = traval.RuleSet(name=rules.pop("name"))
            ruleset.rules.update(rules)

            data.traval.ruleset = ruleset
            nrules = len(data.traval.ruleset.rules) - 1
            form_components = []
            idx = 0
            for i in range(1, nrules + 1):
                irule = data.traval.ruleset.get_rule(istep=i)
                irow = generate_traval_rule_components(irule, idx)
                form_components.append(irow)
                idx += 1

            return form_components, True, "success", "Loaded ruleset"
        except Exception as e:
            return no_update, True, "warning", f"Could not load ruleset: {e}"
    elif contents is None:
        raise PreventUpdate
