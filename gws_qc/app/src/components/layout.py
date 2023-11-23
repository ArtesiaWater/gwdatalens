import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from . import ids, tabs
from ..data.source import DataSource


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
            html.Div(
                id="header",
                children=[
                    html.H1(app.title, id="app_title"),
                    # button_help_modal.render(app),
                ],
            ),
            tabs.render(),
            html.Div(id=ids.TAB_CONTENT),
        ],
    )
