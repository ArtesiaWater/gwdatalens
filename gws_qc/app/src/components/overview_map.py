from functools import partial

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from . import ids, tab_overview, tab_qc

import plotly.express as px
import plotly.graph_objs as go
import pandas as pd

mapbox_access_token = open("./assets/.mapbox_access_token", "r").read()


def render(app):
    return dcc.Graph(
        id=ids.OVERVIEW_MAP,
        figure=draw_map(
            pd.DataFrame(),
            mapbox_access_token,
        ),
        style={
            "height": "45vh",
            # "margin-bottom": "10px",
        },
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToAdd": ["zoom", "zoom2d"],
        },
    )


def draw_map(
    df,
    mapbox_access_token,
):
    """Draw ScatterMapBox.

    Parameters
    ----------
    df : pandas.DataFrame
        data to plot
    mapbox_access_token : str
        mapbox access token, see Readme for more information

    Returns
    -------
    dict
        dictionary containing plotly maplayout and mapdata
    """
    # msize = 20 + 150 * (df["z"].max() - df["z"]) / (
    #     df["z"].max() - df["z"].min()
    # )
    # msize.fillna(30, inplace=True)

    # oseries data for map
    pb_data = dict(
        # lat=df.lat,
        # lon=df.lon,
        name="peilbuizen",
        # customdata=df.z,
        type="scattermapbox",
        # text=df.reset_index()["name"].tolist(),
        textposition="top center" if mapbox_access_token else None,
        textfont=dict(size=12, color="black") if mapbox_access_token else None,
        mode="markers+text" if mapbox_access_token else "markers",
        marker=go.scattermapbox.Marker(
            # size=msize,
            sizeref=0.5,
            sizemin=2,
            sizemode="area",
            opacity=0.7,
            # color=df["z"],
            colorscale=px.colors.sequential.Reds,
            reversescale=False,
            showscale=True,
            colorbar={
                "title": "depth<br>(m NAP)",
                "x": -0.1,
                "y": 0.95,
                "len": 0.95,
                "yanchor": "top",
            },
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            + "<b>z:</b> NAP%{marker.color:.2f} m"
            + "<extra></extra> "
        ),
        showlegend=False,
        unselected={"marker": {"opacity": 0.5}},
    )

    # if selected_rows is None:
    #     zoom, center = get_plotting_zoom_level_and_center_coordinates(
    #         df.lon.values, df.lat.values
    #     )

    mapdata = [pb_data]

    maplayout = dict(
        # top, bottom, left and right margins
        margin=dict(t=0, b=0, l=0, r=0),
        font=dict(color="#000000", size=11),
        paper_bgcolor="white",
        clickmode="event+select",
        mapbox=dict(
            # here you need the token from Mapbox
            accesstoken=mapbox_access_token,
            bearing=0,
            # where we want the map to be centered
            center={"lon": 3.61389, "lat": 51.5},
            # we want the map to be "parallel" to our screen, with no angle
            pitch=0,
            # default level of zoom
            zoom=9,
            # default map style (some options listed, not all support labels)
            style="outdoors" if mapbox_access_token else "open-street-map",
            # public styles
            # style="carto-positron",
            # style="open-street-map",
            # style="stamen-terrain",
            # mapbox only styles (requires access token):
            # style="basic",
            # style="streets",
            # style="light",
            # style="dark",
            # style="satellite",
            # style="satellite-streets"
        ),
        # relayoutData=mapbox_cfg,
        legend={"x": 0.99, "y": 0.99, "xanchor": "right", "yanchor": "top"},
        uirevision="1",
        modebar={
            "bgcolor": "rgba(255,255,255,0.9)",
        },
    )

    return dict(data=mapdata, layout=maplayout)
