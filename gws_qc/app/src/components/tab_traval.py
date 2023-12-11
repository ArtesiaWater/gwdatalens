import dash_bootstrap_components as dbc
import numpy as np
from dash import dcc, html

from ..data.source import DataSource
from . import ids


def render():
    return dcc.Tab(
        label="QC Rules",
        value=ids.TAB_TRAVAL,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_content(data: DataSource):
    # data.ruleset.get_rule()
    form_components = []
    nrules = len(data.ruleset.rules) - 1
    idx = 0
    for i in range(1, nrules + 1):
        row_components = []
        irule = data.ruleset.get_rule(istep=i)
        name = irule["name"]

        lbl = dbc.Label(name, width=1)
        row_components.append(lbl)

        for k, v in irule["kwargs"].items():
            disabled = False
            if isinstance(v, tuple) and callable(v[0]):
                input_type = "text"
                v = str(v)
                disabled = True
            elif callable(v):
                v = str(v)
                disabled = True
            elif isinstance(v, float):
                input_type = "number"
                # step = np.min([10 ** np.floor(np.log10(v)) / 2, 10])
                vstr = str(0.01 % 1)
                ndecimals = len(vstr) - vstr.find(".") - 1
                step = 10 ** (-ndecimals) / 2
            elif isinstance(v, (int, np.integer)):
                input_type = "number"
                step = int(np.min([10 ** np.floor(np.log10(v)), 10]))
                if isinstance(v, bool):
                    v = int(v)
            else:
                input_type = "text"
                step = "any"

            ilbl = dbc.Label(k, width="auto")
            param = dbc.Col(
                dbc.Input(
                    id={"type": "rule_input", "index": f"{idx}-{name}-{k}"},
                    step=step,
                    type=input_type,
                    placeholder=str(type(v).__name__),
                    value=v,
                    disabled=disabled,
                    size="sm",
                ),
                className="me-3",
                width=1,
            )
            row_components += [ilbl, param]
            idx += 1
        ibtn = dbc.Button(
            html.Span(
                [html.I(className="fa-solid fa-x")],
                n_clicks=0,
            ),
            id=f"clear-button-{name}",
            style={
                "background-color": "#006f92",
                # "margin-left": "auto",
                "fontSize": "small",
                "width": "auto",
            },
        )
        row_components.append(ibtn)
        irow = dbc.Row(row_components, className="g-3")
        form_components.append(irow)
    form = dbc.Form(form_components)

    return dbc.Container(
        [
            form,
            html.Pre(id=ids.TRAVAL_OUTPUT, lang="JSON", style={"fontSize": 8}),
        ],
        fluid=True,
    )
