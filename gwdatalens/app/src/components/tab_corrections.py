from typing import List

import dash_bootstrap_components as dbc
import i18n
import pandas as pd
import plotly.graph_objects as go
from dash import __version__ as DASH_VERSION
from dash import dash_table, dcc, html
from packaging.version import parse as parse_version

from ..data.interface import DataInterface
from . import ids
from .overview_chart import plot_obs
from .styling import DATA_TABLE_HEADER_BGCOLOR


def render():
    """Renders the Model Tab.

    Returns
    -------
    dcc.Tab
        The model tab
    """
    return dcc.Tab(
        label=i18n.t("general.tab_corrections"),
        value=ids.TAB_CORRECTIONS,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_content(data: DataInterface, selected_data: List):
    """Renders the content for the model tab.

    Parameters
    ----------
    data : DataInterface
        The data interface containing the necessary data for rendering.
    selected_data : List
        A list of selected data items.

    Returns
    -------
    dbc.Container
        A Dash Bootstrap Container with the rendered content.
    """
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [render_corrections_dropdown(data, selected_data)], width=4
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col([render_well_configuration(data, selected_data)], width=2),
                    dbc.Col([render_tube_table(data, selected_data)], width=3),
                    dbc.Col([render_chart(data, selected_data)], width=7),
                ],
                style={"height": "35vh"},
            ),
            html.Hr(style={"margin": "20px 0"}),
            # dbc.Row(
            #     [
            #         dbc.Col(
            #             [
            #                 html.H5(
            #                     i18n.t("general.observation_comparison"),
            #                     style={"margin-bottom": "15px"},
            #                 )
            #             ],
            #             width=12,
            #         ),
            #     ]
            # ),
            dbc.Row(
                [
                    dbc.Col([render_well_selection(data, selected_data)], width=12),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col([render_observations_table(data, selected_data)], width=12),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col([render_correction_controls()], width=12),
                ]
            ),
            # Data stores for state management
            dcc.Store(id=ids.CORRECTIONS_ORIGINAL_DATA_STORE),
            dcc.Store(id=ids.CORRECTIONS_EDIT_HISTORY_STORE),
            dcc.Store(id=ids.CORRECTIONS_COMMIT_TRIGGER_STORE),
            dcc.Store(id=ids.CORRECTIONS_RESET_TRIGGER_STORE),
        ],
        fluid=True,
    )


def render_tube_table(data, selected_data):
    """Renders a table displaying tube information for the selected location.

    Parameters
    ----------
    data : object
        An object that contains a database connection with methods to list
        locations and access location data.
    selected_data : list or None
        A list containing the currently selected location(s). If None or the list
        is empty, no location is pre-selected.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing a table of tube information.
    """
    usecols = [
        "display_name",
        "tube_top_position",
        "ground_level_position",
        "screen_top",
        "screen_bot",
    ]
    if selected_data is not None and len(selected_data) == 1:
        names = data.db.get_tube_numbers(selected_data[0])
        df = data.db.query_gdf(display_name=names, operator="in", columns=usecols)
    else:
        df = pd.DataFrame(index=None, columns=usecols)

    return html.Div(
        id="table-div",
        children=[
            dash_table.DataTable(
                id=ids.CORRECTIONS_TUBE_TABLE,
                data=df.to_dict("records"),
                columns=[
                    {
                        "id": "display_name",
                        "name": "Naam",
                        "type": "text",
                    },
                    {
                        "id": "tube_top_position",
                        "name": "BKB\n[m NAP]",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "id": "ground_level_position",
                        "name": "MV\n[m NAP]",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "id": "screen_top",
                        "name": "BKF\n[m NAP]",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "id": "screen_bot",
                        "name": "OKF\n[m NAP]",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                ],
                fixed_rows={"headers": True},
                page_action="none",
                sort_action="native",
                style_table={"margin-top": 30},
                style_cell={"whiteSpace": "pre-line", "fontSize": 12},
                style_cell_conditional=[
                    {
                        "if": {"column_id": c},
                        "textAlign": "left",
                    }
                    for c in ["display_name"]
                ]
                + [
                    {"if": {"column_id": "display_name"}, "width": "30%"},
                    {"if": {"column_id": "tube_top_position"}, "width": "17.5%"},
                    {"if": {"column_id": "ground_level_position"}, "width": "17.5%"},
                    {"if": {"column_id": "screen_top"}, "width": "17.5%"},
                    {"if": {"column_id": "screen_bot"}, "width": "17.5%"},
                ],
                style_data_conditional=[
                    {
                        "if": {"state": "selected"},  # 'active' | 'selected'
                        "border": "1px solid #006f92",
                    },
                ],
                style_header={
                    "backgroundColor": DATA_TABLE_HEADER_BGCOLOR,
                    "fontWeight": "bold",
                },
            ),
        ],
        className="dbc dbc-row-selectable",
    )


def render_corrections_dropdown(data, selected_data):
    """Renders a dropdown component for selecting a time series.

    Parameters
    ----------
    data : object
        An object that contains a database connection with methods to list
        locations and access location data.
    selected_data : list or None
        A list containing the currently selected location(s). If None or the list
        is empty, no location is pre-selected.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing a Dropdown for selecting a location.
    """
    locs = data.db.list_locations()

    options = []
    for _, row in locs.iterrows():
        label_text = f"{row['location_name']}: {row['ntubes']} tube(s)"
        if row["hasdata"]:
            # Normal styling for locations with data
            label = label_text
        else:
            # Grey and italic for locations without data
            label = html.Span(
                label_text + " (no data)",
                style={"color": "#999", "font-style": "italic"},
            )

        options.append(
            {"label": label, "value": row["id"], "search": row["location_name"]}
        )

    if selected_data is not None and len(selected_data) == 1:
        value = selected_data[0]
    else:
        value = None

    return html.Div(
        [
            dcc.Dropdown(
                id=ids.CORRECTIONS_DROPDOWN_SELECTOR,
                clearable=True,
                placeholder=i18n.t("general.select_location"),
                value=value,
                multi=False,
                searchable=True,
                disabled=False,
                options=options,
            )
        ]
    )


def render_chart(data, selected_data):
    kwargs = (
        {"delay_show": 500}
        if parse_version(DASH_VERSION) >= parse_version("2.17.0")
        else {}
    )

    if selected_data is not None:
        if len(selected_data) > 1:
            wids = None
        else:
            # get ids for all tubes in the selected well
            names = data.db.get_tube_numbers(selected_data[0])
            wids = (
                data.db.query_gdf(display_name=names, operator="in", columns=["id"])
                .squeeze(axis="columns")
                .tolist()
            )
    else:
        wids = None

    return html.Div(
        id="series-chart-div",
        children=[
            dcc.Loading(
                id=ids.LOADING_CORRECTION_SERIES_CHART,
                type="dot",
                style={"position": "absolute", "align-self": "center"},
                parent_className="loading-wrapper",
                children=[
                    dcc.Graph(
                        figure=plot_obs(wids, data, plot_manual_obs=True),
                        id=ids.CORRECTION_SERIES_CHART,
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                        },
                        style={
                            "height": "35vh",
                            "margin-top": 5,
                            "margin-left": 5,
                            "margin-right": 5,
                            # "margin-bottom": "10px",
                        },
                    ),
                ],
                **kwargs,
            ),
        ],
        style={
            "position": "relative",
            "justify-content": "center",
            "margin-bottom": 10,
        },
    )


def render_well_configuration(data, selected_data):
    usecols = [
        "tube_top_position",
        "ground_level_position",
        "screen_top",
        "screen_bot",
        "display_name",
    ]
    if selected_data is not None and len(selected_data) == 1:
        names = data.db.get_tube_numbers(selected_data[0])
        df = data.db.query_gdf(display_name=names, operator="in", columns=usecols)
        df = df.set_index("display_name")
    else:
        df = pd.DataFrame(index=None, columns=usecols)

    return html.Div(
        children=[
            dcc.Loading(
                id=ids.LOADING_WELL_CONFIGURATION_PLOT,
                type="dot",
                style={"position": "absolute", "align-self": "center"},
                parent_className="loading-wrapper",
                children=[
                    dcc.Graph(
                        figure=plot_well_cross_section(df),
                        id=ids.WELL_CONFIGURATION_PLOT,
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                        },
                        style={
                            "height": "35vh",
                            # "margin-bottom": "10px",
                            # "margin-top": 5,
                        },
                    ),
                ],
                # **kwargs,
            )
        ]
    )


def plot_well_cross_section(df, tube_width=0.15):
    """
    Plot cross-section of observation wells showing tube positions and screen intervals.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing well data with columns:
        - tube_top_position: elevation of tube top (m)
        - ground_level_position: ground surface elevation (m)
        - screen_top: top of screen interval (m)
        - screen_bot: bottom of screen interval (m)
        Index should contain tube identifiers/numbers
    tube_width : float, optional
        Width of the tube representation (default: 0.15)

    Returns
    -------
    fig : plotly.graph_objects.Figure
        Plotly figure object
    """
    if df.empty:
        return {"layout": {"title": {"text": i18n.t("general.no_well_data")}}}

    fig = go.Figure()

    # Sort by ground level position for better visualization
    df_sorted = df.sort_values("ground_level_position", ascending=False)

    # Create x-positions for each well
    x_positions = list(range(len(df_sorted)))
    df_sorted.index.tolist()

    # Determine plot bounds
    min_elevation = df_sorted[["screen_bot", "ground_level_position"]].min().min()
    max_elevation = df_sorted["tube_top_position"].max()
    ground_level = df_sorted["ground_level_position"].iloc[
        0
    ]  # Assuming same ground level

    # Add subsurface shading (sand layer below ground level)
    fig.add_trace(
        go.Scatter(
            x=[-0.5, len(df_sorted) - 0.5, len(df_sorted) - 0.5, -0.5, -0.5],
            y=[
                ground_level,
                ground_level,
                min_elevation - 5,
                min_elevation - 5,
                ground_level,
            ],
            fill="toself",
            fillcolor="rgba(245, 222, 179, 0.4)",  # Light yellow/wheat color for sand
            line={"width": 0},
            mode="lines",
            showlegend=False,
            name="Subsurface (sand)",
            hoverinfo="skip",
        )
    )

    # Add ground level line
    fig.add_trace(
        go.Scatter(
            x=[-0.5, len(df_sorted) - 0.5],
            y=[ground_level, ground_level],
            mode="lines",
            line={"color": "green", "width": 3},
            showlegend=True,
            name="Ground level",
            hovertemplate=f"Ground level: {ground_level:.2f} m<extra></extra>",
        )
    )

    for i, (tube_name, row) in enumerate(df_sorted.iterrows()):
        x_pos = x_positions[i]
        half_width = tube_width / 2

        # Solid rectangle from tube top to screen top (tube casing)
        x_tube = [
            x_pos - half_width,
            x_pos + half_width,
            x_pos + half_width,
            x_pos - half_width,
            x_pos - half_width,
        ]
        y_tube = [
            row["tube_top_position"],
            row["tube_top_position"],
            row["screen_top"],
            row["screen_top"],
            row["tube_top_position"],
        ]

        fig.add_trace(
            go.Scatter(
                x=x_tube,
                y=y_tube,
                fill="toself",
                fillcolor="rgba(0, 0, 0, 0.3)",  #'rgba(70, 130, 180, 0.7)',# Steel blue
                line={"color": "black", "width": 2},
                mode="lines",
                showlegend=False,
                hoveron="fills+points",  # enable hover on the filled area
                name="Tube casing",  # avoid "trace n" fallback
                hovertemplate=(
                    f"{tube_name}<br>Top: NAP{row['tube_top_position']:+.2f} "
                    "m<extra></extra>"
                ),
            )
        )
        # Add invisible hover point at center
        fig.add_trace(
            go.Scatter(
                x=[x_pos],
                y=[(row["tube_top_position"] + row["screen_top"]) / 2],
                # line=dict(color="black", width=2),
                mode="markers",
                marker={"size": 15, "opacity": 0, "color": "black"},  # invisible
                showlegend=False,
                hovertemplate=(
                    f"{tube_name}<br>Top: NAP{row['tube_top_position']:+.2f} "
                    "m<extra></extra>"
                ),
            )
        )

        # Dashed rectangle from screen top to screen bottom (screen interval)
        x_screen = [
            x_pos - half_width,
            x_pos + half_width,
            x_pos + half_width,
            x_pos - half_width,
            x_pos - half_width,
        ]
        y_screen = [
            row["screen_top"],
            row["screen_top"],
            row["screen_bot"],
            row["screen_bot"],
            row["screen_top"],
        ]

        fig.add_trace(
            go.Scatter(
                x=x_screen,
                y=y_screen,
                fill="toself",
                fillcolor="rgba(255, 99, 71, 0.3)",  # Light red/tomato
                line={"color": "red", "width": 2, "dash": "2px,2px"},
                mode="lines",
                showlegend=False,
                hoveron="fills+points",  # enable hover on the filled area
                name="Screen interval",  # avoid "trace n" fallback
                hovertemplate=(
                    f"{tube_name}<br>Top: NAP{row['screen_top']:+.2f} m<br>Bottom: "
                    f"NAP{row['screen_bot']:+.2f} m<extra></extra>"
                ),
            )
        )

        # Add tube label at the top
        fig.add_annotation(
            x=x_pos,
            y=row["tube_top_position"],
            text=tube_name.split("-")[-1],  # Show only the tube number
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor="black",
            ax=0,
            ay=-30,
            font={"size": 10, "color": "black"},
        )

    # Add legend entries for tube types
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            fill="toself",
            fillcolor="rgba(0, 0, 0, 0.3)",
            line={"color": "black", "width": 2},
            name="Tube casing",
            hoverinfo="skip",  # Skip hover for legend entry
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            fill="toself",
            fillcolor="rgba(255, 99, 71, 0.3)",
            line={"color": "red", "width": 2, "dash": "2px,2px"},
            name="Screen interval",
            hoverinfo="skip",  # Skip hover for legend entry
        )
    )

    # Update layout
    fig.update_layout(
        # title=df.index[0].split("-")[0],
        title_x=0.5,  # Center align the title
        xaxis={
            # title='Tube Number',
            # tickmode='array',
            # tickvals=x_positions,
            # ticktext=[name.split('-')[-1] for name in tube_names],  # Show only tubeno
            "range": [-0.5, len(df_sorted) - 0.5],
            "showticklabels": False,  # Hide x-axis tick labels
        },
        yaxis={
            "title": "Elevation (m NAP)",
            # autorange=True
            "range": [min_elevation - 5, max_elevation + 2],
        },
        hovermode="closest",
        # height=600,
        # width=400,
        showlegend=True,
        legend={
            "orientation": "v",  # Changed to vertical
            "yanchor": "bottom",
            "y": 0.025,  # Changed from 1.02 to 0.02
            "xanchor": "left",
            "x": 0.025,  # Changed from 0.5 to 0.02
        },
        template="plotly_white",
        # plot_bgcolor="rgba(240, 248, 255, 0.3)",  # Light blue background
        margin={"l": 5, "r": 0, "t": 50, "b": 20},
    )

    return fig


def render_well_selection(data, selected_data):
    """Renders dropdowns for selecting two observation wells for comparison.

    Parameters
    ----------
    data : DataInterface
        The data interface containing the necessary data.
    selected_data : list or None
        A list containing the currently selected location(s).

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the well selection dropdowns.
    """
    # Get available tubes for the selected location
    if selected_data is not None and len(selected_data) == 1:
        names = data.db.get_tube_numbers(selected_data[0])
        tubes_df = data.db.query_gdf(
            display_name=names, operator="in", columns=["id", "display_name"]
        )
        options = [
            {"label": row["display_name"], "value": row["id"]}
            for _, row in tubes_df.iterrows()
        ]
    else:
        options = []

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label(
                                i18n.t("general.select_well_1"),
                                style={"font-weight": "bold", "margin-bottom": "5px"},
                            ),
                            dcc.Dropdown(
                                id=ids.CORRECTIONS_WELL1_DROPDOWN,
                                options=options,
                                placeholder=i18n.t("general.select_well_1"),
                                clearable=True,
                                searchable=True,
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            html.Label(
                                i18n.t("general.select_well_2"),
                                style={"font-weight": "bold", "margin-bottom": "5px"},
                            ),
                            dcc.Dropdown(
                                id=ids.CORRECTIONS_WELL2_DROPDOWN,
                                options=options,
                                placeholder=i18n.t("general.select_well_2"),
                                clearable=True,
                                searchable=True,
                            ),
                        ],
                        width=5,
                    ),
                    dbc.Col(
                        [
                            html.Label(
                                "\u00a0",  # Non-breaking space for alignment
                                style={"margin-bottom": "5px"},
                            ),
                            dbc.Button(
                                i18n.t("general.clear_selection_button"),
                                id=ids.CORRECTIONS_CLEAR_SELECTION_BUTTON,
                                color="secondary",
                                size="sm",
                                style={"width": "100%"},
                            ),
                        ],
                        width=1,
                    ),
                ],
                style={"margin-bottom": "20px"},
            ),
        ]
    )


def render_observations_table(_data, _selected_data):
    """Renders two side-by-side editable tables for comparing observations from 2 wells.

    Parameters
    ----------
    _data : DataInterface
        The data interface (unused, tables populated by callback).
    _selected_data : list or None
        Selected location (unused, tables populated by callback).

    Returns
    -------
    html.Div
        A Dash HTML Div component containing two side-by-side observation tables.
    """
    kwargs = (
        {"delay_show": 500}
        if parse_version(DASH_VERSION) >= parse_version("2.17.0")
        else {}
    )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dcc.Loading(
                                id=ids.LOADING_CORRECTIONS_TABLE,
                                type="dot",
                                style={"position": "absolute", "align-self": "center"},
                                parent_className="loading-wrapper",
                                children=[
                                    dash_table.DataTable(
                                        id=ids.CORRECTIONS_OBSERVATIONS_TABLE_1,
                                        columns=[
                                            {
                                                "id": "datetime",
                                                "name": "Date/Time",
                                                "type": "datetime",
                                                "editable": False,
                                            },
                                            {
                                                "id": "field_value",
                                                "name": "Field value",
                                                "type": "numeric",
                                                "editable": False,
                                                "format": {"specifier": ".3f"},
                                            },
                                            {
                                                "id": "calculated_value",
                                                "name": i18n.t(
                                                    "general.calculated_value_original"
                                                ),
                                                "type": "numeric",
                                                "editable": False,
                                                "format": {"specifier": ".3f"},
                                            },
                                            {
                                                "id": "corrected_value",
                                                "name": "Corrected value",
                                                "type": "numeric",
                                                "editable": True,
                                                "format": {"specifier": ".3f"},
                                            },
                                            {
                                                "id": "comment",
                                                "name": "Comment",
                                                "type": "text",
                                                "editable": True,
                                            },
                                        ],
                                        data=[],
                                        editable=True,
                                        row_deletable=False,
                                        page_action="none",
                                        style_table={
                                            "height": "27.5vh",
                                            "overflowY": "auto",
                                            "margin-top": 5,
                                        },
                                        style_cell={
                                            "textAlign": "left",
                                            "padding": "4px 8px",
                                            "fontSize": 11,
                                            "whiteSpace": "pre-line",
                                        },
                                        style_cell_conditional=[
                                            {
                                                "if": {"column_id": "datetime"},
                                                "width": "20%",
                                            },
                                            {
                                                "if": {"column_id": "field_value"},
                                                "width": "20%",
                                            },
                                            {
                                                "if": {"column_id": "calculated_value"},
                                                "width": "20%",
                                            },
                                            {
                                                "if": {"column_id": "corrected_value"},
                                                "width": "20%",
                                            },
                                            {
                                                "if": {"column_id": "comment"},
                                                "width": "20%",
                                            },
                                        ],
                                        style_data_conditional=[
                                            {
                                                "if": {"state": "selected"},
                                                "border": "1px solid #006f92",
                                            },
                                        ],
                                        style_header={
                                            "backgroundColor": (
                                                DATA_TABLE_HEADER_BGCOLOR
                                            ),
                                            "fontWeight": "bold",
                                            "padding": "4px 8px",
                                            "fontSize": 11,
                                        },
                                        tooltip_header={
                                            "calculated_value": {
                                                "type": "markdown",
                                                "value": i18n.t(
                                                    "general.calculated_value_original_tooltip"
                                                ),
                                            },
                                            "corrected_value": {
                                                # "use_with": "both",
                                                "type": "markdown",
                                                "value": i18n.t(
                                                    "general.corrected_value_tooltip"
                                                ),
                                            },
                                            "comment": {
                                                # "use_with": "both",
                                                "type": "markdown",
                                                "value": i18n.t(
                                                    "general.correction_reason_tooltip"
                                                ),
                                            },
                                        },
                                    ),
                                ],
                                **kwargs,
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dcc.Loading(
                                id=ids.LOADING_CORRECTIONS_TABLE_2,
                                type="dot",
                                style={"position": "absolute", "align-self": "center"},
                                parent_className="loading-wrapper",
                                children=[
                                    dash_table.DataTable(
                                        id=ids.CORRECTIONS_OBSERVATIONS_TABLE_2,
                                        columns=[
                                            {
                                                "id": "datetime",
                                                "name": "Date/Time",
                                                "type": "datetime",
                                                "editable": False,
                                            },
                                            {
                                                "id": "field_value",
                                                "name": "Field value",
                                                "type": "numeric",
                                                "editable": False,
                                                "format": {"specifier": ".3f"},
                                            },
                                            {
                                                "id": "calculated_value",
                                                "name": i18n.t(
                                                    "general.calculated_value_original"
                                                ),
                                                "type": "numeric",
                                                "editable": False,
                                                "format": {"specifier": ".3f"},
                                            },
                                            {
                                                "id": "corrected_value",
                                                "name": "Corrected value",
                                                "type": "numeric",
                                                "editable": True,
                                                "format": {"specifier": ".3f"},
                                            },
                                            {
                                                "id": "comment",
                                                "name": "Comment",
                                                "type": "text",
                                                "editable": True,
                                            },
                                        ],
                                        data=[],
                                        editable=True,
                                        row_deletable=False,
                                        page_action="none",
                                        style_table={
                                            "height": "27.5vh",
                                            "overflowY": "auto",
                                            "margin-top": 5,
                                        },
                                        style_cell={
                                            "textAlign": "left",
                                            "padding": "4px 8px",
                                            "fontSize": 11,
                                            "whiteSpace": "pre-line",
                                        },
                                        style_cell_conditional=[
                                            {
                                                "if": {"column_id": "datetime"},
                                                "width": "20%",
                                            },
                                            {
                                                "if": {"column_id": "field_value"},
                                                "width": "20%",
                                            },
                                            {
                                                "if": {"column_id": "calculated_value"},
                                                "width": "20%",
                                            },
                                            {
                                                "if": {"column_id": "corrected_value"},
                                                "width": "20%",
                                            },
                                            {
                                                "if": {"column_id": "comment"},
                                                "width": "20%",
                                            },
                                        ],
                                        style_data_conditional=[
                                            {
                                                "if": {"state": "selected"},
                                                "border": "1px solid #006f92",
                                            },
                                        ],
                                        style_header={
                                            "backgroundColor": (
                                                DATA_TABLE_HEADER_BGCOLOR
                                            ),
                                            "fontWeight": "bold",
                                            "padding": "4px 8px",
                                            "fontSize": 11,
                                        },
                                        tooltip_header={
                                            "calculated_value": {
                                                "type": "markdown",
                                                "value": i18n.t(
                                                    "general.calculated_value_original_tooltip"
                                                ),
                                            },
                                            "corrected_value": {
                                                # "use_with": "both",
                                                "type": "markdown",
                                                "value": i18n.t(
                                                    "general.corrected_value_tooltip"
                                                ),
                                            },
                                            "comment": {
                                                # "use_with": "both",
                                                "type": "markdown",
                                                "value": i18n.t(
                                                    "general.correction_reason_tooltip"
                                                ),
                                            },
                                        },
                                    ),
                                ],
                                **kwargs,
                            ),
                        ],
                        width=6,
                    ),
                ],
                style={
                    "position": "relative",
                    "justify-content": "center",
                    "margin-bottom": 20,
                },
            ),
        ]
    )


def render_correction_controls():
    """Renders control buttons and status alert for corrections.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the correction controls.
    """
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                i18n.t("general.commit_corrections"),
                                id=ids.CORRECTIONS_COMMIT_BUTTON,
                                color="primary",
                                disabled=True,
                                style={"margin-right": "10px"},
                            ),
                            dbc.Button(
                                i18n.t("general.reset_changes"),
                                id=ids.CORRECTIONS_RESET_BUTTON,
                                color="primary",
                                disabled=True,
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    dbc.Label(
                                        i18n.t("general.bkb_label"),
                                        html_for=ids.CORRECTIONS_BKB_INPUT,
                                        style={
                                            "font-weight": "bold",
                                            "margin-right": "10px",
                                        },
                                    ),
                                    dbc.Input(
                                        id=ids.CORRECTIONS_BKB_INPUT,
                                        type="number",
                                        placeholder=i18n.t("general.example") + " 1.50",
                                        step=0.01,
                                        style={
                                            "width": "120px",
                                            "display": "inline-block",
                                        },
                                    ),
                                    dbc.Tooltip(
                                        i18n.t("general.bkb_tooltip"),
                                        target=ids.CORRECTIONS_BKB_INPUT,
                                        placement="top",
                                    ),
                                ],
                                style={
                                    "display": "inline-block",
                                    "margin-right": "15px",
                                },
                            ),
                            html.Div(
                                [
                                    dbc.Label(
                                        i18n.t("general.observation_cm_label"),
                                        html_for=ids.CORRECTIONS_OBSERVATION_CM_INPUT,
                                        style={
                                            "font-weight": "bold",
                                            "margin-right": "10px",
                                        },
                                    ),
                                    dbc.Input(
                                        id=ids.CORRECTIONS_OBSERVATION_CM_INPUT,
                                        type="number",
                                        placeholder=i18n.t("general.example") + " 135",
                                        step=1.0,
                                        style={
                                            "width": "120px",
                                            "display": "inline-block",
                                        },
                                    ),
                                    dbc.Tooltip(
                                        i18n.t("general.observation_cm_tooltip"),
                                        target=ids.CORRECTIONS_OBSERVATION_CM_INPUT,
                                        placement="top",
                                    ),
                                ],
                                style={
                                    "display": "inline-block",
                                    "margin-right": "15px",
                                },
                            ),
                            html.Div(
                                [
                                    dbc.Label(
                                        i18n.t("general.observation_mnap_label"),
                                        html_for=ids.CORRECTIONS_OBSERVATION_MNAP_INPUT,
                                        style={
                                            "font-weight": "bold",
                                            "margin-right": "10px",
                                        },
                                    ),
                                    dbc.Input(
                                        id=ids.CORRECTIONS_OBSERVATION_MNAP_INPUT,
                                        type="number",
                                        placeholder=i18n.t("general.example") + " 0.15",
                                        step=0.01,
                                        style={
                                            "width": "120px",
                                            "display": "inline-block",
                                        },
                                    ),
                                    dbc.Tooltip(
                                        i18n.t("general.observation_mnap_tooltip"),
                                        target=ids.CORRECTIONS_OBSERVATION_MNAP_INPUT,
                                        placement="top",
                                    ),
                                ],
                                style={"display": "inline-block"},
                            ),
                        ],
                        width=6,
                        style={"text-align": "right"},
                    ),
                ],
                style={"margin-top": "10px"},
            ),
        ]
    )
