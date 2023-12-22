import dash_bootstrap_components as dbc
from dash import dcc

from ..data.source import DataSource
from . import ids, qc_results_table


def render():
    return dcc.Tab(
        label="QC Result",
        value=ids.TAB_QC_RESULT,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_content(data: DataSource):
    return dbc.Container(
        [
            qc_results_table.render(data),
        ]
    )
