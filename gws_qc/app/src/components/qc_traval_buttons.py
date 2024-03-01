from dash import html, dcc
from dash_bootstrap_components import Button

from . import ids


def render_run_traval_button():
    return html.Div(
        Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-gear"),
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
            id=ids.QC_RUN_TRAVAL_BUTTON,
        ),
    )


def render_add_rule_button():
    return html.Div(
        Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-plus"),
                    " Add rule",
                ],
                id="span-add-rule",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
            },
            disabled=True,
            id=ids.TRAVAL_ADD_RULE_BUTTON,
        ),
    )


def render_load_ruleset_button():
    return html.Div(
        children=[
            # NOTE: Upload component does not trigger callback if same file is selected.
            # Solution (i.e. workaround) is to create a new Upload component once it's
            # been used.
            dcc.Upload(
                id=ids.TRAVAL_LOAD_RULESET_BUTTON,
                # accept=[
                #     ".pickle",
                #     ".pkl",
                # ],  # Only works in production mode, not in debug mode
                children=[
                    html.A(
                        html.Span(
                            [
                                html.I(className="fa-solid fa-file-import"),
                                "  Load RuleSet ",
                            ],
                            style={
                                "color": "white",
                            },
                        )
                    )
                ],
                style={
                    "width": "110px",
                    "height": "33px",
                    "lineHeight": "31.5px",
                    "borderWidth": "1px",
                    "borderStyle": "solid",
                    "borderRadius": "3px",
                    "backgroundClip": "border-box",
                    "backgroundColor": "#2c3e50",  # "#006f92",
                    "textAlign": "center",
                },
            )
        ],
        style={
            "display": "inline-block",
            "margin-top": 5,
            "margin-bottom": 10,
            "margin-right": 5,
            "verticalAlign": "middle",
        },
    )
