from typing import List, Optional
from dash import html, dcc

from . import ids
from ..data.source import DataSource


def render_selection_series_dropdown(data: DataSource, selected_data: Optional[List]):
    locs = data.list_locations()
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


def render_additional_series_dropdown(data: DataSource):
    locs = data.list_locations()
    locs = [f"{iloc[0]}-{iloc[1]:03g}" for iloc in locs]
    options = [{"label": i, "value": i} for i in locs]
    return html.Div(
        children=[
            dcc.Dropdown(
                options=options,
                clearable=True,
                searchable=True,
                placeholder="Select additional time series to plot...",
                id=ids.QC_DROPDOWN_ADDITIONAL,
                disabled=True,
                multi=True,
            )
        ]
    )
