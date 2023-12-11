from dash import Dash, html, dcc

from ..data.source import DataSource
from . import button_help_modal, ids, tabs, alert


def create_layout(app: Dash, data: DataSource) -> html.Div:
    """Create app layout.

    Parameters
    ----------
    app : Dash
        dash app object
    data : DataSource
        data class

    Returns
    -------
    html.Div
        html containing app layout.
    """
    return html.Div(
        id="main",
        children=[
            dcc.Store(id=ids.SELECTED_OSERIES_STORE),
            dcc.Store(ids.PASTAS_MODEL_STORE),
            html.Div(
                id="header",
                children=[
                    html.H1(app.title, id="app_title"),
                    alert.render(),
                    button_help_modal.render(),
                ],
            ),
            tabs.render(),
            html.Div(id=ids.TAB_CONTENT),
        ],
    )
