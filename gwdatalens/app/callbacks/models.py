import json
import os

import i18n
import pandas as pd
import pastas as ps
from dash import Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate
from pastas.extensions import register_plotly
from pastas.io.pas import PastasEncoder

from gwdatalens.app.src.components import ids

register_plotly()


# %% MODEL TAB


def register_model_callbacks(app, data):
    @app.callback(
        Output(ids.MODEL_RESULTS_CHART_1, "data"),
        Output(ids.MODEL_DIAGNOSTICS_CHART_1, "data"),
        Output(ids.PASTAS_MODEL_STORE, "data"),
        Output(ids.MODEL_SAVE_BUTTON_1, "data"),
        Output(ids.ALERT_GENERATE_MODEL, "data"),
        Input(ids.MODEL_GENERATE_BUTTON, "n_clicks"),
        State(ids.MODEL_DROPDOWN_SELECTION, "value"),
        State(ids.MODEL_DATEPICKER_TMIN, "date"),
        State(ids.MODEL_DATEPICKER_TMAX, "date"),
        State(ids.MODEL_USE_ONLY_VALIDATED, "value"),
        prevent_initial_call=True,
    )
    def generate_model(n_clicks, value, tmin, tmax, use_only_validated):
        if n_clicks is not None:
            if value is not None:
                try:
                    tmin = pd.Timestamp(tmin)
                    tmax = pd.Timestamp(tmax)
                    # get time series
                    gmw_id, tube_id = value.split("-")
                    ts = data.db.get_timeseries(gmw_id, tube_id)
                    if use_only_validated:
                        mask = ts.loc[:, data.db.qualifier_column] == "goedgekeurd"
                        ts = ts.loc[mask, data.db.value_column]
                    else:
                        ts = ts.loc[:, data.db.value_column]
                    # update stored copy
                    data.pstore.update_oseries(ts, value)
                    # create model
                    ml = ps.Model(ts)
                    data.pstore.add_recharge(ml)
                    ml.solve(freq="D", tmin=tmin, tmax=tmax, report=False)
                    ml.add_noisemodel(ps.ArNoiseModel())
                    ml.solve(
                        freq="D",
                        tmin=tmin,
                        tmax=tmax,
                        report=False,
                        initial=False,
                    )
                    mljson = json.dumps(
                        ml.to_dict(), cls=PastasEncoder
                    )  # store generated model
                    return (
                        ml.plotly.results(),
                        ml.plotly.diagnostics(),
                        mljson,
                        False,  # enable save button
                        (
                            True,  # show alert
                            "success",  # alert color
                            f"Created time series model for {value}.",
                        ),  # empty alert message
                    )
                except Exception as e:
                    return (
                        no_update,
                        no_update,
                        None,
                        True,  # disable save button
                        (
                            True,  # show alert
                            "danger",  # alert color
                            f"Error {e}",  # alert message
                        ),
                    )
            else:
                raise PreventUpdate
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.ALERT_SAVE_MODEL, "data"),
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
            try:
                data.pstore.add_model(ml, overwrite=True)
                return (
                    True,
                    "success",
                    f"Success! Saved model for {ml.oseries.name} in Pastastore!",
                )
            except Exception as e:
                return (
                    True,
                    "danger",
                    f"Error! Model for {ml.oseries.name} not saved: {e}!",
                )
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.MODEL_RESULTS_CHART_2, "data"),
        Output(ids.MODEL_DIAGNOSTICS_CHART_2, "data"),
        Output(ids.MODEL_SAVE_BUTTON_2, "data"),
        Output(ids.ALERT_PLOT_MODEL_RESULTS, "data"),
        Output(ids.MODEL_DATEPICKER_TMIN, "date"),
        Output(ids.MODEL_DATEPICKER_TMAX, "date"),
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
                    (
                        True,  # show alert
                        "success",  # alert color
                        f"Loaded time series model '{value}' from PastaStore.",
                    ),
                    ml.settings["tmin"].to_pydatetime(),
                    ml.settings["tmax"].to_pydatetime(),
                )
            except Exception as e:
                return (
                    {"layout": {"title": i18n.t("general.no_model")}},
                    {"layout": {"title": i18n.t("general.no_model")}},
                    True,
                    (
                        True,  # show alert
                        "warning",  # alert color
                        (
                            f"No model available for {value}. "
                            f"Click 'Generate Model' to create one. Error: {e}"
                        ),
                    ),
                    None,
                    None,
                )
        elif value is None:
            return (
                {"layout": {"title": i18n.t("general.no_model")}},
                {"layout": {"title": i18n.t("general.no_model")}},
                True,
                (
                    False,  # show alert
                    "success",  # alert color
                    "",  # empty message
                ),
                None,
                None,
            )

    @app.callback(
        Output(ids.MODEL_RESULTS_CHART, "figure"),
        Input(ids.MODEL_RESULTS_CHART_1, "data"),
        Input(ids.MODEL_RESULTS_CHART_2, "data"),
        prevent_initial_call=True,
    )
    def update_model_results_chart(*figs, **kwargs):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list
        if any(figs):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            figure = figs[i]
            return figure
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.MODEL_DIAGNOSTICS_CHART, "figure"),
        Input(ids.MODEL_DIAGNOSTICS_CHART_1, "data"),
        Input(ids.MODEL_DIAGNOSTICS_CHART_2, "data"),
        prevent_initial_call=True,
    )
    def update_model_diagnostics_chart(*figs, **kwargs):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any(figs):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            figure = figs[i]
            return figure
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.MODEL_SAVE_BUTTON, "disabled"),
        Input(ids.MODEL_SAVE_BUTTON_1, "data"),
        Input(ids.MODEL_SAVE_BUTTON_2, "data"),
        prevent_initial_call=True,
    )
    def toggle_model_save_button(*b, **kwargs):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any([boolean is not None for boolean in b]):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            return b[i]
        else:
            raise PreventUpdate
