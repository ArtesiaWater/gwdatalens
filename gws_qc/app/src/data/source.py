import logging
import os
import pickle
from functools import cached_property, lru_cache
from typing import List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import sqlalchemy as sa
import traval
from icecream import ic
from pyproj import Transformer

from .util import EPSG_28992, WGS84, get_model_sim_pi

try:
    from . import config
except ImportError:
    import config

logger = logger = logging.getLogger(__name__)


class DataInterface:
    def __init__(self, db=None, pstore=None, traval=None):
        self.db = db
        self.pstore = pstore
        self.traval = traval

    def attach_pastastore(self, pstore):
        self.pstore = pstore

    def attach_traval(self, traval):
        self.traval = traval


class TravalInterface:
    def __init__(self, db, pstore=None):
        self.db = db
        self.pstore = pstore
        self.ruleset = None
        
        self.traval_result = None
        self.traval_figure = None

    def load_ruleset(self):
        # ruleset
        # initialize RuleSet object
        ruleset = traval.RuleSet(name="basic")

        # add rules
        ruleset.add_rule(
            "spikes",
            traval.rulelib.rule_spike_detection,
            apply_to=0,
            kwargs={"threshold": 0.15, "spike_tol": 0.15, "max_gap": "7D"},
        )
        ic(self.db.gmw_gdf.index)
        ruleset.add_rule(
            "hardmax",
            traval.rulelib.rule_ufunc_threshold,
            apply_to=0,
            kwargs={
                "ufunc": (np.greater,),
                "threshold": lambda name: self.db.gmw_gdf.loc[name, "screen_top"],
            },
        )
        ruleset.add_rule(
            "flat_signal",
            traval.rulelib.rule_flat_signal,
            apply_to=0,
            kwargs={"window": 100, "min_obs": 5, "std_threshold": 2e-2},
        )
        ruleset.add_rule(
            "offsets",
            traval.rulelib.rule_offset_detection,
            apply_to=0,
            kwargs={
                "threshold": 0.5,
                "updown_diff": 0.5,
                "max_gap": "100D",
                "search_method": "time",
            },
        )
        ci = 0.99
        ruleset.add_rule(
            "pastas",
            traval.rulelib.rule_pastas_outside_pi,
            apply_to=0,
            kwargs={
                "ml": lambda name: self.pstore.models[name],
                "ci": ci,
                "min_ci": 0.1,
                "smoothfreq": "30D",
                "verbose": True,
            },
        )
        ruleset.add_rule(
            "combine_results",
            traval.rulelib.rule_combine_nan_or,
            apply_to=(1, 2, 3, 4),
        )

        # set ruleset in data object
        self.ruleset = ruleset

    def run_traval(self, gmw_id, tube_id):
        name = f"{gmw_id}-{int(tube_id):03g}"
        ic(f"Running traval for {name}...")
        ts = self.db.get_timeseries(gmw_id, tube_id)

        series = ts.loc[:, self.db.value_column]
        series.name = f"{gmw_id}-{tube_id}"
        detector = traval.Detector(series)
        detector.apply_ruleset(self.ruleset)

        comments = detector.get_comment_series()

        df = detector.series.to_frame().loc[comments.index]
        df.columns = ["values"]
        df["comment"] = ""
        df.loc[comments.index, "comment"] = comments

        df.index.name = "datetime"
        # table = df.reset_index().to_dict("records")
        try:
            ml = self.pstore.get_models(series.name)
        except Exception as e:
            ic(e)
            ml = None
        figure = self.plot_traval_result(detector, ml)
        return df, figure

    @staticmethod
    def plot_traval_result(detector, model=None):
        traces = []

        ts0 = detector.series

        trace_0 = go.Scattergl(
            x=ts0.index,
            y=ts0.values,
            mode="markers+lines",
            line={
                "width": 1,
                "color": "gray",
            },
            marker={
                "size": 3,
                "line_color": "gray",
            },
            name=ts0.name,
            legendgroup=ts0.name,
            showlegend=True,
        )
        traces.append(trace_0)

        colors = px.colors.qualitative.Dark24
        for step, corrections in detector.corrections.items():
            if isinstance(corrections, np.ndarray) or corrections.empty:
                continue
            ts_i = ts0.loc[corrections.index]
            label = detector.ruleset.get_step_name(step)
            trace_i = go.Scattergl(
                x=ts_i.index,
                y=ts_i.values,
                mode="markers",
                marker={
                    "size": 8,
                    "symbol": "x-thin",
                    "line_width": 2,
                    "line_color": colors[(step - 1) % len(colors)],
                },
                name=label,
                legendgroup=label,
                showlegend=True,
                legendrank=1003,
            )
            traces.append(trace_i)

        if model is not None:
            try:
                ci = detector.ruleset.get_rule(stepname="pastas")["kwargs"]["ci"]
            except KeyError:
                ci = 0.95
            sim, pi = get_model_sim_pi(model, ts0, ci=ci, smoothfreq="30D")
            trace_sim = go.Scattergl(
                x=sim.index,
                y=sim.values,
                mode="lines",
                line={
                    "width": 1,
                    "color": "cornflowerblue",
                },
                name="model simulation",
                legendgroup="model simulation",
                showlegend=True,
                legendrank=1001,
            )
            trace_lower = go.Scattergl(
                x=pi.index,
                y=pi.iloc[:, 0].values,
                mode="lines",
                line={"width": 0.5, "color": "rgba(100,149,237,0.35)"},
                name=f"PI ({ci:.1%})",
                legendgroup="PI",
                showlegend=False,
                fill="tonexty",
                legendrank=1005,
            )
            trace_upper = go.Scattergl(
                x=sim.index,
                y=pi.iloc[:, 1].values,
                mode="lines",
                line={"width": 0.5, "color": "rgba(100,149,237,0.35)"},
                name=f"PI ({ci:.1%})",
                legendgroup="PI",
                showlegend=True,
                fill="tonexty",
                fillcolor="rgba(100,149,237,0.1)",
                legendrank=1002,
            )

            traces = [trace_lower, trace_upper] + traces + [trace_sim]

        layout = {
            # "xaxis": {"range": [sim.index[0], sim.index[-1]]},
            "yaxis": {"title": "(m NAP)"},
            "legend": {
                "traceorder": "reversed+grouped",
                "orientation": "h",
                "xanchor": "left",
                "yanchor": "bottom",
                "x": 0.0,
                "y": 1.02,
            },
            # "hovermode": "x",
            "dragmode": "pan",
            # "margin": dict(t=70, b=40, l=40, r=10),
        }

        return dict(data=traces, layout=layout)


class DataSource:
    def __init__(self):
        # init connection to database OR just read in some data from somewhere
        # Connect to database using psycopg2
        try:
            self.engine = sa.create_engine(
                f"postgresql+psycopg2://{config.user}:{config.password}@"
                f"{config.host}:{config.port}/{config.database}"
            )

            logger.info("Database connected successfully")
        except Exception as e:
            print(e)
            logger.error("Database not connected successfully")

        self.value_column = "field_value"
        self.qualifier_column = "qualifier"
        self.source = "zeeland"

    @cached_property
    def gmw_gdf(self):
        return self._gmw_to_gdf()

    def _gmw_to_gdf(self):
        """Return all groundwater monitoring wells (gmw) as a GeoDataFrame"""
        # get a DataFrame with the properties of all wells
        wells = self._get_table_df("gmw.groundwater_monitoring_wells")

        # get a GeoDataFrame with locations
        table_name = "gmw.delivered_locations"
        query = sa.text(f"select *  FROM {table_name}")
        with self.engine.connect() as connection:
            locs = gpd.GeoDataFrame.from_postgis(
                query, connection, geom_col="coordinates"
            )
        # make sure all locations are in EPSG:28992
        msg = "Other coordinate reference systems than RD not supported yet"
        assert (locs["referencesystem"].str.lower() == "rd").all, msg
        # drop duplicate location entries (TODO: find out why they are there)
        mask = locs["groundwater_monitoring_well_id"].duplicated()
        if mask.any():
            logger.info(f"Dropping {mask.sum()} duplicate delivered_locations")
            locs = locs[~mask]

        # add information from locations wells
        wells = wells.merge(locs, how="left", on="groundwater_monitoring_well_id")

        # combine static and dynamic tube-info
        tube_dyn = self._get_table_df("gmw.groundwater_monitoring_tubes_dynamic")
        tube_dyn = tube_dyn[
            ~tube_dyn["groundwater_monitoring_tube_static_id"].duplicated(keep="last")
        ]

        tubes = self._get_table_df("gmw.groundwater_monitoring_tubes_static")
        tubes = tubes.merge(
            tube_dyn, how="left", on="groundwater_monitoring_tube_static_id"
        )

        # only keep wells with a gmw
        tubes = tubes[
            tubes["groundwater_monitoring_well_id"].isin(
                wells["groundwater_monitoring_well_id"]
            )
        ]
        # add information from wells to tubes
        tubes = tubes.merge(wells, how="left", on="groundwater_monitoring_well_id")

        gdf = gpd.GeoDataFrame(tubes, geometry="coordinates")

        # calculate top filter and bottom filter
        gdf["screen_top"] = gdf["tube_top_position"] - gdf["plain_tube_part_length"]
        gdf["screen_bot"] = gdf["screen_top"] - gdf["screen_length"]

        gdf["name"] = gdf.loc[:, ["bro_id", "tube_number"]].apply(
            lambda p: f"{p[0]}-{p[1]:03g}", axis=1
        )

        # set bro_id and tube_number as index
        # gdf = gdf.set_index(["bro_id", "tube_number"])
        gdf = gdf.set_index("name")

        # add number of measurements
        gdf["metingen"] = 0
        hasobs = [x for x in self.list_locations() if x in gdf.index]
        gdf.loc[hasobs, "metingen"] = 1

        # add location data in RD and lat/lon in WGS84
        gdf["x"] = gdf.geometry.x
        gdf["y"] = gdf.geometry.y

        transformer = Transformer.from_proj(EPSG_28992, WGS84, always_xy=False)
        gdf.loc[:, ["lon", "lat"]] = np.vstack(
            transformer.transform(gdf["x"].values, gdf["y"].values)
        ).T

        # sort data:
        gdf.sort_values(
            ["metingen", "nitg_code", "tube_number"], ascending=False, inplace=True
        )

        # gdf = gdf.reset_index()
        return gdf

    @lru_cache
    def list_locations(self) -> List[Tuple[str, int]]:
        """Return a list of locations that contain groundwater level dossiers, where
        each location is defines by a tuple of length 2: bro-id and tube_id"""
        # get all grundwater level dossiers
        df = self._get_table_df("gld.groundwater_level_dossier")
        # get unique combinations of gmw id and tube id
        loc_df = df[["gmw_bro_id", "tube_number"]].drop_duplicates()
        locations = list(loc_df.itertuples(index=False, name=None))
        return locations

    def list_locations_sorted_by_distance(self, name):
        gdf = self.gmw_gdf.copy()
        gdf = gdf.set_index("name")
        # ic(gdf.head())
        # ic(name)
        # ic(gdf.loc[name, "coordinates"])

        p = gdf.loc[name, "coordinates"]

        gdf.drop(name, inplace=True)
        dist = gdf.distance(p)
        dist.name = "distance"
        distsorted = gdf.join(dist, how="right").sort_values("distance", ascending=True)
        return distsorted
        # return list(
        #     distsorted.loc[:, ["monitoring_well", "tube_nr"]]
        #     .apply(tuple, axis=1)
        #     .values
        # )

    def get_timeseries(self, gmw_id: str, tube_id: int) -> pd.Series:
        """Return a Pandas Series for the measurements at the requested bro-id and
        tube-id, im m. Return None when there are no measurements."""
        # get groundwater_level_dossier_id
        table_name = "gld.groundwater_level_dossier"
        query = f"select groundwater_level_dossier_id FROM {table_name} WHERE gmw_bro_id = '{gmw_id}' AND tube_number = {tube_id}"
        cursor = self._execute_query(query)
        gld_ids = [x[0] for x in cursor.fetchall()]
        if len(gld_ids) == 0:
            logger.info(f"No data found for {gmw_id}, {tube_id}")
            return None

        # get observation_id
        table_name = "gld.observation"
        gld_ids_str = str(gld_ids).replace("[", "").replace("]", "")
        query = f"select observation_id FROM {table_name} WHERE groundwater_level_dossier_id in ({gld_ids_str})"
        cursor = self._execute_query(query)
        observation_ids = [x[0] for x in cursor.fetchall()]
        if len(observation_ids) == 0:
            logger.info(f"No data found for {gmw_id}, {tube_id}")
            return None

        # get measurements from table gld.measurement_tvp
        table_name = "gld.measurement_tvp"
        observation_ids_str = str(observation_ids).replace("[", "").replace("]", "")
        query = f"select * FROM {table_name} WHERE observation_id in ({observation_ids_str})"
        mtvp = self._query_to_df(query).set_index("measurement_time")

        # make sure all measurements are in m
        mask = mtvp["field_value_unit"] == "cm"
        if mask.any():
            mtvp.loc[mask, self.value_column] /= 100
            mtvp.loc[mask, "field_value_unit"] = "m"

        # convert all other measurements to NaN
        mask = mtvp["field_value_unit"] != "m"
        if mask.any():
            mtvp.loc[mask, self.value_column] = np.nan
        # msg = "Other units than m or cm not supported yet"
        # assert (mtvp["field_value_unit"] == "m").all(), msg

        mtvp[self.value_column] = pd.to_numeric(mtvp[self.value_column])

        # get measurement_point_metadata_id
        table_name = "gld.measurement_point_metadata"
        mpm_id = mtvp["measurement_point_metadata_id"]
        measurement_point_metadata_ids_str = (
            str(list(mpm_id.unique())).replace("[", "").replace("]", "")
        )
        query = f"select * FROM {table_name} WHERE measurement_point_metadata_id in ({measurement_point_metadata_ids_str})"
        mpm = self._query_to_df(query).set_index("measurement_point_metadata_id")

        # add qualifier to time-value-pairs
        mtvp[self.qualifier_column] = mpm.loc[
            mtvp["measurement_point_metadata_id"], "qualifier_by_category"
        ].values

        # only keep value and qualifier, and sort index
        df = mtvp[[self.value_column, self.qualifier_column]].sort_index()

        # make index DateTimeIndex
        if df.index.dtype == "O":
            df.index = pd.to_datetime(df.index, utc=True)
        df.index = df.index.tz_localize(None)

        # drop dupes
        df = df.loc[~df.index.duplicated(keep="first")]

        return df

    # def set_qualifier(self, df, qualifier="goedgekeurd"):
    #    table_name = "gld.type_status_quality_control"
    #    query = f"select qualifier_by_category_id FROM {table_name} WHERE value = '{qualifier}'"
    #    cursor = self._execute_query(query)
    #    gld_ids = [x[0] for x in cursor.fetchall()]
    #    if len(gld_ids) == 0:
    #        raise (Exception(f"Unknown qualifier: {qualifier}"))

    def _get_all_tables(self):
        cursor = self._execute_query("SELECT table_name FROM information_schema.tables")
        tables = [x for x in cursor.fetchall()]
        # tables = sa.inspect(self.engine).get_table_names()
        return tables

    def _get_tables_in_schema(self, schema):
        cursor = self._execute_query(
            f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}'"
        )
        tables = [x[0] for x in cursor.fetchall()]
        return tables

    def _exists_table(self, table):
        cursor = self._execute_query(
            f"select exists(select * FROM information_schema.tables where table_name={table})"
        )
        return cursor.fetchone()[0]
        # return self.engine.dialect.has_table(self.engine.connect(), table)

    def _get_table_df(self, table_name):
        query = f"select * FROM {table_name}"
        return self._query_to_df(query)

    def _execute_query(self, query):
        with self.engine.connect() as connection:
            result = connection.execute(sa.text(query))
        return result

    def _query_to_df(self, query):
        with self.engine.connect() as connection:
            df = pd.read_sql_query(sa.text(query), con=connection)
        return df
