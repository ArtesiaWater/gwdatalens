import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, html
from dash.exceptions import PreventUpdate

try:
    from gwdatalens.app.src.components import (
        ids,
        tab_model,
        tab_overview,
        tab_qc,
        tab_qc_result,
    )
except ImportError:
    from src.components import (
        ids,
        tab_model,
        tab_overview,
        tab_qc,
        tab_qc_result,
    )


def register_general_callbacks(app, data):
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
        State(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
    )
    def render_tab_content(tab, selected_data, figure):
        if tab == ids.TAB_OVERVIEW:
            return tab_overview.render_content(data, selected_data)
        elif tab == ids.TAB_MODEL:
            return tab_model.render_content(data, selected_data)
        elif tab == ids.TAB_QC:
            return tab_qc.render_content(data, selected_data)
        elif tab == ids.TAB_QC_RESULT:
            return tab_qc_result.render_content(
                data, figure[1] if figure is not None else None
            )
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.ALERT_DIV, "children"),
        Input(ids.ALERT_TIME_SERIES_CHART, "data"),
        Input(ids.ALERT_DISPLAY_RULES_FOR_SERIES, "data"),
        Input(ids.ALERT_GENERATE_MODEL, "data"),
        Input(ids.ALERT_SAVE_MODEL, "data"),
        Input(ids.ALERT_PLOT_MODEL_RESULTS, "data"),
        Input(ids.ALERT_LOAD_RULESET, "data"),
        Input(ids.ALERT_EXPORT_TO_DB, "data"),
        Input(ids.ALERT_MARK_OBS, "data"),
        Input(ids.ALERT_LABEL_OBS, "data"),
        prevent_initial_call=True,
    )
    def show_alert(*args, **kwargs):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any(args):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            alert_data = args[i]
            is_open, color, message = alert_data
        else:
            raise PreventUpdate
        return [
            dbc.Alert(
                children=[
                    html.P(message, id=ids.ALERT_BODY),
                ],
                id=ids.ALERT,
                color=color,
                dismissable=True,
                duration=4000,
                fade=True,
                is_open=is_open,
            ),
        ]