from typing import List, Optional

from dash import dcc, html
from traval import rulelib

from ..data.source import DataInterface
from . import ids


def render_selection_series_dropdown(data: DataInterface, selected_data: Optional[List]):
    locs = data.db.list_locations()
    locs = [f"{iloc[0]}-{iloc[1]:03g}" for iloc in locs]
    options = [{"label": i, "value": i} for i in locs]

    if selected_data is not None and len(selected_data) == 1:
        value = selected_data[0]
    else:
        value = None

    return html.Div(
        children=[
            dcc.Dropdown(
                options=options,
                value=value,
                clearable=True,
                searchable=True,
                placeholder="Select time series ...",
                id=ids.QC_DROPDOWN_SELECTION,
                disabled=False,
            )
        ]
    )


def render_additional_series_dropdown(data: DataInterface):
    locs = data.db.list_locations()
    locs = [f"{iloc[0]}-{iloc[1]:03g}" for iloc in locs]
    options = [{"label": i, "value": i} for i in locs]
    return html.Div(
        children=[
            dcc.Dropdown(
                options=options,
                clearable=True,
                searchable=True,
                placeholder="Select additional time series to plot ...",
                id=ids.QC_DROPDOWN_ADDITIONAL,
                disabled=True,
                multi=True,
            )
        ]
    )


def render_add_rule_dropdown():
    options = [
        {"value": i, "label": i}
        for i in [rule for rule in dir(rulelib) if rule.startswith("rule_")]
    ]

    return html.Div(
        [
            dcc.Dropdown(
                id=ids.TRAVAL_ADD_RULE_DROPDOWN,
                clearable=True,
                placeholder="Select a rule to add",
                value=None,
                multi=False,
                searchable=True,
                disabled=False,
                options=options,
            )
        ]
    )
