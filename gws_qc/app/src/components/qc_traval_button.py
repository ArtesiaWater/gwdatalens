from dash import html
from dash_bootstrap_components import Button

from . import ids


def render():
    return html.Div(
        Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-gear"),  # , style={"color: #006f92"}
                    " Run TRAVAL",
                ],
                id="span-recalculate",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
            },
            disabled=False,
            id=ids.QC_TRAVAL_BUTTON,
        ),
    )
