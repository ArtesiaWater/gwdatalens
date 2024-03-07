import dash_bootstrap_components as dbc
from dash import dcc
import i18n

from ..cache import TIMEOUT, cache
from ..data.source import DataInterface
from . import ids, overview_chart, overview_map, overview_table


def render():
    return dcc.Tab(
        label=i18n.t("general.tab_overview"),
        value=ids.TAB_OVERVIEW,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


@cache.memoize(timeout=TIMEOUT)
def render_content(data: DataInterface, selected_data: str):
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            overview_map.render(data, selected_data),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            overview_table.render(data, selected_data),
                        ],
                        width=6,
                    ),
                ],
                style={"height": "45vh"},
            ),
            dbc.Row(
                [
                    overview_chart.render(data, selected_data),
                ],
            ),
        ],
        fluid=True,
    )
