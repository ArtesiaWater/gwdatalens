import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from . import ids, tabs


def create_layout(app: Dash) -> html.Div:
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
            tabs.render(app),
            html.Div(id=ids.TAB_CONTENT),
        ],
    )


# %%
# html.Div(
#                 id="div-body",
#                 children=[
#                     dbc.Container(
#                         [
#                             dbc.Row(
#                                 children=[
#                                     # Column 1:
#                                     dbc.Col(
#                                         children=[
#                                         ],
#                                         width=2,
#                                     ),
#                                     # Column 2:
#                                     dbc.Col(
#                                         children=[
#                                         ],
#                                         width=5,
#                                     ),
#                                     # Column 3:
#                                     dbc.Col(
#                                         children=[
#                                         ],
#                                         width=5,
#                                     ),
#                                 ]
#                             )
#                         ],
#                         fluid=True,
#                     ),
#                 ],
#             )
