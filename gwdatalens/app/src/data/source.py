import logging
import os
import pickle
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import cached_property, lru_cache
from typing import Any, List, Optional, Tuple, Union
from urllib.parse import quote

import geopandas as gpd
import i18n
import numpy as np
import pandas as pd
from pyproj import Transformer
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session

from gwdatalens.app.src.data import datamodel, sql
from gwdatalens.app.src.data.util import EPSG_28992, WGS84

logger = logger = logging.getLogger(__name__)


class DataSourceTemplate(ABC):
    """Abstract base class for a data source class.

    This class defines the interface for the data source class, which includes
    methods for retrieving metadata, listing measurement locations, and
    getting time series data from a data source (e.g. database).

    Methods
    -------
    gmw_gdf : gpd.GeoDataFrame
        Get head observations metadata as GeoDataFrame.
    list_locations: List[str]
        List of measurement location names.
    list_observation_wells: List[str]
        List of observation well names.
    list_observation_wells_with_data_sorted_by_distance : List[str]
        List of observation well names, sorted by distance.
    get_timeseries : pd.DataFrame
        Get time series.
    save_qualifier :
        Save error detection (traval) result in database.
    """

    @property
    @abstractmethod
    def gmw_gdf(self) -> gpd.GeoDataFrame:
        """Get head observations metadata as GeoDataFrame.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame containing head observations locations and metadata.
        """

    @abstractmethod
    def list_observation_wells_with_data(self) -> List[str]:
        """List of measurement location names.

        Returns
        -------
        List[str]
            List of measurement location names.
        """

    @abstractmethod
    def list_observation_wells_with_data_sorted_by_distance(self, name) -> List[str]:
        """List of measurement location names, sorted by distance.

        Parameters
        ----------
        name : str
            name of location to compute distances from

        Returns
        -------
        List[str]
            List of measurement location names, sorted by distance from `name`.
        """

    @abstractmethod
    def get_timeseries(
        self,
        gmw_id: str,
        tube_id: int,
        observation_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get time series.

        Parameters
        ----------
        gmw_id : str
            id of the observation well
        tube_id : int
            tube number of the observation well
        observation_type : str, optional
            type of observation, for BRO "reguliereMeting" or "controlemeting"

        Returns
        -------
        pd.DataFrame
            time series of head observations.
        """

    @abstractmethod
    def save_qualifier(self, df: pd.DataFrame) -> None:
        """Save error detection (traval) result after manual review.

        Parameters
        ----------
        df : pd.DataFrame
            dataframe containig error detection results after manual review.
        """

    @property
    @abstractmethod
    def backend(self):
        """Backend of the data source."""


class PostgreSQLDataSource(DataSourceTemplate):
    """DataSource class connecting to Provincie Zeelands PostgreSQL database.

    Parameters
    ----------
    config : dict
        Configuration dictionary containing database connection parameters.

    Attributes
    ----------
    config : dict
        Configuration dictionary containing database connection parameters.
    engine : sqlalchemy.engine.Engine
        SQLAlchemy engine for database connection.
    value_column : str
        Column name for the value field (containing the observations)
    source : str
        Source identifier, default is "zeeland".

    Methods
    -------
    gmw_gdf
        Returns all unique piezometers as a GeoDataFrame.
    list_locations
        Returns a list of unique measurement locations.
    list_observation_wells_with_data
        Returns a list of locations that contain groundwater level dossiers.
    list_observation_wells_with_data_sorted_by_distance
        Returns a list of locations sorted by distance from a given location.
    get_timeseries
        Returns a Pandas DataFrame for the measurements for a given location.
    count_measurements_per_filter
        Returns a count of measurements per filter.
    save_qualifier
        Saves the quality control information to the database.
    set_qc_fields_for_database(
        Sets the quality control fields.
    """

    backend = "postgresql"

    def __init__(self, config):
        # init connection to database OR just read in some data from somewhere
        # Connect to database using psycopg2
        self.config = config
        try:
            self.engine = self._engine()
            logger.info("Database connected successfully")
            # NOTE: use for background callbacks
            # self.engine.dispose()
        except Exception as e:
            self.engine = None
            msg = f"Database not connected successfully: {e}"
            logger.error(msg)
            raise Exception(msg) from e

        self.value_column = datamodel.FIELD_CALCULATED_VALUE
        self.qualifier_column = datamodel.FIELD_STATUS_QUALITY_CONTROL
        self.source = "zeeland"

    def _engine(self):
        # NOTE: could theoretically be used to return new engine for
        # background callbacks (but this approach made app slower on Windows though)
        config = self.config
        user = config.get("user")
        password = config.get("password")
        host = config.get("host")
        port = config.get("port")
        database = config.get("database")

        if not all([user, password, host, port, database]):
            raise ValueError("Database configuration is incomplete")

        # URL-encode the password
        encoded_password = quote(password, safe="")

        connection_string = (
            f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{database}"
        )

        return create_engine(
            connection_string,
            connect_args={"options": "-csearch_path=gmw,gld,public,django_admin"},
        )

    @staticmethod
    def get_location_name(df):
        return (
            df["well_code"]
            .fillna(df["bro_id"])
            .fillna(df["nitg_code"])
            .fillna(df["well_static_id"].astype(str))
        )

    @staticmethod
    def get_display_name(df):
        return (
            PostgreSQLDataSource.get_location_name(df)
            + "-"
            + df["tube_number"].apply("{:03g}".format)
        )

    @cached_property
    def gmw_gdf(self) -> gpd.GeoDataFrame:
        """Get metadata as GeoDataFrame.

        Returns
        -------
        gpd.GeoDataFrame
            A GeoDataFrame containing the metadata of piezometers.
        """
        return self._gmw_gdf()

    def get_gmw_metadata(self):
        """Return all piezometer metadata as a (Geo)DataFrame.

        Returns
        -------
        gdf : a gpd.GeoDataFrame
            a GeoDataFrame with the metadata.
        """
        stmt = sql.sql_get_gmws()
        with self.engine.connect() as con:
            gdf = gpd.GeoDataFrame.from_postgis(stmt, con=con, geom_col="coordinates")

        # make sure all locations are in EPSG:28992
        msg = "Other coordinate reference systems than RD not supported yet"
        assert (gdf["reference_system"].str.lower() == "rd").all, msg

        # calculate top filter and bottom filter
        gdf["screen_top"] = gdf["tube_top_position"] - gdf["plain_tube_part_length"]
        gdf["screen_bot"] = gdf["screen_top"] - gdf["screen_length"]

        # set location name and display name
        gdf["location_name"] = self.get_location_name(gdf)
        gdf["display_name"] = self.get_display_name(gdf)

        return gdf

    def _gmw_gdf(self):
        gdf = self.get_gmw_metadata()

        # add number of measurements
        count = self.count_measurements_per_tube()
        gdf = gdf.join(count, on=["well_static_id", "tube_static_id"], how="left")
        gdf["metingen"] = gdf["metingen"].fillna(0).astype(int)

        # add location data in RD and lat/lon in WGS84
        gdf["x"] = gdf.geometry.x
        gdf["y"] = gdf.geometry.y
        transformer = Transformer.from_proj(EPSG_28992, WGS84, always_xy=False)
        gdf.loc[:, ["lon", "lat"]] = np.vstack(
            transformer.transform(gdf["x"].values, gdf["y"].values)
        ).T

        # sort data
        gdf.sort_values(
            ["location_name", "tube_number"],
            ascending=[True, True],
            inplace=True,
        )

        # set index to our own internal numbering
        gdf["id"] = np.arange(gdf.index.size)
        gdf.index = gdf["id"]

        return gdf

    def get_tube_numbers(self, wid=None, query=None, return_ids=False):
        if wid is not None:
            well_static_id = self.gmw_gdf.loc[wid, "well_static_id"]
            location_name = self.gmw_gdf.at[wid, "location_name"]
        elif query is not None:
            sel = self.query_gdf(**query)
            if sel.index.size > 1:
                raise ValueError("Query returned multiple results.")
            well_static_id = sel.at[sel.index[0], "well_static_id"]
            location_name = sel.at[sel.index[0], "location_name"]
        else:
            raise ValueError("Either 'wid' or 'query' must be provided.")

        stmt = sql.sql_get_tube_numbers_for_location(well_static_id=well_static_id)
        with self.engine.connect() as con:
            names = pd.read_sql(stmt, con=con)

        names = location_name + names.map(lambda s: f"-{s:03g}")
        if return_ids:
            return self.query_gdf(display_name=names.tolist(), operator="in").index
        else:
            return names.squeeze("columns").to_list()

    @lru_cache  # noqa: B019
    def list_locations(self) -> pd.DataFrame:
        # # Get unique locations
        # stmt = sql.sql_get_unique_locations()
        # with self.engine.connect() as con:
        #     locs = pd.read_sql(stmt, con=con)

        gr = self.gmw_gdf.groupby("well_static_id")
        cols = [
            "well_static_id",
            "bro_id",
            "well_code",
            "nitg_code",
            "location_name",
            "id",
        ]
        locs = gr.first().reset_index().loc[:, cols]
        locs["ntubes"] = gr["tube_static_id"].count().values
        locs["hasdata"] = gr["metingen"].sum().values > 0

        return locs

    @lru_cache  # noqa: B019
    def list_observation_wells(self) -> List[str]:
        """Return a list of observation wells.

        Returns
        -------
        List[str]
            List of measurement location names.
        """
        # NOTE: this returns 7000+ locations with duplicates
        # # get all groundwater level dossiers
        # stmt = sql.sql_get_observation_wells()
        # with self.engine.connect() as con:
        #     obswells = pd.read_sql(stmt, con=con)

        # # get names
        # obswells["display_name"] = (
        #     self.get_location_name(obswells)
        #     + "-"
        #     + obswells["tube_number"].apply("{:03g}".format)
        # )
        # return obswells
        self.gmw_gdf["display_name"]

    @lru_cache  # noqa: B019
    def list_observation_wells_with_data(self) -> List[str]:
        """Return a list of locations that contain groundwater level dossiers.

        Each location is defines by a tuple of length 2: bro_id/well_code and tube_id.

        Returns
        -------
        List[str]
            List of measurement location names.
        """
        # get all groundwater level dossiers
        mask = self.gmw_gdf["metingen"] > 0
        use_cols = [
            "well_static_id",
            "bro_id",
            "well_code",
            "nitg_code",
            "tube_number",
            "display_name",
            "id",
        ]

        return self.gmw_gdf.loc[mask, use_cols]

    def list_observation_wells_with_data_sorted_by_distance(self, wid) -> List[str]:
        """List locations sorted by their distance from a given location.

        Parameters
        ----------
        wid : int
            the id of the location to compute distances from.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the locations sorted by distance.
        """
        # only locations with data:
        gdf = self.gmw_gdf.copy()
        gdf = gdf.loc[gdf["metingen"] > 0]

        try:
            p = gdf.loc[wid, "coordinates"]
        except KeyError as e:
            raise KeyError(
                f"Location id '{wid}' is not in database or has no data."
            ) from e

        gdf.drop(wid, inplace=True)
        dist = gdf.distance(p)
        dist.name = "distance"
        distsorted = gdf.join(dist, how="right").sort_values("distance", ascending=True)
        return distsorted

    def get_wellcode(self, wid=None, query=None):
        if wid is not None:
            well_code = self.gmw_gdf.at[wid, "well_code"]
        elif query is not None:
            sel = self.query_gdf(**query, columns=["well_code", "tube_number"])
            if sel.index.size > 1:
                raise ValueError("Query returned multiple results.")
            wid = sel.index[0]
            well_code = sel.at[wid, "well_code"]
        else:
            raise ValueError("Either 'wid' or 'query' must be provided.")
        tube_number = sel.at[wid, "tube_number"]
        if isinstance(well_code, str) and len(well_code) > 0:
            return well_code + f"-{tube_number:03g}"
        else:
            return ""

    def wellcode_to_broid(self, well_code):
        query = {}
        if "-" in well_code:
            # split well_code into bro_id and tube_id
            parts = well_code.split("-")
            query["well_code"] = parts[0]
            query["tube_number"] = int(parts[-1])
            tube_number = query["tube_number"]
        else:
            query["well_code"] = well_code
            tube_number = None

        bro_id = self.query_gdf(**query, columns="bro_id")
        if bro_id.empty:
            raise KeyError(f"Well code '{well_code}' not found in the database.")
        elif pd.isna(bro_id).all():
            raise ValueError(f"No bro_id available for well code '{well_code}'.")
        else:
            return bro_id.astype(str).iloc[0] + (
                f"-{tube_number:03g}" if tube_number else ""
            )

    def broid_to_wellcode(self, bro_id):
        query = {}
        if "-" in bro_id:
            # split bro_id into bro_id and tube_id
            parts = bro_id.split("-")
            query["bro_id"] = parts[0]
            query["tube_number"] = int(parts[-1])
            tube_number = query["tube_number"]
        else:
            query["bro_id"] = bro_id
            tube_number = None

        well_code = self.query_gdf(**query, columns="well_code")
        if well_code.empty:
            raise KeyError(f"Well code '{well_code}' not found in the database.")
        elif pd.isna(well_code).all():
            raise ValueError(f"No well_code available for well code '{well_code}'.")
        else:
            return well_code.astype(str).iloc[0] + (
                f"-{tube_number:03g}" if tube_number else ""
            )

    def query_gdf(
        self,
        query: str | None = None,
        operator: str = "==",
        columns: Optional[List[str] | str] = None,
        **kwargs,
    ) -> gpd.GeoDataFrame:
        """Query the gmw_gdf with a pandas query string.

        Parameters
        ----------
        query : str
            pandas query string to filter the gmw_gdf.
        columns : list of str or str, optional
            columns to return, by default None (all columns)
        **kwargs : dict
            key-value pairs to build a query string.

        Returns
        -------
        gpd.GeoDataFrame
            Filtered GeoDataFrame.
        """
        if query is not None:
            qgdf = self.gmw_gdf.query(query)
        else:
            template = "({} {} @{})"
            query = " and ".join(
                [template.format(k, operator, k) for k in kwargs.keys()]
            )
            qgdf = self.gmw_gdf.query(query, local_dict=kwargs)
        if columns is not None:
            qgdf = qgdf.loc[:, columns]
        return qgdf

    def translate(self, to: str = None, **kwargs):
        if not isinstance(to, str):
            raise TypeError("'to' must be a string.")
        q = self.query_gdf(**kwargs, columns=to)
        if q.empty:
            raise KeyError(
                "No matching entry for '{1}' in column '{0}'".format(
                    *list(kwargs.items())[0]
                )
            )
        try:
            return q.item()
        except (AttributeError, ValueError) as e:
            raise ValueError(
                f"Query did not return a single value for column '{to}'."
            ) from e

    def get_internal_id(self, **kwargs):
        return self.translate(to="id", **kwargs)

    def get_timeseries(
        self,
        wid: Optional[int] = None,
        query: Optional[dict[str:Any]] = None,
        observation_type="reguliereMeting",
        column: Optional[Union[List[str], str]] = None,
    ) -> pd.Series | pd.DataFrame:
        """Return a Pandas Series for the measurements for given bro-id and tube-id.

        Values returned im m. Return None when there are no measurements.

        Parameters
        ----------
        wid : int
            id of the observation well
        query : dict, optional
            query to select observation well, by default None
        observation_type : str, optional
            type of observation, by default "reguliereMeting". Options are
            "reguliereMeting", "controlemeting".
        column : str, optional
            column to return, by default None

        Returns
        -------
        pd.Series
            time series of head observations.
        """
        if wid is not None:
            well_static_id = self.gmw_gdf.at[wid, "well_static_id"]
            tube_static_id = int(self.gmw_gdf.at[wid, "tube_static_id"])
            display_name = self.gmw_gdf.at[wid, "display_name"]
        elif query is not None:
            sel = self.query_gdf(
                **query, columns=["well_static_id", "tube_static_id", "display_name"]
            )
            if sel.index.size > 1:
                raise ValueError("Query returned multiple results.")
            wid = sel.index[0]
            well_static_id = sel.at[wid, "well_static_id"]
            tube_static_id = int(sel.at[wid, "tube_static_id"])
            display_name = sel.at[wid, "display_name"]
        else:
            raise ValueError("Either 'wid' or 'query' must be provided.")

        logger.info(
            f"Reading timeseries for {display_name} (gmw_id: {well_static_id}, "
            f"tube_id: {tube_static_id}) ..."
        )
        stmt = sql.sql_get_timeseries(
            well_static_id=well_static_id,
            tube_static_id=tube_static_id,
            observation_type=observation_type,
        )
        with self.engine.connect() as con:
            df = pd.read_sql(stmt, con=con, index_col="measurement_time")

        if (
            df.loc[:, self.value_column].isna().all()
            and observation_type != "controlemeting"
        ):
            logger.warning(
                f"Timeseries {{display_name}} has no data in {self.value_column}!"
            )

        if self.value_column == "field_value":
            # make sure all measurements are in m
            mask = df["field_value_unit"] == "cm"
            if mask.any():
                df.loc[mask, "field_value"] /= 100.0
                df.loc[mask, "field_value_unit"] = "m"

            # convert all other measurements to NaN
            mask = ~(df["field_value_unit"].isna() | (df["field_value_unit"] == "m"))
            if mask.any():
                df.loc[mask, self.value_column] = np.nan
            # msg = "Other units than m or cm not supported yet"
            # assert (df["field_value_unit"] == "m").all(), msg

        # make index DateTimeIndex
        if df.index.dtype == "O":
            df.index = pd.to_datetime(df.index, utc=True)
        df.index = df.index.tz_localize(None)
        df.index.name = display_name

        # drop dupes
        df = df.loc[~df.index.duplicated(keep="first")]

        if column is not None:
            return df.loc[:, column]
        else:
            return df

    def count_measurements_per_tube(self):
        with self.engine.connect() as con:
            stmt = sql.sql_count_measurements()
            df = pd.read_sql(stmt, con=con)

        return df.set_index(["well_static_id", "tube_static_id"]).loc[
            :, ["metingen", "controlemetingen"]
        ]

    def count_measurements_per_tube_old(self, fast=True) -> pd.Series:
        """Count the number of measurements per filter.

        Returns
        -------
        pd.Series
            A pandas Series containing the count of measurements in each time series.
        """
        if fast:
            subq = (
                select(
                    datamodel.MeasurementTvp.observation_id,
                    func.count(datamodel.MeasurementTvp.measurement_tvp_id).label(
                        "metingen"
                    ),
                )
                .group_by(datamodel.MeasurementTvp.observation_id)
                .subquery()
            )

            stmt = (
                select(
                    datamodel.WellStatic.groundwater_monitoring_well_static_id,
                    datamodel.WellStatic.internal_id,
                    datamodel.WellStatic.bro_id,
                    datamodel.WellStatic.well_code,
                    datamodel.WellStatic.nitg_code,
                    datamodel.TubeStatic.tube_number,
                    func.sum(subq.c.metingen).label("metingen"),
                )
                .join(
                    datamodel.Observation,
                    datamodel.Observation.observation_id == subq.c.observation_id,
                )
                .join(
                    datamodel.ObservationMetadata,
                    datamodel.ObservationMetadata.observation_metadata_id
                    == datamodel.Observation.observation_metadata_id,
                )
                .join(
                    datamodel.GroundwaterLevelDossier,
                    datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id
                    == datamodel.Observation.groundwater_level_dossier_id,
                )
                .join(
                    datamodel.TubeStatic,
                    datamodel.TubeStatic.groundwater_monitoring_tube_static_id
                    == datamodel.GroundwaterLevelDossier.groundwater_monitoring_tube_id,
                )
                .join(
                    datamodel.WellStatic,
                    datamodel.WellStatic.groundwater_monitoring_well_static_id
                    == datamodel.TubeStatic.groundwater_monitoring_well_static_id,
                )
                .filter(
                    datamodel.ObservationMetadata.observation_type == "reguliereMeting"
                )
                .group_by(
                    datamodel.WellStatic.groundwater_monitoring_well_static_id,
                    datamodel.WellStatic.internal_id,
                    datamodel.WellStatic.bro_id,
                    datamodel.WellStatic.well_code,
                    datamodel.WellStatic.nitg_code,
                    datamodel.TubeStatic.tube_number,
                )
            )
            with self.engine.connect() as con:
                count = pd.DataFrame(con.execute(stmt).mappings().all())
        else:
            stmt = (
                select(
                    datamodel.WellStatic.groundwater_monitoring_well_static_id,
                    datamodel.WellStatic.internal_id,
                    datamodel.WellStatic.bro_id,
                    datamodel.WellStatic.well_code,
                    datamodel.WellStatic.nitg_code,
                    datamodel.TubeStatic.tube_number,
                    func.count(
                        func.distinct(datamodel.MeasurementTvp.measurement_time)
                    ).label("metingen"),
                )
                .join(datamodel.Observation)
                .join(datamodel.ObservationMetadata)
                .join(datamodel.GroundwaterLevelDossier)
                .join(datamodel.TubeStatic)
                .join(datamodel.WellStatic)
                .group_by(
                    datamodel.WellStatic.groundwater_monitoring_well_static_id,
                    datamodel.WellStatic.bro_id,
                    datamodel.WellStatic.nitg_code,
                    datamodel.TubeStatic.tube_number,
                )
                .filter(
                    datamodel.ObservationMetadata.observation_type == "reguliereMeting"
                )
            )
            with self.engine.connect() as con:
                count = pd.read_sql(stmt, con=con)
        return count

    def save_qualifier(self, df):
        """Save qualifier information to the database.

        Parameters
        ----------
        df : pandas.DataFrame
            The DataFrame containing the qualifier data to be saved. It must include
            the following columns:
            - datamodel.FIELD_MEASUREMENT_POINT_METADATA_ID
            - datamodel.FIELD_STATUS_QUALITY_CONTROL
            - datamodel.FIELD_CENSOR_REASON_DATALENS
            - datamodel.FIELD_CENSOR_REASON
            - datamodel.VALUE_LIMIT
        """
        df = self.set_qc_fields_for_database(df)

        param_columns = [
            datamodel.FIELD_MEASUREMENT_POINT_METADATA_ID,
            datamodel.FIELD_STATUS_QUALITY_CONTROL,
            datamodel.FIELD_CENSOR_REASON_DATALENS,
            datamodel.FIELD_CENSOR_REASON,
            datamodel.FIELD_VALUE_LIMIT,
        ]
        params = df[param_columns].to_dict("records")
        with Session(self.engine) as session:
            session.execute(update(datamodel.MeasurementPointMetadata), params)
            session.commit()

    def save_correction(self, df):
        """Save correction information to the database.

        Parameters
        ----------
        df : pandas.DataFrame
            The DataFrame containing the correction data to be saved. It must include
            the following columns:
            - measurement_tvp_id: identifier of the measurement to correct
            - corrected_value: new value to save to calculated_value
            - comment: reason for the correction (saved to correction_reason)

        Notes
        -----
        This method:
        - Saves the original calculated_value to value_to_be_corrected
        - Updates calculated_value with the corrected_value
        - Saves the comment to correction_reason
        - Records the current timestamp to correction_time
        """
        # Prepare the updates
        params = []
        for _, row in df.iterrows():
            # Convert numpy types to Python native types
            measurement_tvp_id = int(row["measurement_tvp_id"])
            original_calc_value = row.get("original_calculated_value")
            if original_calc_value is not None and pd.notna(original_calc_value):
                original_calc_value = float(original_calc_value)

            corrected_value = row["corrected_value"]
            if corrected_value is not None and pd.notna(corrected_value):
                corrected_value = float(corrected_value)

            param = {
                "measurement_tvp_id": measurement_tvp_id,
                "value_to_be_corrected": original_calc_value,
                "calculated_value": corrected_value,
                "correction_reason": row.get("comment", ""),
                "correction_time": datetime.now(timezone.utc),
            }
            params.append(param)

        # Execute batch update
        with Session(self.engine) as session:
            session.execute(update(datamodel.MeasurementTvp), params)
            session.commit()

    def reset_correction(self, df):
        """Reset correction information in the database.

        Parameters
        ----------
        df : pandas.DataFrame
            The DataFrame containing the corrections to reset. It must include
            the following column:
            - measurement_tvp_id: identifier of the measurement to reset

        Notes
        -----
        This method:
        - Restores calculated_value from value_to_be_corrected
        - Clears correction_reason, value_to_be_corrected, and correction_time
        """
        # Prepare the reset updates
        params = []
        for _, row in df.iterrows():
            # Convert numpy types to Python native types
            measurement_tvp_id = int(row["measurement_tvp_id"])
            value_to_be_corrected = row.get("value_to_be_corrected")
            if value_to_be_corrected is not None and pd.notna(value_to_be_corrected):
                value_to_be_corrected = float(value_to_be_corrected)

            param = {
                "measurement_tvp_id": measurement_tvp_id,
                "calculated_value": value_to_be_corrected,
                "value_to_be_corrected": None,
                "correction_reason": None,
                "correction_time": None,
            }
            params.append(param)

        # Execute batch update
        with Session(self.engine) as session:
            session.execute(update(datamodel.MeasurementTvp), params)
            session.commit()

    def set_qc_fields_for_database(self, df, mask=None):
        if mask is None:
            mask = np.ones(df.index.size, dtype=bool)
        # approved obs
        mask2 = df.loc[:, self.qualifier_column].isin(
            [
                i18n.t("general.reliable"),
                i18n.t("general.unknown"),
            ]
        )
        if mask.any():
            df.loc[mask & mask2, datamodel.FIELD_CENSOR_REASON_DATALENS] = None
            df.loc[mask & mask2, "censor_reason"] = None
            df.loc[mask & mask2, "value_limit"] = None

        # flagged obs: create censor_reason_datalens
        mask2 = df.loc[:, self.qualifier_column].isin(
            [
                i18n.t("general.unreliable"),
                i18n.t("general.undecided"),
            ]
        )
        if mask2.any():
            df.loc[mask & mask2, datamodel.FIELD_CENSOR_REASON_DATALENS] = df.loc[
                mask & mask2, ["comment", "category"]
            ].apply(lambda s: ",".join(s), axis=1)

        return df


class HydropandasDataSource(DataSourceTemplate):
    backend = "hydropandas"

    def __init__(self, extent=None, oc=None, fname=None, source="bro", **kwargs):
        if oc is None:
            if fname is None:
                fname = "obs_collection.zip"
            if os.path.isfile(fname):
                oc = pd.read_pickle(fname)
            else:
                import hydropandas as hpd

                if source == "bro":
                    oc = hpd.read_bro(extent, **kwargs)
                    with open(fname, "wb") as file:
                        pickle.dump(oc, file)
                else:
                    raise ValueError(
                        f"Automatic download for source='{source}' not supported."
                    )

        self.source = source
        if self.source == "bro":
            self.value_column = "values"
            self.qualifier_column = "qualifier"
        else:
            self.value_column = "stand_m_tov_nap"
            self.qualifier_column = "bijzonderheid"

        self.oc = oc

    @cached_property
    def gmw_gdf(self) -> gpd.GeoDataFrame:
        return self._gmw_to_gdf()

    def _gmw_to_gdf(self):
        """Return all groundwater monitoring wells (gmw) as a GeoDataFrame.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame containing groundwater monitoring well locations and metadata
        """
        oc = self.oc
        use_cols = oc.columns.difference({"obs"})
        gdf = gpd.GeoDataFrame(
            oc.loc[:, use_cols], geometry=gpd.points_from_xy(oc.x, oc.y)
        )
        columns = {
            "monitoring_well": "bro_id",
            "screen_bottom": "screen_bot",
            "tube_nr": "tube_number",
            "tube_top": "tube_top_position",
        }
        gdf = gdf.rename(columns=columns)
        gdf["nitg_code"] = ""

        # add location data in RD and lat/lon in WGS84
        transformer = Transformer.from_proj(EPSG_28992, WGS84, always_xy=False)
        gdf.loc[:, ["lon", "lat"]] = np.vstack(
            transformer.transform(gdf["x"].values, gdf["y"].values)
        ).T

        # add number of measurements
        gdf["metingen"] = self.oc.stats.n_observations
        gdf["bro_id"] = gdf.index.tolist()

        # sort data
        gdf.sort_values(
            ["bro_id", "tube_number"],
            ascending=[True, True],
            inplace=True,
        )

        # add id
        gdf["id"] = range(gdf.index.size)

        return gdf

    @lru_cache  # noqa: B019
    def list_observation_wells_with_data(self) -> List[Tuple[str, int]]:
        """Return a list of locations that contain groundwater level dossiers.

        Each location is defines by a tuple of length 2: bro-id and tube_id.

        Returns
        -------
        List[Tuple[str, int]]
            List of measurement location names.
        """
        oc = self.oc
        locations = []
        mask = [not x.dropna(how="all").empty for x in oc["obs"]]
        for index in oc[mask].index:
            # locations.append(tuple(oc.loc[index, ["monitoring_well", "tube_nr"]]))
            locations.append(index)
        return locations

    def list_observation_wells_with_data_sorted_by_distance(self, name):
        gdf = self.gmw_gdf.copy()
        p = gdf.loc[name, "geometry"]
        gdf.drop(name, inplace=True)
        dist = gdf.distance(p)
        dist.name = "distance"
        distsorted = self.oc.join(dist, how="right").sort_values(
            "distance", ascending=True
        )
        return distsorted

    def get_timeseries(
        self,
        gmw_id: str,
        tube_id: Optional[Union[int, str]] = None,
        observation_type="reguliereMeting",
    ) -> pd.DataFrame:
        """Return a Pandas Series for the measurements for gmw_id and tube_id.

        Values returned in m. Return None when there are no measurements.

        Parameters
        ----------
        gmw_id : str
            id of the observation well
        tube_id : int
            tube number of the observation well

        Returns
        -------
        pd.DataFrame
            time series of head observations.
        """
        # empty return for controlemeting
        if observation_type == "controlemeting":
            return pd.Series()

        if self.source == "bro":
            name = f"{gmw_id}_{tube_id}"  # bro
        elif self.source == "dino":
            if isinstance(tube_id, str):
                name = f"{gmw_id}-{tube_id}"  # dino
            elif isinstance(tube_id, int):
                name = f"{gmw_id}-{tube_id:03g}"
        else:
            raise ValueError

        columns = [self.value.column, self.qualifier_column]
        df = pd.DataFrame(self.oc.loc[name, "obs"].loc[:, columns])
        return df

    def save_qualifier(self, df: pd.DataFrame) -> None:
        raise NotImplementedError("Not connected to a database. Use CSV export!")
