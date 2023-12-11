from dash import html, dcc

from . import ids


def render(data, selected_data):
    locs = data.list_locations()
    locs = [f"{iloc[0]}-{iloc[1]:03g}" for iloc in locs]
    options = [{"label": i, "value": i} for i in locs]

    if selected_data is not None and len(selected_data) == 1:
        value = selected_data[0]
    else:
        value = None

    return html.Div(
        [
            dcc.Dropdown(
                id=ids.MODEL_DROPDOWN_SELECTION,
                clearable=True,
                placeholder="Select a location",
                value=value,
                multi=False,
                searchable=True,
                disabled=False,
                options=options,
            )
        ]
    )
