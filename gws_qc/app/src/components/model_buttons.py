from dash import html
from dash_bootstrap_components import Button

from . import ids


def render_generate_button():
    return html.Div(
        Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-gear"),  # , style={"color: #006f92"}
                    " Generate model",
                ],
                id="span-recalculate",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
            },
            disabled=False,
            id=ids.MODEL_GENERATE_BUTTON,
        ),
    )


def render_save_button():
    return html.Div(
        Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-gear"),  # , style={"color: #006f92"}
                    " Save model",
                ],
                id="span-recalculate",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
            },
            disabled=True,
            id=ids.MODEL_SAVE_BUTTON,
        ),
    )
