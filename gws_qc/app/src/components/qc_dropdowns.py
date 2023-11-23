from dash import html, dcc, Dash

from . import ids
from ..data.source import DataSource


def render_selection_series_dropdown(data: DataSource):
    locs = data.list_locations()
    locs = [f"{iloc[0]}-{iloc[1]:03g}" for iloc in locs]
    options = [{"label": i, "value": i} for i in locs]

    return html.Div(
        children=[
            dcc.Dropdown(
                options=options,
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
