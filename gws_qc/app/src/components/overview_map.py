import numpy as np
import plotly.graph_objs as go
from dash import dcc

from ..cache import cache
from ..data.source import DataInterface
from . import ids

try:
    mapbox_access_token = open("./assets/.mapbox_access_token", "r").read()
except FileNotFoundError:
    mapbox_access_token = None


@cache.memoize()
def render(data: DataInterface):
    df = data.db.gmw_gdf.reset_index()
    return dcc.Graph(
        id=ids.OVERVIEW_MAP,
        figure=draw_map(
            df,
            mapbox_access_token,
        ),
        style={
            "margin-top": "15",
            "height": "45vh",
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

    mask = df["metingen"] > 0

    # oseries data for map
    pb_data = dict(
        lat=df.loc[mask, "lat"],
        lon=df.loc[mask, "lon"],
        name="peilbuizen",
        # customdata=df.loc[mask, "z"],
        type="scattermapbox",
        text=df.loc[mask, "name"].tolist(),
        textposition="top center" if mapbox_access_token else None,
        textfont=dict(size=12, color="black") if mapbox_access_token else None,
        mode="markers" if mapbox_access_token else "markers",
        marker=go.scattermapbox.Marker(
            size=10,
            # sizeref=0.5,
            # sizemin=2,
            # sizemode="area",
            opacity=0.7,
            color="red",
            # colorscale=px.colors.sequential.Reds,
            # reversescale=False,
            # showscale=True,
            # colorbar={
            #     "title": "depth<br>(m NAP)",
            #     "x": -0.1,
            #     "y": 0.95,
            #     "len": 0.95,
            #     "yanchor": "top",
            # },
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            # + "<b>z:</b> NAP%{marker.color:.2f} m"
            # + "<extra></extra> "
        ),
        showlegend=False,
        unselected={"marker": {"opacity": 0.15}},
    )

    pb_nodata = dict(
        lat=df.loc[~mask, "lat"],
        lon=df.loc[~mask, "lon"],
        name="peilbuizen",
        # customdata=df.loc[~mask, "z"],
        type="scattermapbox",
        text=df.loc[~mask, "name"].tolist(),
        textposition="top center" if mapbox_access_token else None,
        textfont=dict(size=12, color="black") if mapbox_access_token else None,
        mode="markers" if mapbox_access_token else "markers",
        marker=go.scattermapbox.Marker(
            size=5,
            # sizeref=0.5,
            # sizemin=2,
            # sizemode="area",
            opacity=0.7,
            color="black",
            # colorscale=px.colors.sequential.Reds,
            # reversescale=False,
            # showscale=True,
            # colorbar={
            #     "title": "depth<br>(m NAP)",
            #     "x": -0.1,
            #     "y": 0.95,
            #     "len": 0.95,
            #     "yanchor": "top",
            # },
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            # + "<b>z:</b> NAP%{marker.color:.2f} m"
            # + "<extra></extra> "
        ),
        showlegend=False,
        unselected={"marker": {"opacity": 0.15}},
    )

    # if selected_rows is None:
    zoom, center = get_plotting_zoom_level_and_center_coordinates(
        df.lon.values, df.lat.values
    )

    mapdata = [pb_data, pb_nodata]

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
            center=center,
            # we want the map to be "parallel" to our screen, with no angle
            pitch=0,
            # default level of zoom
            zoom=zoom,
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
        # uirevision="1",
        modebar={
            "bgcolor": "rgba(255,255,255,0.9)",
        },
    )

    return dict(data=mapdata, layout=maplayout)


def get_plotting_zoom_level_and_center_coordinates(longitudes=None, latitudes=None):
    """Get zoom level and center coordinate for ScatterMapbox.

    Basic framework adopted from Krichardson under the following thread:
    https://community.plotly.com/t/dynamic-zoom-for-mapbox/32658/7
    Returns the appropriate zoom-level for these plotly-mapbox-graphics along with
    the center coordinate tuple of all provided coordinate tuples.

    Parameters
    ----------
    longitudes : array, optional
        longitudes
    latitudes : array, optional
        latitudes

    Returns
    -------
    zoom : float
        zoom level
    dict
        dictionary containing lat/lon coordinates of center point.
    """

    # Check whether both latitudes and longitudes have been passed,
    # or if the list lenghts don't match
    if (latitudes is None or longitudes is None) or (len(latitudes) != len(longitudes)):
        # Otherwise, return the default values of 0 zoom and the coordinate
        # origin as center point
        return 0, (0, 0)

    # Get the boundary-box
    b_box = {}
    b_box["height"] = latitudes.max() - latitudes.min()
    b_box["width"] = longitudes.max() - longitudes.min()
    b_box["center"] = dict(lon=np.mean(longitudes), lat=np.mean(latitudes))

    # get the area of the bounding box in order to calculate a zoom-level
    area = b_box["height"] * b_box["width"]

    # * 1D-linear interpolation with numpy:
    # - Pass the area as the only x-value and not as a list, in order to return a
    #   scalar as well
    # - The x-points "xp" should be in parts in comparable order of magnitude of the
    #   given area
    # - The zoom-levels are adapted to the areas, i.e. start with the smallest area
    #   possible of 0 which leads to the highest possible zoom value 20, and so forth
    #   decreasing with increasing areas as these variables are antiproportional
    zoom = np.interp(
        x=area,
        xp=[0, 5**-10, 4**-10, 3**-10, 2**-10, 1**-10, 1**-5],
        fp=[20, 15, 14, 13, 12, 7, 5],
    )

    zoom = min([zoom, 15])  # do not use zoom 20

    # Finally, return the zoom level and the associated boundary-box center coordinates

    # NOTE: manual correction to view all of obs for Zeeland ...
    # (because of non-square window/extent?).
    return zoom - 1.25, b_box["center"]
