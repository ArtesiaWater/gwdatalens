import numpy as np
import pandas as pd
from dash import Input, Output, Patch, State, dcc, no_update
from dash.exceptions import PreventUpdate
from icecream import ic

try:
    from .src.components import ids

except ImportError:
    from src.components import ids


def register_result_callbacks(app, data):
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

    @app.callback(
        Output(ids.QC_RESULT_TABLE, "data", allow_duplicate=True),
        Input(ids.QC_RESULT_TABLE, "derived_virtual_data"),
        State(ids.QC_RESULT_TABLE, "columns"),
        State(ids.QC_RESULT_TABLE, "selected_cells"),
        # State(ids.QC_RESULT_TABLE, "data"),
        prevent_initial_call=True,
    )
    def multi_edit_qc_results_table(filtered_data, cols, selected_cells):
        if selected_cells is None or selected_cells == []:
            raise PreventUpdate
        selected_columns = [c["column_id"] for c in selected_cells]
        if not np.any(np.isin(selected_columns, ["manual_check", "category"])):
            raise PreventUpdate
        selected_row_id = [c["row_id"] for c in selected_cells]
        changed_cell = selected_cells[0]
        new_value = filtered_data[changed_cell["row"]][changed_cell["column_id"]]

        for r in filtered_data:
            if r["id"] in selected_row_id:
                mask = data.traval.traval_result["id"] == r["id"]
                data.traval.traval_result.loc[mask, changed_cell["column_id"]] = (
                    new_value
                )
                r[changed_cell["column_id"]] = new_value
        return data.traval.traval_result.reset_index().to_dict("records")

    @app.callback(
        Output(ids.DOWNLOAD_EXPORT_CSV, "data"),
        Input(ids.QC_RESULT_EXPORT_CSV, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    def download_export_csv(n_clicks, name):
        timestr = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestr}_qc_result_{name[0]}.csv"
        if data.traval.traval_result is not None:
            return dcc.send_string(data.traval.traval_result.to_csv, filename=filename)

    @app.callback(
        Output(ids.DOWNLOAD_EXPORT_DB, "data"),  # what do i need to use as output?
        Input(ids.QC_RESULT_EXPORT_DB, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    def export_to_db(n_clicks, name):
        if data.traval.traval_result is not None:
            df = data.traval.traval_result
            mask = df["manual_check"] = 1
            df.loc[mask, "qualifier_by_category"] = "goedgekeurd"
            mask = df["manual_check"] = 0
            df.loc[mask, "qualifier_by_category"] = "afgekeurd"
            data.save_qualifier(df)
            return None  # ??

    @app.callback(
        Output(ids.QC_RESULT_TABLE, "filter_query"),
        Input(ids.QC_RESULTS_SHOW_ALL_OBS_SWITCH, "value"),
        State(ids.QC_RESULT_TABLE, "filter_query"),
        prevent_initial_call=True,
    )
    def show_all_observations(value, query):
        if value and (query != ""):
            return ""
        elif not value and (query == ""):
            return '{comment} != ""'
        else:
            # some query is active, try keeping it active but also filtering on comments
            if "{comment}" not in query:
                if value:
                    return query
                else:
                    return query + ' && {comment} != ""'  # add comment query
            else:
                if value:
                    return ""  # can't remove only comment query so remove all filters
                else:
                    return query  # return current active query

    @app.callback(
        Output(ids.QC_RESULT_TABLE, "data", allow_duplicate=True),
        Output(ids.RESULT_TABLE_SELECTION, "data", allow_duplicate=True),
        Input(ids.QC_RESULT_CHART, "selectedData"),
        State(ids.RESULT_TABLE_SELECTION, "data"),
        prevent_initial_call=True,
    )
    def filter_table_from_result_chart(selected_data, table_selection):
        if table_selection:
            return no_update, False
        if selected_data is not None and len(selected_data) > 0:
            ic(selected_data)
            pts = pd.DataFrame(selected_data["points"])
            t = pts["x"].unique()
            return (
                data.traval.traval_result.loc[t].reset_index().to_dict("records"),
                False,
            )
        elif data.traval.traval_result is not None:
            return data.traval.traval_result.reset_index().to_dict("records"), False
        else:
            return no_update, False

    @app.callback(
        Output(ids.QC_RESULT_CHART, "selectedData"),
        Output(ids.QC_RESULT_CHART, "figure", allow_duplicate=True),
        Output(ids.RESULT_TABLE_SELECTION, "data", allow_duplicate=True),
        Input(ids.QC_RESULT_TABLE, "selected_cells"),
        prevent_initial_call=True,
    )
    def select_points_in_chart_from_table(selected_cells):
        if selected_cells is not None:
            selected_row_ids = [c["row_id"] for c in selected_cells]
            series = data.traval.traval_result

            selectedData = {
                "points": [
                    {
                        "curveNumber": 2,  # TODO: if no pastas model, the original series is trace 0
                        "pointNumber": series["id"].iloc[i],
                        "pointIndex": series["id"].iloc[i],
                        "x": series.index[i],
                        "y": series["values"].iloc[i],
                    }
                    for i in selected_row_ids
                ]
            }
            ptspatch = Patch()
            # TODO: if no pastas model, the original series is trace 0
            ptspatch["data"][2]["selectedpoints"] = selected_row_ids
            active_selection = True
        else:
            selectedData = {}
            active_selection = False
            # ptspatch = Patch()
            # # TODO: if no pastas model, the original series is trace 0
            # ptspatch["data"][2]["selectedpoints"] = []
            ptspatch = no_update
        return selectedData, ptspatch, active_selection
