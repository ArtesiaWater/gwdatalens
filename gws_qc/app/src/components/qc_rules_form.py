from inspect import signature

import dash_bootstrap_components as dbc
import numpy as np
from dash import dash_table, html
from dash.dash_table.Format import Format

from ..data.source import DataSource
from . import ids
from .styling import DATA_TABLE_HEADER_BGCOLOR


def generate_kwargs_from_func(func):
    sig = signature(func)
    kwargs = {}
    for k, v in sig.parameters.items():
        if v.default != v.empty:
            kwargs[k] = v.default
    return kwargs


def generate_traval_rule_components(rule, rule_number):
    name = rule["name"]
    ibtn = dbc.Button(
        html.Span(
            [html.I(className="fa-solid fa-x")],
            n_clicks=0,
        ),
        id={"type": "clear-button", "index": f"{name}-{rule_number}"},
        size="sm",
        style={
            "background-color": "darkred",
            "fontSize": "small",
            # "padding": 1,
            "height": "30px",
            "width": "30px",
        },
    )
    lbl = dbc.Label(name, width=1)
    row_components = [ibtn, lbl]
    idx = rule_number  # input_field_no
    for k, v in rule["kwargs"].items():
        disabled = False
        step = None
        if isinstance(v, tuple) and callable(v[0]):
            input_type = "text"
            v = str(v)
            disabled = True
        elif callable(v):
            v = str(v)
            disabled = True
            input_type = "text"
        elif isinstance(v, float):
            input_type = "number"
            # step = np.min([10 ** np.floor(np.log10(v)) / 2, 10])
            vstr = str(v % 1)
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

        ilbl = dbc.Label(k, width=1)
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

    irow = dbc.Row(
        row_components,
        className="g-3",
        id={"type": "rule_row", "index": f"{name}-{rule_number}"},
    )
    return irow


def render_rules_table(data):
    rule_table = data.ruleset.to_dataframe().loc[:, ["name", "apply_to", "kwargs"]]
    rule_table = rule_table.reset_index().astype(str)

    return html.Div(
        id="qc-rules-div",
        children=[
            dash_table.DataTable(
                id=ids.QC_RULES_TABLE,
                data=rule_table.to_dict("records"),
                columns=[
                    {
                        "id": "step",
                        "name": "Step",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=1),
                        "editable": False,
                    },
                    {
                        "id": "name",
                        "name": "Rule",
                        "type": "text",
                        "editable": False,
                    },
                    {
                        "id": "apply_to",
                        "name": "Apply to",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=1),
                        "editable": True,
                    },
                    #     {
                    #         "id": "kwargs",
                    #         "name": "Parameters",
                    #         "type": "text",
                    #         "editable": True,
                    #     },
                ],
                editable=False,
                fixed_rows={"headers": True},
                page_action="none",
                # style_table={
                #     # "height": "70vh",
                #     # "overflowY": "auto",
                #     # "margin-top": 15,
                #     # "maxHeight": "70vh",
                # },
                row_selectable="multi",
                style_cell={"whiteSpace": "pre-line", "fontSize": 12},
                style_cell_conditional=[
                    {"if": {"column_id": "step"}, "width": "20%"},
                    {"if": {"column_id": "name"}, "width": "40%"},
                    {"if": {"column_id": "apply_to"}, "width": "40%"},
                    # {"if": {"column_id": "kwargs"}, "width": "75%"},
                ]
                + [
                    {
                        "if": {"column_id": c},
                        "textAlign": "left",
                    }
                    for c in ["name", "kwargs"]
                ],
                # style_data_conditional=style_data_conditional,
                style_header={
                    "backgroundColor": DATA_TABLE_HEADER_BGCOLOR,
                    "fontWeight": "bold",
                },
            ),
        ],
        className="dbc dbc-row-selectable",
    )


def render_traval_form(data: DataSource):
    form_components = []
    nrules = len(data.ruleset.rules) - 1

    idx = 0
    for i in range(1, nrules + 1):
        irule = data.ruleset.get_rule(istep=i)
        irow = generate_traval_rule_components(irule, idx)
        form_components.append(irow)
        idx += 1

    form = dbc.Form(id=ids.TRAVAL_RULES_FORM, children=form_components)
    return form
