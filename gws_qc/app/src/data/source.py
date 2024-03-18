import logging
from functools import cached_property, lru_cache
from typing import List
from copy import deepcopy

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from sqlalchemy import create_engine, select, ForeignKey, DateTime, func, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from datetime import datetime
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
        self._ruleset = None

        self.traval_result = None
        self.traval_figure = None

        # set ruleset in data object
        self.ruleset = self.get_default_ruleset()
        self._ruleset = deepcopy(self.ruleset)

    def get_default_ruleset(self):
        # ruleset
        # initialize RuleSet object
        ruleset = traval.RuleSet(name="default")

        # add rules
        ruleset.add_rule(
            "spikes",
            traval.rulelib.rule_spike_detection,
            apply_to=0,
            kwargs={"threshold": 0.15, "spike_tol": 0.15, "max_gap": "7D"},
        )

        def get_tube_top_level(name):
            return self.db.gmw_gdf.loc[name, "tube_top_position"].item()

        ruleset.add_rule(
            "hardmax",
            traval.rulelib.rule_ufunc_threshold,
            apply_to=0,
            kwargs={
                "ufunc": (np.greater,),
                "threshold": get_tube_top_level,
            },
        )
        ruleset.add_rule(
            "flat_signal",
            traval.rulelib.rule_flat_signal,
            apply_to=0,
            kwargs={"window": 100, "min_obs": 5, "std_threshold": 2e-2},
        )
        # ruleset.add_rule(
        #     "offsets",
        #     traval.rulelib.rule_offset_detection,
        #     apply_to=0,
        #     kwargs={
        #         "threshold": 0.5,
        #         "updown_diff": 0.5,
        #         "max_gap": "100D",
        #         "search_method": "time",
        #     },
        # )
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
            apply_to=(1, 2, 3),
        )
        return ruleset

    def run_traval(self, gmw_id, tube_id, ruleset=None):
        name = f"{gmw_id}-{int(tube_id):03g}"
        ic(f"Running traval for {name}...")
        ts = self.db.get_timeseries(gmw_id, tube_id)

        series = ts.loc[:, self.db.value_column]
        series.name = f"{gmw_id}-{tube_id}"
        detector = traval.Detector(series)
        ruleset = self._ruleset
        detector.apply_ruleset(ruleset)

        # TODO: store detector for now to inspect result
        self.detector = detector

        comments = detector.get_comment_series()

        df = detector.series.to_frame().loc[comments.index]
        df = ts.join(detector.get_results_dataframe())
        df["flagged"] = df.isna().any(axis=1)
        df["comment"] = ""
        df.loc[comments.index, "comment"] = comments
        df.rename(columns={"base series": "values"}, inplace=True)

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
            selected={"marker": {"opacity": 1.0, "size": 6, "color": "black"}},
            unselected={"marker": {"opacity": 1.0, "size": 3, "color": "gray"}},
            selectedpoints=[],
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


class Base(DeclarativeBase):
    pass


class GroundwaterMonitoringWell(Base):
    __tablename__ = "groundwater_monitoring_wells"

    groundwater_monitoring_well_id: Mapped[int] = mapped_column(primary_key=True)
    bro_id: Mapped[str]
    nitg_code: Mapped[str]
    tubes: Mapped[List["GroundwaterMonitoringTubesStatic"]] = relationship(
        back_populates="groundwater_monitoring_well", cascade="all, delete-orphan"
    )

    # groundwater_monitoring_tube_static_id: Mapped[int]


class GroundwaterMonitoringTubesStatic(Base):
    __tablename__ = "groundwater_monitoring_tubes_static"
    groundwater_monitoring_tube_static_id: Mapped[int] = mapped_column(primary_key=True)
    screen_length: Mapped[float]
    tube_number: Mapped[int]
    groundwater_monitoring_well_id: Mapped[int] = mapped_column(
        ForeignKey("groundwater_monitoring_wells.groundwater_monitoring_well_id")
    )
    groundwater_monitoring_well: Mapped["GroundwaterMonitoringWell"] = relationship(
        back_populates="tubes"
    )
    dynamic: Mapped[List["GroundwaterMonitoringTubesDynamic"]] = relationship(
        back_populates="groundwater_monitoring_tubes_static",
        cascade="all, delete-orphan",
    )


class GroundwaterMonitoringTubesDynamic(Base):
    __tablename__ = "groundwater_monitoring_tubes_dynamic"
    groundwater_monitoring_tube_dynamic_id: Mapped[int] = mapped_column(
        primary_key=True
    )
    tube_top_position: Mapped[float]
    plain_tube_part_length: Mapped[float]
    groundwater_monitoring_tube_static_id: Mapped[int] = mapped_column(
        ForeignKey(
            "groundwater_monitoring_tubes_static.groundwater_monitoring_tube_static_id"
        )
    )
    groundwater_monitoring_tubes_static: Mapped["GroundwaterMonitoringTubesStatic"] = (
        relationship(back_populates="dynamic")
    )


class DeliveredLocations(Base):
    __tablename__ = "delivered_locations"
    location_id: Mapped[int] = mapped_column(primary_key=True)
    coordinates: Mapped[str]
    referencesystem: Mapped[str]
    groundwater_monitoring_well_id: Mapped[int] = mapped_column(
        ForeignKey("groundwater_monitoring_wells.groundwater_monitoring_well_id")
    )


class GroundwaterLevelDossier(Base):
    __tablename__ = "groundwater_level_dossier"
    groundwater_level_dossier_id: Mapped[int] = mapped_column(primary_key=True)
    gmw_bro_id: Mapped[str]
    tube_number: Mapped[int]


class Observation(Base):
    __tablename__ = "observation"
    observation_id: Mapped[int] = mapped_column(primary_key=True)
    groundwater_level_dossier_id: Mapped[int] = mapped_column(
        ForeignKey("groundwater_level_dossier.groundwater_level_dossier_id")
    )
    observation_metadata_id: Mapped[int] = mapped_column(
        ForeignKey("observation_metadata.observation_metadata_id")
    )


class ObservationMetadata(Base):
    __tablename__ = "observation_metadata"
    observation_metadata_id: Mapped[int] = mapped_column(primary_key=True)
    observation_type: Mapped[str]


class MeasurementTvp(Base):
    __tablename__ = "measurement_tvp"
    measurement_tvp_id: Mapped[int] = mapped_column(primary_key=True)
    measurement_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    field_value: Mapped[float]
    field_value_unit: Mapped[str]
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("observation.observation_id")
    )
    measurement_point_metadata_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_point_metadata.measurement_point_metadata_id")
    )


class MeasurementPointMetadata(Base):
    __tablename__ = "measurement_point_metadata"
    measurement_point_metadata_id: Mapped[int] = mapped_column(primary_key=True)
    qualifier_by_category: Mapped[str]


class DataSource:
    def __init__(self):
        # init connection to database OR just read in some data from somewhere
        # Connect to database using psycopg2
        try:
            self.engine = create_engine(
                f"postgresql+psycopg2://{config.user}:{config.password}@"
                f"{config.host}:{config.port}/{config.database}",
                connect_args={"options": "-csearch_path=gmw,gld"},
            )

            logger.info("Database connected successfully")
        except Exception as e:
            print(e)
            logger.error("Database not connected successfully")

        self.value_column = "field_value"
        self.qualifier_column = "qualifier_by_category"
        self.source = "zeeland"

    @cached_property
    def gmw_gdf(self):
        return self._gmw_to_gdf()

    def _gmw_to_gdf(self):
        """
        Return all unique piezometers as a (Geo)DataFrame.

        Returns
        -------
        gdf : a (Geo)Pandas(Geo)DataFrame
            a (Geo)DataFrame with a unique index, describing the well-name and the tube-
            number, and at least the following columns:
                screen_top
                screen_bot
                lat
                lon
        """
        stmt = (
            select(
                GroundwaterMonitoringWell.bro_id,
                GroundwaterMonitoringWell.nitg_code,
                GroundwaterMonitoringTubesStatic.tube_number,
                GroundwaterMonitoringTubesDynamic.tube_top_position,
                GroundwaterMonitoringTubesDynamic.plain_tube_part_length,
                GroundwaterMonitoringTubesStatic.screen_length,
                DeliveredLocations.coordinates,
                DeliveredLocations.referencesystem,
            )
            .join(GroundwaterMonitoringTubesStatic.groundwater_monitoring_well)
            .join(GroundwaterMonitoringTubesDynamic)
            .join(DeliveredLocations)
        )
        # tubes = pd.read_sql(stmt, con=engine)
        gdf = gpd.GeoDataFrame.from_postgis(stmt, self.engine, geom_col="coordinates")
        # for duplicates only keep the last combination of bro_id and tube_number
        gdf = gdf[~gdf.duplicated(subset=["bro_id", "tube_number"], keep="last")]

        # make sure all locations are in EPSG:28992
        msg = "Other coordinate reference systems than RD not supported yet"
        assert (gdf["referencesystem"].str.lower() == "rd").all, msg

        # calculate top filter and bottom filter
        gdf["screen_top"] = gdf["tube_top_position"] - gdf["plain_tube_part_length"]
        gdf["screen_bot"] = gdf["screen_top"] - gdf["screen_length"]

        gdf["name"] = gdf.loc[:, ["bro_id", "tube_number"]].apply(
            lambda p: f"{p[0]}-{p[1]:03g}", axis=1
        )

        # set bro_id and tube_number as index
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
        gdf["id"] = range(gdf.index.size)

        return gdf

    @lru_cache
    def list_locations(self) -> List[str]:
        """Return a list of locations that contain groundwater level dossiers, where
        each location is defines by a tuple of length 2: bro-id and tube_id"""
        # get all grundwater level dossiers
        df = pd.read_sql(select(GroundwaterLevelDossier), con=self.engine)
        # get unique combinations of gmw id and tube id
        loc_df = df[["gmw_bro_id", "tube_number"]].drop_duplicates()
        locations = [
            f"{t[0]}-{t[1]:03g}" for t in loc_df.itertuples(index=False, name=None)
        ]
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
        stmt = (
            select(
                MeasurementTvp.measurement_time,
                MeasurementTvp.field_value,
                MeasurementPointMetadata.qualifier_by_category,
                MeasurementTvp.field_value_unit,
                MeasurementTvp.measurement_tvp_id,
                MeasurementTvp.measurement_point_metadata_id,
            )
            .join(MeasurementPointMetadata)
            .join(Observation)
            .join(ObservationMetadata)
            .join(GroundwaterLevelDossier)
            .filter(
                GroundwaterLevelDossier.gmw_bro_id.in_([gmw_id]),
                GroundwaterLevelDossier.tube_number.in_([tube_id]),
                ObservationMetadata.observation_type == "reguliereMeting",
            )
            .order_by(MeasurementTvp.measurement_time)
        )
        df = pd.read_sql(stmt, con=self.engine, index_col="measurement_time")

        # make sure all measurements are in m
        mask = df["field_value_unit"] == "cm"
        if mask.any():
            df.loc[mask, self.value_column] /= 100
            df.loc[mask, "field_value_unit"] = "m"

        # convert all other measurements to NaN
        mask = df["field_value_unit"] != "m"
        if mask.any():
            df.loc[mask, self.value_column] = np.nan
        # msg = "Other units than m or cm not supported yet"
        # assert (mtvp["field_value_unit"] == "m").all(), msg

        # make index DateTimeIndex
        if df.index.dtype == "O":
            df.index = pd.to_datetime(df.index, utc=True)
        df.index = df.index.tz_localize(None)

        # drop dupes
        df = df.loc[~df.index.duplicated(keep="first")]

        return df

    def count_measurements_per_filter(self):
        stmt = (
            select(
                GroundwaterLevelDossier.gmw_bro_id,
                GroundwaterLevelDossier.tube_number,
                func.count(MeasurementTvp.measurement_tvp_id).label("Metingen"),
            )
            .join(MeasurementPointMetadata)
            .join(Observation)
            .join(ObservationMetadata)
            .join(GroundwaterLevelDossier)
            .group_by(
                GroundwaterLevelDossier.gmw_bro_id, GroundwaterLevelDossier.tube_number
            )
            .filter(ObservationMetadata.observation_type == "reguliereMeting")
        )
        count = pd.read_sql(stmt, con=self.engine)
        return count

    def save_qualifier(self, df):
        param_columns = ["measurement_point_metadata_id", "qualifier_by_category"]
        params = df[param_columns].to_dict("records")
        with Session(self.engine) as session:
            session.execute(update(MeasurementPointMetadata), params)
            session.commit()

    def set_qualifier(self, df, qualifier="goedgekeurd"):
        mask = df["qualifier_by_category"] != qualifier
        ids = list(df.loc[mask, "measurement_point_metadata_id"])
        stmt = (
            update(MeasurementPointMetadata)
            .where(MeasurementPointMetadata.measurement_point_metadata_id.in_(ids))
            .values(qualifier_by_category=qualifier)
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
