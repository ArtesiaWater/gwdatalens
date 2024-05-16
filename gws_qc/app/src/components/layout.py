from dash import Dash, dcc, html

from ..data.source import DataInterface
from . import button_help_modal, ids, tabs


def create_layout(app: Dash, data: DataInterface) -> html.Div:
    """Create app layout.

    Parameters
    ----------
    app : Dash
        dash app object
    data : DataInterface
        data class

    Returns
    -------
    html.Div
        html containing app layout.
    """
    return html.Div(
        id="main",
        children=[
            dcc.Store(id=ids.SELECTED_OSERIES_STORE),
            dcc.Store(id=ids.PASTAS_MODEL_STORE),
            dcc.Store(id=ids.OVERVIEW_TABLE_SELECTION),
            dcc.Store(id=ids.ACTIVE_TABLE_SELECTION_STORE),
            dcc.Store(id=ids.TRAVAL_RULESET_STORE),
            dcc.Store(id=ids.TRAVAL_RESULT_FIGURE_STORE),
            dcc.Store(id=ids.TRAVAL_RESULT_TABLE_STORE),
            dcc.Store(id=ids.SELECTED_OBS_STORE),
            # alert containers
            dcc.Store(id=ids.ALERT_TIME_SERIES_CHART),
            dcc.Store(id=ids.ALERT_DISPLAY_RULES_FOR_SERIES),
            dcc.Store(id=ids.ALERT_GENERATE_MODEL),
            dcc.Store(id=ids.ALERT_SAVE_MODEL),
            dcc.Store(id=ids.ALERT_PLOT_MODEL_RESULTS),
            dcc.Store(id=ids.ALERT_EXPORT_TO_DB),
            dcc.Store(id=ids.ALERT_MARK_OBS),
            dcc.Store(id=ids.ALERT_LOAD_RULESET),
            # header + tabs
            html.Div(
                id="header",
                children=[
                    html.H1(app.title, id="app_title"),
                    html.Div(id=ids.ALERT_DIV),
                    # alert.render(),
                    button_help_modal.render(),
                ],
            ),
            tabs.render(),
            html.Div(id=ids.TAB_CONTENT),
        ],
    )
