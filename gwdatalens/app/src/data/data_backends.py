"""Data source abstraction layer for groundwater monitoring data.

Provides abstract interface (DataSourceTemplate) for pluggable backends:
- PostgreSQLDataSource: Production PostgreSQL database
- HydropandasDataSource: In-memory hydropandas collections

This module orchestrates database connections, metadata building,
and time series retrieval while delegating specific responsibilities
to specialized modules.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import cached_property
from time import perf_counter
from typing import Any, List, Optional, Sequence, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from sqlalchemy import bindparam, column, func, or_, select, text, update, values
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from gwdatalens.app.constants import (
    ColumnNames,
    DatabaseFields,
    QCFlags,
    TimeRangeDefaults,
    UnitConversion,
)
from gwdatalens.app.messages import t_
from gwdatalens.app.src.data import datamodel, sql
from gwdatalens.app.src.data.database_connector import DatabaseConnector
from gwdatalens.app.src.data.metadata_builder import (
    TUBE_NUMBER_FORMAT,
    GMWMetadataBuilder,
)
from gwdatalens.app.src.data.spatial_transformer import SpatialTransformer
from gwdatalens.app.src.data.util import conditional_cachedmethod
from gwdatalens.app.validators import validate_not_empty, validate_single_result

try:
    from cachetools import TTLCache

    CACHETOOLS_AVAILABLE = True
except (ModuleNotFoundError, ImportError):
    CACHETOOLS_AVAILABLE = False

logger = logging.getLogger(__name__)

GMW_METADATA_COLUMNS = [
    ColumnNames.WELL_STATIC_ID,
    ColumnNames.BRO_ID,
    ColumnNames.WELL_CODE,
    ColumnNames.WELL_NITG_CODE,
    ColumnNames.TUBE_NUMBER,
    ColumnNames.DISPLAY_NAME,
    ColumnNames.ID,
]


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

    @property
    @abstractmethod
    def list_observation_wells_with_data(self) -> List[str]:
        """List of measurement location names.

        Returns
        -------
        List[str]
            List of measurement location names.
        """

    @abstractmethod
    def list_observation_wells_with_data_sorted_by_distance(self, wid) -> List[str]:
        """List of measurement location names, sorted by distance.

        Parameters
        ----------
        wid : int
            internal id of observation well

        Returns
        -------
        List[str]
            List of measurement location names, sorted by distance from `wid`.
        """

    @abstractmethod
    def get_timeseries(
        self,
        wid: int,
        tube_id: int,
        observation_type: Optional[str] = None,
        tmin: Optional[str] = None,
        tmax: Optional[str] = None,
        deduplicate: bool = True,
    ) -> pd.DataFrame:
        """Get time series.

        Parameters
        ----------
        wid_id : str
            id of the observation well
        tube_id : int
            tube number of the observation well
        observation_type : str, optional
            type of observation, for BRO "reguliereMeting" or "controlemeting"
        tmin : str or None, optional
            ISO-8601 date string; only measurements at or after this timestamp
            are returned.
        tmax : str or None, optional
            ISO-8601 date string; only measurements at or before this timestamp
            are returned.
        deduplicate : bool, optional
            When ``True`` (default) keep only the highest ``measurement_tvp_id``
            for each distinct timestamp (handled in SQL for PostgreSQL, in
            memory for Hydropandas).  Set ``False`` to skip the deduplication
            step and receive raw rows.

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

    Composition-based architecture with delegated responsibilities:
    - DatabaseConnector: database connection management
    - GMWMetadataBuilder: metadata enrichment
    - SpatialTransformer: coordinate transformations

    Parameters
    ----------
    config : dict
        Configuration dictionary containing database connection parameters.

    Attributes
    ----------
    connector : DatabaseConnector
        Database connection handler
    metadata_builder : GMWMetadataBuilder
        Metadata construction and enrichment
    value_column : str
        Column name for the value field (containing the observations)
    qualifier_column : str
        Column name for the qualifier field
    source : str
        Source identifier, default is "zeeland".
    """

    backend = "postgresql"

    def __init__(
        self,
        config: dict,
        use_cache: bool = False,
        max_cache_size: Optional[int] = None,
        cache_timeout: Optional[int] = None,
    ):
        """Initialize PostgreSQL data source.

        Parameters
        ----------
        config : dict
            Database configuration dictionary
        """
        self.connector = DatabaseConnector(config)
        self.metadata_builder = GMWMetadataBuilder(
            self.connector,
            spatial_transformer=SpatialTransformer(),
        )

        self.value_column = DatabaseFields.FIELD_CALCULATED_VALUE
        self.qualifier_column = DatabaseFields.FIELD_STATUS_QUALITY_CONTROL
        self.source = "zeeland"

        # expiring LRU cache (for timeseries)
        if CACHETOOLS_AVAILABLE and use_cache:
            self.use_cache = use_cache
            self._cache = TTLCache(maxsize=max_cache_size, ttl=cache_timeout)
        else:
            self.use_cache = False
            self._cache = None

        # Permanent instance-level cache for gmw_gdf.  Well metadata is
        # loaded once at startup and never changes during a session, so a
        # TTL-expiring cache is wrong here.  Using a plain attribute avoids
        # re-executing two database queries on every get_timeseries() call
        # when USE_LRU_CACHE is false.
        self._gmw_gdf_store: Optional[gpd.GeoDataFrame] = None

    @property
    def engine(self):
        """Get database engine from connector."""
        return self.connector.engine

    @property
    def gmw_gdf(self) -> gpd.GeoDataFrame:
        """Get metadata as GeoDataFrame, building it once per instance lifetime.

        Returns
        -------
        gpd.GeoDataFrame
            A GeoDataFrame containing the metadata of piezometers.
        """
        if self._gmw_gdf_store is None:
            self._gmw_gdf_store = self._build_gmw_gdf()
        return self._gmw_gdf_store

    def invalidate_gmw_gdf(self) -> None:
        """Force a rebuild of gmw_gdf on the next access.

        Call this after any operation that may change well/tube metadata
        (e.g. importing new wells from BRO).
        """
        self._gmw_gdf_store = None

    def _build_gmw_gdf(self, include_krw_lichaam: bool = False) -> gpd.GeoDataFrame:
        """Build and enrich groundwater monitoring well GeoDataFrame.

        Parameters
        ----------
        include_krw_lichaam : bool, optional
            Temporary option. When ``True``, enrich metadata with
            ``krw_lichaam`` from ``gld.grondwaterlichaam`` joined on
            ``tube_static_id``.

        Returns
        -------
        gpd.GeoDataFrame
            Enriched GeoDataFrame with all metadata
        """
        # Build base metadata
        gdf = self.metadata_builder.build_gmw_metadata()

        # Add measurement counts
        count = self.count_measurements_per_tube()
        date_range = self.get_timeseries_date_range_per_tube()
        count = count.join(date_range, how="left")

        # Enrich metadata
        gdf = self.metadata_builder.enrich_metadata(gdf, count)

        if include_krw_lichaam:
            stmt = sql.sql_get_krw_lichaam_per_tube()
            krw_df = self.connector.execute_query(stmt, index_col=["tube_static_id"])

            # Normalize join key dtype on both sides to avoid pandas merge errors
            # (e.g. int64 vs object from database driver).
            gdf = gdf.copy()
            gdf[ColumnNames.TUBE_STATIC_ID] = pd.to_numeric(
                gdf[ColumnNames.TUBE_STATIC_ID], errors="coerce"
            ).astype("Int64")
            krw_df.index = pd.to_numeric(krw_df.index, errors="coerce").astype("Int64")

            gdf = gdf.join(krw_df, on=ColumnNames.TUBE_STATIC_ID, how="left")

        # Sort and index
        gdf = gdf.sort_values(
            ["location_name", ColumnNames.TUBE_NUMBER],
            ascending=[True, True],
        )
        gdf[ColumnNames.ID] = np.arange(len(gdf))
        gdf.index = gdf[ColumnNames.ID]

        return gdf

    def get_timeseries_date_range_per_tube(
        self,
        observation_type: Optional[Union[str, Sequence[str]]] = None,
    ) -> pd.DataFrame:
        """Get first and last observation timestamp per tube from database.

        Parameters
        ----------
        observation_type : str, sequence or None, optional
            Optional filter for observation type(s). Provide a string for a
            single type, a list/tuple of types for multiple, or None to include
            all observation types.

        Returns
        -------
        pd.DataFrame
            DataFrame indexed by (well_static_id, tube_static_id) with columns
            ``first_observation_date`` and ``last_observation_date``.
        """
        stmt = sql.sql_get_timeseries_date_range(observation_type=observation_type)
        df = self.connector.execute_query(
            stmt,
            index_col=[ColumnNames.WELL_STATIC_ID, ColumnNames.TUBE_STATIC_ID],
        )
        return df.loc[:, ["first_observation_date", "last_observation_date"]].map(
            lambda t: t.date()
        )

    def get_tube_numbers(self, wid=None, query=None, return_ids=False):
        """Get tube numbers for a given well.

        Parameters
        ----------
        wid : int, optional
            Well ID from gmw_gdf
        query : dict, optional
            Query parameters to find the well
        return_ids : bool, optional
            If True, return internal IDs instead of names

        Returns
        -------
        list or pd.Index
            Tube names or IDs
        """
        if wid is not None:
            well_static_id = self.gmw_gdf.loc[wid, ColumnNames.WELL_STATIC_ID]
            location_name = self.gmw_gdf.at[wid, ColumnNames.LOCATION_NAME]
        elif query is not None:
            sel = self.query_gdf(**query)
            row = validate_single_result(sel, context="well lookup")
            well_static_id = row[ColumnNames.WELL_STATIC_ID]
            location_name = row[ColumnNames.LOCATION_NAME]
        else:
            raise ValueError("Either 'wid' or 'query' must be provided.")

        stmt = sql.sql_get_tube_numbers_for_location(well_static_id=well_static_id)
        names = self.connector.execute_query(stmt)

        names = location_name + names.map(lambda s: f"-{s:{TUBE_NUMBER_FORMAT}}")
        if return_ids:
            return self.query_gdf(display_name=names.tolist(), operator="in").index
        else:
            return names.squeeze("columns").to_list()

    @cached_property
    def list_locations(self) -> pd.DataFrame:
        # # Get unique locations
        # stmt = sql.sql_get_unique_locations()
        # with self.engine.connect() as con:
        #     locs = pd.read_sql(stmt, con=con)

        gr = self.gmw_gdf.groupby(ColumnNames.WELL_STATIC_ID)
        cols = [
            ColumnNames.WELL_STATIC_ID,
            ColumnNames.BRO_ID,
            ColumnNames.WELL_CODE,
            ColumnNames.WELL_NITG_CODE,
            "location_name",
            ColumnNames.ID,
        ]
        locs = gr.first().reset_index().loc[:, cols]
        locs["ntubes"] = gr[ColumnNames.TUBE_STATIC_ID].count().values
        locs["hasdata"] = gr["metingen"].sum().values > 0

        return locs

    @cached_property
    def list_observation_wells(self) -> List[str]:
        """Return a list of observation wells.

        Returns
        -------
        List[str]
            List of measurement location names.
        """
        return self.gmw_gdf[ColumnNames.DISPLAY_NAME].tolist()

    @cached_property
    def list_observation_wells_with_data(self) -> pd.DataFrame:
        """Return a list of locations that contain groundwater level dossiers.

        Each location is defines by a tuple of length 2: bro_id/well_code and tube_id.

        Returns
        -------
        List[str]
            List of measurement location names.
        """
        # get all groundwater level dossiers
        mask = self.gmw_gdf["metingen"] > 0

        return self.gmw_gdf.loc[mask, GMW_METADATA_COLUMNS]

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
            well_code = self.gmw_gdf.at[wid, ColumnNames.WELL_CODE]
            tube_number = self.gmw_gdf.at[wid, ColumnNames.TUBE_NUMBER]
        elif query is not None:
            sel = self.query_gdf(
                **query, columns=[ColumnNames.WELL_CODE, ColumnNames.TUBE_NUMBER]
            )
            row = validate_single_result(sel, context="well code lookup")
            well_code = row[ColumnNames.WELL_CODE]
            tube_number = row[ColumnNames.TUBE_NUMBER]
        else:
            raise ValueError("Either 'wid' or 'query' must be provided.")
        if isinstance(well_code, str) and len(well_code) > 0:
            return well_code + f"-{tube_number:03g}"
        else:
            return ""

    def wellcode_to_broid(self, well_code):
        query = {}
        if "-" in well_code:
            # split well_code into bro_id and tube_id
            parts = well_code.split("-")
            query[ColumnNames.WELL_CODE] = parts[0]
            query[ColumnNames.TUBE_NUMBER] = int(parts[-1])
            tube_number = query[ColumnNames.TUBE_NUMBER]
        else:
            query[ColumnNames.WELL_CODE] = well_code
            tube_number = None

        bro_id = self.query_gdf(**query, columns=ColumnNames.BRO_ID)
        validate_not_empty(bro_id, context=f"bro_id lookup for well code '{well_code}'")
        if pd.isna(bro_id).all():
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
            query[ColumnNames.BRO_ID] = parts[0]
            query[ColumnNames.TUBE_NUMBER] = int(parts[-1])
            tube_number = query[ColumnNames.TUBE_NUMBER]
        else:
            query[ColumnNames.BRO_ID] = bro_id
            tube_number = None

        well_code = self.query_gdf(**query, columns=ColumnNames.WELL_CODE)
        validate_not_empty(well_code, context=f"well code lookup for bro_id '{bro_id}'")
        if pd.isna(well_code).all():
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

    def get_corresponding_value(self, to: str = None, **kwargs):
        if not isinstance(to, str):
            raise TypeError("'to' must be a string.")
        q = self.query_gdf(**kwargs, columns=to)
        validate_not_empty(
            q, context=f"entry for '{list(kwargs.items())[0] if kwargs else 'unknown'}'"
        )
        try:
            return q.item()
        except (AttributeError, ValueError) as e:
            raise ValueError(
                f"Query did not return a single value for column '{to}'."
            ) from e

    def get_internal_id(self, **kwargs):
        return self.get_corresponding_value(to=ColumnNames.ID, **kwargs)

    @conditional_cachedmethod(lambda self: self._cache)
    def get_timeseries(
        self,
        wid: Optional[int] = None,
        query: Optional[dict[str, Any]] = None,
        observation_type: Optional[Union[str, Sequence[str]]] = "reguliereMeting",
        columns: Optional[Union[List[str], str]] = None,
        tmin: Optional[str] = None,
        tmax: Optional[str] = None,
        deduplicate: bool = True,
    ) -> pd.Series | pd.DataFrame:
        """Return a Pandas Series for the measurements for given bro-id and tube-id.

        Values returned im m. Return None when there are no measurements.

        Parameters
        ----------
        wid : int
            id of the observation well
        query : dict, optional
            query to select observation well, by default None
        observation_type : str, sequence or None, optional
            Type(s) of observation to filter for. Provide a string for a single
            type, a list/tuple of types for multiple, or None to return all
            observations regardless of type. Defaults to "reguliereMeting".
        columns : str, optional
            columns to return, by default None
        tmin : str or None, optional
            ISO-8601 date string; only measurements at or after this timestamp
            are returned.  ``None`` means no lower bound.
        tmax : str or None, optional
            ISO-8601 date string; only measurements at or before this timestamp
            are returned.  ``None`` means no upper bound.
        deduplicate : bool, optional
            When ``True`` (default) the SQL query uses ``ROW_NUMBER()`` to keep
            only the highest ``measurement_tvp_id`` per timestamp across all
            observations for the well/tube.  Set ``False`` to skip the window
            function for a faster query when data quality is known to be clean.

        Returns
        -------
        pd.Series
            time series of head observations.
        """
        if wid is not None:
            well_static_id = self.gmw_gdf.at[wid, ColumnNames.WELL_STATIC_ID]
            tube_static_id = int(self.gmw_gdf.at[wid, ColumnNames.TUBE_STATIC_ID])
            display_name = self.gmw_gdf.at[wid, ColumnNames.DISPLAY_NAME]
        elif query is not None:
            sel = self.query_gdf(
                **query,
                columns=[
                    ColumnNames.WELL_STATIC_ID,
                    ColumnNames.TUBE_STATIC_ID,
                    ColumnNames.DISPLAY_NAME,
                ],
            )
            row = validate_single_result(sel, context="timeseries lookup")
            well_static_id = row[ColumnNames.WELL_STATIC_ID]
            tube_static_id = int(row[ColumnNames.TUBE_STATIC_ID])
            display_name = row[ColumnNames.DISPLAY_NAME]
        else:
            raise ValueError("Either 'wid' or 'query' must be provided.")

        logger.info(
            "Loading time series for %s (%sgmw_id: %s, tube_id: %s, obstype: %s"
            ", tmin: %s, tmax: %s)",
            display_name,
            f"id: {wid}, " if wid else "",
            well_static_id,
            tube_static_id,
            observation_type,
            tmin,
            tmax,
        )
        stmt = sql.sql_get_timeseries(
            well_static_id=well_static_id,
            tube_static_id=tube_static_id,
            observation_type=observation_type,
            tmin=tmin,
            tmax=tmax,
            deduplicate=deduplicate,
        )
        df = self.connector.execute_query(stmt, index_col=["measurement_time"])

        # fix time zone and ensure index is timezone-naive in local time
        # (handling DST issues)
        df.index = (
            pd.to_datetime(df.index, utc=True)
            .tz_convert(TimeRangeDefaults.LOCAL_TIMEZONE)
            .tz_localize(None, ambiguous="NaT", nonexistent="shift_forward")
        )

        if (
            df.loc[:, self.value_column].isna().all()
            and observation_type != "controlemeting"
        ):
            logger.warning(
                "Timeseries %s has no data in %s!", display_name, self.value_column
            )

        if self.value_column == ColumnNames.FIELD_VALUE:
            # make sure all measurements are in m
            mask = df["field_value_unit"] == "cm"
            if mask.any():
                df.loc[mask, ColumnNames.FIELD_VALUE] *= UnitConversion.CM_TO_M
                df.loc[mask, "field_value_unit"] = "m"

            # convert all other measurements to NaN
            # mask = ~(df["field_value_unit"].isna() | (df["field_value_unit"] == "m"))
            # if mask.any():
            #     df.loc[mask, self.value_column] = np.nan
            # msg = "Other units than m or cm not supported yet"
            # assert (df["field_value_unit"] == "m").all(), msg

        df.index.name = display_name

        # drop dupes
        if df.index.has_duplicates:
            if deduplicate:
                # SQL deduplication was requested but duplicates slipped through
                # (e.g. the window function was applied per-observation, or the
                # query plan chose a different path). Log a warning and fall
                # back to the pandas approach so callers always receive a
                # unique-index result.
                logger.warning(
                    "Duplicate timestamps found in timeseries %s after SQL "
                    "deduplication — falling back to in-memory dedup "
                    "(preferring non-null measurement_point_metadata_id, "
                    "then highest measurement_tvp_id).",
                    display_name,
                )
            else:
                logger.debug(
                    "Duplicate timestamps found in timeseries %s "
                    "(deduplicate=False — applying in-memory dedup).",
                    display_name,
                )
            df = (
                df.sort_values(
                    ["measurement_point_metadata_id", "measurement_tvp_id"],
                    ascending=[True, True],
                    na_position="first",
                )
                .groupby(level=0, sort=False)
                .tail(1)
                .sort_index()  # restore temporal order lost by sort_values+groupby
            )

        # Ensure the returned DataFrame is always monotonically increasing by
        # measurement_time, regardless of which dedup path was taken or whether
        # the DB engine returned rows in a different order.
        if not df.index.is_monotonic_increasing:
            logger.debug(
                "Sorting timeseries %s index to enforce monotonic order.",
                display_name,
            )
            df = df.sort_index()

        # mark None status quality control as "unknown" when not labeled
        if pd.isnull(df[ColumnNames.STATUS_QUALITY_CONTROL]).any():
            logger.warning(
                "Timeseries %s contains measurements with NULL quality control "
                "status — treating as 'unknown'.",
                display_name,
            )
            # use Dutch flag, as database uses Dutch values
            df[ColumnNames.STATUS_QUALITY_CONTROL] = df[
                ColumnNames.STATUS_QUALITY_CONTROL
            ].where(
                ~pd.isnull(df[ColumnNames.STATUS_QUALITY_CONTROL]), QCFlags.ONBEKEND
            )

        if columns is not None:
            return df.loc[:, columns]
        else:
            return df

    def count_measurements_per_tube(self):
        """Count measurements per tube from database.

        Returns
        -------
        pd.DataFrame
            DataFrame indexed by (well_static_id, tube_static_id) with measurement
            counts
        """
        stmt = sql.sql_count_measurements()
        df = self.connector.execute_query(
            stmt, index_col=[ColumnNames.WELL_STATIC_ID, ColumnNames.TUBE_STATIC_ID]
        )

        return df.loc[:, ["metingen", "controlemetingen"]]

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

    def _execute_db_write(
        self,
        stmt,
        params: Optional[Sequence[dict[str, Any]]] = None,
        *,
        operation_name: str,
        lock_timeout: str = "5s",
        statement_timeout: str = "120s",
    ):
        """Execute a write statement in a transaction with session-local timeouts.

        Parameters
        ----------
        stmt : sqlalchemy.sql.Executable
            Statement to execute.
        params : sequence of dict, optional
            Optional parameter mappings for executemany-style execution.
        operation_name : str
            Human-readable operation name used in logging.
        lock_timeout : str, optional
            PostgreSQL lock timeout value, defaults to ``"5s"``.
        statement_timeout : str, optional
            PostgreSQL statement timeout value, defaults to ``"120s"``.

        Returns
        -------
        Any
            SQLAlchemy result object from ``session.execute``.
        """
        with Session(self.engine) as session:
            try:
                session.execute(
                    text("SELECT set_config('lock_timeout', :lock_timeout, true)"),
                    {"lock_timeout": lock_timeout},
                )
                session.execute(
                    text(
                        "SELECT set_config('statement_timeout', "
                        ":statement_timeout, true)"
                    ),
                    {"statement_timeout": statement_timeout},
                )

                if params is None:
                    result = session.execute(stmt)
                else:
                    result = session.execute(stmt, params)

                t_commit = perf_counter()
                session.commit()
                logger.info(
                    "%s commit finished in %.2fs",
                    operation_name,
                    perf_counter() - t_commit,
                )
                return result
            except OperationalError as e:
                session.rollback()
                sqlstate = getattr(getattr(e, "orig", None), "pgcode", None)
                logger.exception(
                    "%s failed with OperationalError (SQLSTATE=%s).",
                    operation_name,
                    sqlstate,
                )
                raise
            except Exception:
                session.rollback()
                logger.exception("%s failed and was rolled back.", operation_name)
                raise

    def save_qualifier(self, df):
        """Save qualifier information to the database.

        Parameters
        ----------
        df : pandas.DataFrame
            The DataFrame containing the qualifier data to be saved. It must include
            the following columns:
            - DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID
            - DatabaseFields.FIELD_MEASUREMENT_TVP_ID
            - DatabaseFields.FIELD_STATUS_QUALITY_CONTROL
            - DatabaseFields.FIELD_CENSOR_REASON_DATALENS
            - DatabaseFields.FIELD_CENSOR_REASON
            - DatabaseFields.VALUE_LIMIT
        """
        if df is None or df.empty:
            logger.info("No qualifier changes to save.")
            return
        df = self.set_qc_fields_for_database(df)

        total_rows = len(df)
        if DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID not in df.columns:
            raise KeyError(
                "Missing required column "
                f"'{DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID}' in export."
            )

        null_mpmid_count = int(
            df[DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID].isna().sum()
        )
        if null_mpmid_count > 0:
            logger.warning(
                "QC qualifier export: %s row(s) have NULL/NaN "
                "measurement_point_metadata_id and will be skipped "
                "(not updated in database).",
                null_mpmid_count,
            )

        df = df.dropna(subset=[DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID])
        if df.empty:
            logger.info("No valid qualifier rows to save after dropping null IDs.")
            return

        # Defensive deduplication by update key. In normal flows this should be 1:1,
        # but duplicate IDs can massively inflate executemany payload size.
        if DatabaseFields.FIELD_MEASUREMENT_TVP_ID in df.columns:
            df = df.sort_values(DatabaseFields.FIELD_MEASUREMENT_TVP_ID)
        unique_ids_before = df[
            DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID
        ].nunique()
        df = df.drop_duplicates(
            subset=[DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID],
            keep="last",
        )
        unique_ids_after = df[
            DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID
        ].nunique()

        param_map = {
            "b_measurement_point_metadata_id": (
                DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID
            ),
            "b_status_quality_control": DatabaseFields.FIELD_STATUS_QUALITY_CONTROL,
            "b_censor_reason_datalens": (DatabaseFields.FIELD_CENSOR_REASON_DATALENS),
            "b_censor_reason": DatabaseFields.FIELD_CENSOR_REASON,
            "b_value_limit": DatabaseFields.FIELD_VALUE_LIMIT,
        }
        params = []
        for row in df.to_dict("records"):
            param_dict = {alias: row[col] for alias, col in param_map.items()}
            # ORM bulk update requires PK with actual column name
            param_dict[DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID] = row[
                DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID
            ]
            params.append(param_dict)

        logger.info(
            "QC qualifier export payload: input_rows=%s valid_rows=%s "
            "unique_measurement_point_metadata_id_before=%s after=%s",
            total_rows,
            len(params),
            unique_ids_before,
            unique_ids_after,
        )

        if not params:
            logger.info("No qualifier changes to save after preprocessing.")
            return

        # Set-based export pipeline using SQLAlchemy Core + mapped datamodel:
        # - Build an in-memory VALUES table
        # - Execute one UPDATE ... FROM against measurement_point_metadata
        # - Update only rows that actually changed (IS DISTINCT FROM)
        stage_rows = [
            (
                p[DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID],
                p["b_status_quality_control"],
                p["b_censor_reason_datalens"],
                p["b_censor_reason"],
                p["b_value_limit"],
            )
            for p in params
        ]

        staged_values = (
            values(
                column("measurement_point_metadata_id"),
                column("status_quality_control"),
                column("status_quality_control_reason_datalens"),
                column("censor_reason"),
                column("value_limit"),
                name="tmp_qc_qualifier_updates",
            )
            .data(stage_rows)
            .alias("s")
        )

        update_stmt = (
            update(datamodel.MeasurementPointMetadata)
            .where(
                datamodel.MeasurementPointMetadata.measurement_point_metadata_id
                == staged_values.c.measurement_point_metadata_id
            )
            .where(
                or_(
                    datamodel.MeasurementPointMetadata.status_quality_control.is_distinct_from(  # noqa: E501
                        staged_values.c.status_quality_control
                    ),
                    datamodel.MeasurementPointMetadata.status_quality_control_reason_datalens.is_distinct_from(  # noqa: E501
                        staged_values.c.status_quality_control_reason_datalens
                    ),
                    datamodel.MeasurementPointMetadata.censor_reason.is_distinct_from(
                        staged_values.c.censor_reason
                    ),
                    datamodel.MeasurementPointMetadata.value_limit.is_distinct_from(
                        staged_values.c.value_limit
                    ),
                )
            )
            .values(
                {
                    datamodel.MeasurementPointMetadata.status_quality_control: (
                        staged_values.c.status_quality_control
                    ),
                    datamodel.MeasurementPointMetadata.status_quality_control_reason_datalens: (  # noqa: E501
                        staged_values.c.status_quality_control_reason_datalens
                    ),
                    datamodel.MeasurementPointMetadata.censor_reason: (
                        staged_values.c.censor_reason
                    ),
                    datamodel.MeasurementPointMetadata.value_limit: (
                        staged_values.c.value_limit
                    ),
                }
            )
            .execution_options(synchronize_session=False)
        )

        result = self._execute_db_write(
            update_stmt,
            operation_name="QC qualifier set-based export",
        )
        logger.info(
            "QC qualifier update stats (matched=%s, staged=%s)",
            result.rowcount,
            len(stage_rows),
        )

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
        - Saves the original calculated_value to initial_calculated_value
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
                "b_measurement_tvp_id": measurement_tvp_id,
                ColumnNames.INITIAL_CALCULATED_VALUE: original_calc_value,
                ColumnNames.CALCULATED_VALUE: corrected_value,
                ColumnNames.CORRECTION_REASON: row.get("comment", ""),
                ColumnNames.CORRECTION_TIME: datetime.now(timezone.utc),
            }
            # include PK with actual column name for ORM bulk update
            param[DatabaseFields.FIELD_MEASUREMENT_TVP_ID] = measurement_tvp_id
            params.append(param)

        # Execute batch update
        stmt = (
            update(datamodel.MeasurementTvp)
            .where(
                datamodel.MeasurementTvp.measurement_tvp_id
                == bindparam("b_measurement_tvp_id")
            )
            .values(
                {
                    ColumnNames.INITIAL_CALCULATED_VALUE: bindparam(
                        ColumnNames.INITIAL_CALCULATED_VALUE
                    ),
                    ColumnNames.CALCULATED_VALUE: bindparam(
                        ColumnNames.CALCULATED_VALUE
                    ),
                    ColumnNames.CORRECTION_REASON: bindparam("correction_reason"),
                    ColumnNames.CORRECTION_TIME: bindparam("correction_time"),
                }
            )
            .execution_options(synchronize_session=False)
        )
        self._execute_db_write(
            stmt,
            params=params,
            operation_name="Correction batch update",
        )

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
        - Restores calculated_value from initial_calculated_value
        - Clears correction_reason, initial_calculated_value, and correction_time
        """
        # Prepare the reset updates
        params = []
        for _, row in df.iterrows():
            # Convert numpy types to Python native types
            measurement_tvp_id = int(row["measurement_tvp_id"])
            initial_calculated_value = row.get(ColumnNames.INITIAL_CALCULATED_VALUE)
            if initial_calculated_value is not None and pd.notna(
                initial_calculated_value
            ):
                initial_calculated_value = float(initial_calculated_value)

            param = {
                "b_measurement_tvp_id": measurement_tvp_id,
                ColumnNames.CALCULATED_VALUE: initial_calculated_value,
                ColumnNames.INITIAL_CALCULATED_VALUE: None,
                ColumnNames.CORRECTION_REASON: None,
                ColumnNames.CORRECTION_TIME: None,
            }
            # include PK with actual column name for ORM bulk update
            param[DatabaseFields.FIELD_MEASUREMENT_TVP_ID] = measurement_tvp_id
            params.append(param)

        # Execute batch update
        stmt = (
            update(datamodel.MeasurementTvp)
            .where(
                datamodel.MeasurementTvp.measurement_tvp_id
                == bindparam("b_measurement_tvp_id")
            )
            .values(
                {
                    ColumnNames.CALCULATED_VALUE: bindparam(
                        ColumnNames.CALCULATED_VALUE
                    ),
                    ColumnNames.INITIAL_CALCULATED_VALUE: bindparam(
                        ColumnNames.INITIAL_CALCULATED_VALUE
                    ),
                    ColumnNames.CORRECTION_REASON: bindparam("correction_reason"),
                    ColumnNames.CORRECTION_TIME: bindparam("correction_time"),
                }
            )
            .execution_options(synchronize_session=False)
        )
        self._execute_db_write(
            stmt,
            params=params,
            operation_name="Correction reset batch update",
        )

    def set_qc_fields_for_database(self, df, mask=None):
        if mask is None:
            mask = np.ones(df.index.size, dtype=bool)

        # approved obs
        mask2 = df.loc[:, self.qualifier_column].isin(
            [
                t_("general.reliable"),
                t_("general.unknown"),
            ]
        )
        if mask.any():
            df.loc[mask & mask2, DatabaseFields.FIELD_CENSOR_REASON_DATALENS] = None
            df.loc[mask & mask2, DatabaseFields.FIELD_CENSOR_REASON] = None
            df.loc[mask & mask2, DatabaseFields.FIELD_VALUE_LIMIT] = None

        # flagged obs: create censor_reason_datalens
        mask2 = df.loc[:, self.qualifier_column].isin(
            [
                t_("general.unreliable"),
                t_("general.undecided"),
            ]
        )
        if mask2.any():
            df.loc[mask & mask2, DatabaseFields.FIELD_CENSOR_REASON_DATALENS] = df.loc[
                mask & mask2, ["comment", "category"]
            ].apply(lambda s: ",".join(s), axis=1)

        return df
