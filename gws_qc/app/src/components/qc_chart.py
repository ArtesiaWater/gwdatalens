from dash import dcc, html
from datalens.app.settings import settings

from ..cache import TIMEOUT, cache
from . import ids
from .utils import conditional_cache


@conditional_cache(cache.memoize, not settings["DJANGO_APP"], timeout=TIMEOUT)
def render():
    return html.Div(
        id="series-chart-div",
        children=[
            dcc.Loading(
                id=ids.LOADING_QC_CHART,
                type="dot",
                style={"position": "absolute", "align-self": "center"},
                parent_className="loading-wrapper",
                # delay_show=100,
                children=[
                    dcc.Graph(
                        id=ids.QC_CHART,
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                        },
                        style={
                            "height": "40vh",
                            # "margin-bottom": "10px",
                            # "margin-top": 5,
                        },
                    ),
                ],
            ),
        ],
        style={
            "position": "relative",
            "justify-content": "center",
            "margin-bottom": 10,
        },
    )
