import dash_bootstrap_components as dbc
from dash import dcc

from . import ids, overview_chart, overview_map, overview_table
from ..data.source import DataSource
from ..cache import cache, TIMEOUT


def render():
    return dcc.Tab(
        label="Overview",
        value=ids.TAB_OVERVIEW,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


@cache.memoize(timeout=TIMEOUT)
def render_content(data: DataSource):
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            overview_map.render(data),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            overview_table.render(data),
                        ],
                        width=6,
                    ),
                ],
                style={"height": "45vh"},
            ),
            dbc.Row(
                [
                    overview_chart.render(),
                ],
            ),
        ],
        fluid=True,
    )
