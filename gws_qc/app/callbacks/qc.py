import base64
import io
import pickle
from ast import literal_eval
from copy import deepcopy

import i18n
import pandas as pd
import traval
from dash import (
    ALL,
    MATCH,
    Input,
    Output,
    Patch,
    State,
    ctx,
    dcc,
    html,
    no_update,
    set_props,
)
from dash.exceptions import PreventUpdate
from icecream import ic
from src.components.qc_rules_form import (
    derive_form_parameters,
    generate_kwargs_from_func,
    generate_traval_rule_components,
)
from traval import rulelib

try:
    from .src.components import ids
    from .src.components.overview_chart import plot_obs
except ImportError:
    from src.components import ids
    from src.components.overview_chart import plot_obs


# %% TRAVAL TAB
def register_qc_callbacks(app, data):
    @app.callback(
        Output(
            {"type": "rule_input_tooltip", "index": MATCH},
            "children",
            allow_duplicate=True,
        ),
        Input({"type": "rule_input", "index": MATCH}, "value"),
        Input({"type": "rule_input", "index": MATCH}, "disabled"),
        prevent_initial_call=True,
    )
    def update_ruleset_values(val, disabled, **kwargs):
        if not disabled:
            if len(kwargs) > 0:
                ctx_ = kwargs["callback_context"]
                triggered_id = literal_eval(ctx_.triggered[0]["prop_id"].split(".")[0])
            else:
                triggered_id = ctx.triggered_id
            (idx, rule, param) = triggered_id["index"].split("-")
            ruledict = data.traval._ruleset.get_rule(stepname=rule)
            ruledict["kwargs"][param] = val
            data.traval._ruleset.update_rule(**ruledict)
            return [str(val)]
        else:
            return no_update

    @app.callback(
        Output(ids.QC_CHART_STORE_1, "data"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        Input(ids.QC_DROPDOWN_ADDITIONAL, "value"),
        State(ids.QC_DROPDOWN_ADDITIONAL, "disabled"),
        State(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
    )
    def plot_qc_time_series(value, additional_values, disabled, traval_figure):
        if value is None:
            return {"layout": {"title": "No series selected."}}
        elif disabled:
            raise PreventUpdate
        else:
            if data.db.source == "bro":
                name = value.split("-")[0]
            else:
                name = value
            if additional_values is not None:
                additional = additional_values
            else:
                additional = []

            if traval_figure is not None:
                stored_name, figure = traval_figure
                if stored_name == name:
                    return figure

            return plot_obs([name] + additional, data)

    @app.callback(
        Output(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_1, "data"),
        Output(ids.QC_DROPDOWN_ADDITIONAL, "options"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    def enable_additional_dropdown(value):
        if value is not None:
            # value = value.split("-")
            # value[1] = int(value[1])
            locs = data.db.list_locations_sorted_by_distance(value)
            options = [
                {"label": i + f" ({row.distance / 1e3:.1f} km)", "value": i}
                for i, row in locs.iterrows()
            ]
            return False, options
        else:
            return True, no_update

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_1, "data"),
        Output(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_1, "data"),
        Input({"type": "clear-button", "index": ALL}, "n_clicks"),
        State({"type": "clear-button", "index": ALL}, "n_clicks"),
        State(ids.TRAVAL_RULES_FORM, "children"),
        prevent_initial_call=True,
    )
    def delete_rule(n_clicks, clickstate, rules, **kwargs):
        if all(v is None for v in n_clicks):
            raise PreventUpdate

        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = literal_eval(ctx_.triggered[0]["prop_id"].split(".")[0])
        else:
            triggered_id = ctx.triggered_id

        keep = []
        for rule in rules:
            if rule["props"]["id"]["index"] != triggered_id["index"]:
                keep.append(rule)
            else:
                data.traval._ruleset.del_rule(triggered_id["index"].split("-")[0])

            data.traval._ruleset.del_rule("combine_results")
            data.traval._ruleset.add_rule(
                "combine_results",
                rulelib.rule_combine_nan_or,
                apply_to=tuple(range(1, len(keep) + 1)),
            )
        # ic([rule["props"]["id"]["index"] for rule in keep])
        return keep, False

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_2, "data"),
        Output(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_2, "data"),
        Input(ids.TRAVAL_ADD_RULE_BUTTON, "n_clicks"),
        State(ids.TRAVAL_ADD_RULE_DROPDOWN, "value"),
        State(ids.TRAVAL_RULES_FORM, "children"),
        prevent_initial_call=True,
    )
    def add_rule(n_clicks, rule_to_add, current_rules):
        if n_clicks:
            try:
                rule_number = (
                    int(current_rules[-1]["props"]["id"]["index"].split("-")[-1]) + 1
                )
            except IndexError:
                rule_number = 0
            func = getattr(rulelib, rule_to_add)
            rule = {"name": rule_to_add, "kwargs": generate_kwargs_from_func(func)}
            rule["func"] = func
            irow = generate_traval_rule_components(rule, rule_number)

            # add to ruleset
            data.traval._ruleset.del_rule("combine_results")
            data.traval._ruleset.add_rule(
                rule["name"], func, apply_to=0, kwargs=rule["kwargs"]
            )
            data.traval._ruleset.add_rule(
                "combine_results",
                rulelib.rule_combine_nan_or,
                apply_to=tuple(range(1, len(current_rules) + 1)),
            )

            # patched_children = Patch()
            # patched_children.append(irow)
            # return patched_children, False
            current_rules.append(irow)
            return current_rules, False
        else:
            raise PreventUpdate

    @app.callback(
        Output({"type": "rule_input", "index": ALL}, "value"),
        Output({"type": "rule_input", "index": ALL}, "type"),
        Output({"type": "rule_input", "index": ALL}, "disabled"),
        Output({"type": "rule_input", "index": ALL}, "step"),
        Output(
            {"type": "rule_input_tooltip", "index": ALL},
            "children",
            allow_duplicate=True,
        ),
        Output(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_3, "data"),
        Output(ids.ALERT_DISPLAY_RULES_FOR_SERIES, "data"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    def display_rules_for_series(name):
        # reset ruleset to original version
        # data.traval._ruleset = deepcopy(data.traval.ruleset)

        values = []
        input_types = []
        disableds = []
        steps = []
        tooltips = []
        nrules = len(data.traval._ruleset.rules) - 1
        errors = []

        for i in range(1, nrules + 1):
            irule = data.traval._ruleset.get_rule(istep=i)
            for k, v in irule["kwargs"].items():
                if callable(v):
                    if name is not None:
                        try:
                            v = v(name)
                        except Exception as e:
                            errors.append((f"{irule['name']}: {k}", e))

                v, input_type, disabled, step = derive_form_parameters(v)
                tooltips.append(str(v))
                values.append(v)
                input_types.append(input_type)
                disableds.append(disabled)
                steps.append(step)
        if len(errors) > 0:
            return (
                values,
                input_types,
                disableds,
                steps,
                tooltips,
                False,
                (
                    True,
                    "danger",
                    f"Error! Could not load parameter(s) for: {[e[0] for e in errors]}",
                ),
            )
        else:
            return (
                values,
                input_types,
                disableds,
                steps,
                tooltips,
                False,
                (False, None, None),
            )

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_3, "data"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON, "n_clicks"),
        State(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    def reset_ruleset_to_current_default(n_clicks, name):
        if n_clicks is not None:
            form_components = []
            nrules = len(data.traval.ruleset.rules) - 1

            # reset ruleset to original version
            data.traval._ruleset = deepcopy(data.traval.ruleset)

            idx = 0
            for i in range(1, nrules + 1):
                irule = data.traval.ruleset.get_rule(istep=i)
                irow = generate_traval_rule_components(irule, idx, series_name=name)
                form_components.append(irow)
                idx += 1
            return form_components
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.TRAVAL_ADD_RULE_BUTTON, "disabled"),
        Input(ids.TRAVAL_ADD_RULE_DROPDOWN, "value"),
    )
    def activate_add_rule_button(value):
        if value is not None:
            return False
        return True

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_4, "data"),
        Output(ids.ALERT_LOAD_RULESET, "data"),
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

                # data.traval.ruleset = ruleset
                data.traval._ruleset = ruleset

                nrules = len(data.traval._ruleset.rules) - 1
                form_components = []
                idx = 0
                for i in range(1, nrules + 1):
                    irule = data.traval._ruleset.get_rule(istep=i)
                    irow = generate_traval_rule_components(irule, idx)
                    form_components.append(irow)
                    idx += 1

                return form_components, (True, "success", "Loaded ruleset")
            except Exception as e:
                return no_update, (True, "warning", f"Could not load ruleset: {e}")
        elif contents is None:
            raise PreventUpdate

    @app.callback(
        Output(ids.DOWNLOAD_TRAVAL_RULESET, "data"),
        Input(ids.TRAVAL_EXPORT_RULESET_BUTTON, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    def export_ruleset(n_clicks, name):
        timestr = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestr}_traval_ruleset_{name[0]}.pickle"
        if data.traval._ruleset is not None:
            ruleset = data.traval._ruleset.get_resolved_ruleset(name)
            rules = ruleset.rules

            def to_pickle(f):
                """Version of to_pickle that works with dcc Download component."""
                rules["name"] = name
                pickle.dump(rules, f)

            return dcc.send_bytes(to_pickle, filename=filename)

    @app.callback(
        Output(ids.DOWNLOAD_TRAVAL_PARAMETERS_CSV, "data"),
        Input(ids.TRAVAL_EXPORT_PARAMETERS_CSV_BUTTON, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    def export_parameters_csv(n_clicks, name):
        timestr = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestr}_traval_parameters_{name[0]}.csv"
        if data.traval._ruleset is not None:
            ruleset = data.traval._ruleset.get_resolved_ruleset(name)
            traval_params = traval.TravalParameters.from_ruleset(ruleset)
            return dcc.send_string(traval_params.to_csv, filename=filename)

    @app.callback(
        Output(ids.QC_COLLAPSE_CONTENT, "is_open"),
        Output(ids.QC_COLLAPSE_BUTTON, "children"),
        Input(ids.QC_COLLAPSE_BUTTON, "n_clicks"),
        State(ids.QC_COLLAPSE_CONTENT, "is_open"),
    )
    def toggle_collapse(n, is_open):
        if n:
            if not is_open:
                button_text = [
                    html.I(className="fa-solid fa-chevron-down"),
                    " " + i18n.t("general.hide_parameters"),
                ]
                return not is_open, button_text
            else:
                button_text = [
                    html.I(className="fa-solid fa-chevron-right"),
                    " " + i18n.t("general.show_parameters"),
                ]
                return not is_open, button_text
        # button_text = [
        #     html.I(className="fa-solid fa-chevron-left"),
        #     " Show parameters",
        # ]
        return is_open, no_update

    # @app.callback(
    #     Output(ids.LOADING_QC_CHART_STORE_1, "data"),
    #     Output(ids.RUN_TRAVAL_STORE, "data"),
    #     Input(ids.QC_RUN_TRAVAL_BUTTON, "n_clicks"),
    # )
    # def trigger_traval_run_and_loading_state(n_clicks):
    #     if n_clicks:
    #         return pd.Timestamp.now().isoformat(), n_clicks
    #     else:
    #         raise PreventUpdate

    @app.callback(
        # Output(ids.QC_CHART, "figure", allow_duplicate=True),  # NOTE: Remove for DJANGO
        Output(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
        Output(ids.TRAVAL_RESULT_TABLE_STORE, "data"),
        Output(ids.QC_DROPDOWN_ADDITIONAL, "value"),
        Output(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_2, "data"),
        # Output(ids.LOADING_QC_CHART_STORE_2, "data"),
        Input(ids.QC_RUN_TRAVAL_BUTTON, "n_clicks"),
        # Input(ids.RUN_TRAVAL_STORE, "data"),
        State(ids.QC_DROPDOWN_SELECTION, "value"),
        State(ids.QC_DATEPICKER_TMIN, "date"),
        State(ids.QC_DATEPICKER_TMAX, "date"),
        State(ids.QC_RUN_ONLY_UNVALIDATED_CHECKBOX, "value"),
        background=False,
        # NOTE: only used if background is True
        # running=[
        #     (Output(ids.QC_RUN_TRAVAL_BUTTON, "disabled"), True, False),
        #     (Output(ids.QC_CANCEL_BUTTON, "disabled"), False, True),
        # ],
        # cancel=[Input(ids.QC_CANCEL_BUTTON, "n_clicks")],
        prevent_initial_call=True,
    )
    def run_traval(n_clicks, name, tmin, tmax, only_unvalidated):
        if n_clicks:
            set_props(ids.LOADING_QC_CHART, {"display": "show"})
            gmw_id, tube_id = name.split("-")
            result, figure = data.traval.run_traval(
                gmw_id, tube_id, tmin=tmin, tmax=tmax, only_unvalidated=only_unvalidated
            )
            return (
                # {"layout": {"title": "Running TRAVAL..."}},  # figure
                (name, figure),
                result.reset_index().to_dict("records"),
                None,
                True,
                # "auto"
            )
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.QC_CHART_STORE_2, "data"),
        # Output(ids.LOADING_QC_CHART_STORE_2, "data"),
        Input(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
        Input(ids.TRAVAL_RESULT_TABLE_STORE, "data"),
        prevent_initial_call=True,
    )
    def update_traval_figure(figure, table):
        if figure is not None:
            # set result table
            df = pd.DataFrame(table).set_index("datetime")
            df.index = pd.to_datetime(df.index)
            data.traval.traval_result = df
            return (
                figure[1],
                # "hide",
            )
        else:
            # data.traval.traval_result = None
            return (
                no_update,
                # "hide",
            )

    @app.callback(
        Output(ids.QC_DROPDOWN_ADDITIONAL, "disabled"),
        Input(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_1, "data"),
        Input(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_2, "data"),
        prevent_initial_call=True,
    )
    def toggle_qc_dropdown_additional(*disabled, **kwargs):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any(disabled):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            return disabled[i]
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM, "children"),
        Input(ids.TRAVAL_RULES_FORM_STORE_1, "data"),
        Input(ids.TRAVAL_RULES_FORM_STORE_2, "data"),
        Input(ids.TRAVAL_RULES_FORM_STORE_3, "data"),
        Input(ids.TRAVAL_RULES_FORM_STORE_4, "data"),
        prevent_initial_call=True,
    )
    def update_traval_rules_form(*forms, **kwargs):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        for i in range(len(inputs_list)):
            if inputs_list[i]["id"] == triggered_id:
                break
        return forms[i] if forms[i] is not None else no_update

    @app.callback(
        Output(ids.TRAVAL_RESET_RULESET_BUTTON, "disabled"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_1, "data"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_2, "data"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_3, "data"),
        prevent_initial_call=True,
    )
    def toggle_reset_ruleset_button(*bools, **kwargs):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any([boolean is not None for boolean in bools]):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            return bools[i]
        else:
            raise PreventUpdate

    # @app.callback(
    #     Output(ids.LOADING_QC_CHART, "display"),
    #     Input(ids.LOADING_QC_CHART_STORE_2, "data"),
    #     Input(ids.LOADING_QC_CHART_STORE_1, "data"),
    #     prevent_initial_call=True,
    # )
    # def toggle_chart_loading_state(*states, **kwargs):
    #     if len(kwargs) > 0:
    #         ctx_ = kwargs["callback_context"]
    #         triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
    #         inputs_list = ctx_.inputs_list
    #     else:
    #         triggered_id = ctx.triggered_id
    #         inputs_list = ctx.inputs_list
    #     ic(triggered_id)
    #     ic(states)
    #     if any(states):
    #         for i in range(len(ctx.inputs_list)):
    #             if inputs_list[i]["id"] == triggered_id:
    #                 break
    #         return "auto" if i == 0 else "show"
    #     else:
    #         raise PreventUpdate

    @app.callback(
        Output(ids.QC_CHART, "figure"),
        Output(ids.LOADING_QC_CHART, "display"),
        Input(ids.QC_CHART_STORE_1, "data"),
        Input(ids.QC_CHART_STORE_2, "data"),
        prevent_initial_call=True,
    )
    def display_qc_chart(*figures, **kwargs):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any(figures):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            return figures[i], "auto"
        else:
            raise PreventUpdate
