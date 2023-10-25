from typing import List, Tuple
import pandas as pd
import geopandas as gpd
import logging
import sqlalchemy as sa

try:
    from . import config
except:
    import config

logger = logger = logging.getLogger(__name__)


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

    def gmw_to_gdf(self):
        """Return all groundwater monitoring wells (gmw) as a GeoDataFrame"""
        # get a DataFrame with the properties of all wells
        df = self._get_table_df("gmw.groundwater_monitoring_wells")

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

        # add locations to properties of wells
        df = df.merge(locs, how="left", on="groundwater_monitoring_well_id")
        gdf = gpd.GeoDataFrame(df, geometry="coordinates")
        return gdf

    def list_locations(self) -> List[Tuple[str, int]]:
        """Return a list of locations that contain groundwater level dossiers, where
        each location is defines by a tuple of length 2: bro-id and tube_id"""
        # get all grundwater level dossiers
        df = self._get_table_df("gld.groundwater_level_dossier")
        # get unique combinations of gmw id and tube id
        loc_df = df[["gmw_bro_id", "groundwater_monitoring_tube_id"]].drop_duplicates()
        locations = list(loc_df.itertuples(index=False, name=None))
        return locations

    def get_timeseries(
        self, gmw_id: str, tube_id: int, column="calculated_value"
    ) -> pd.Series:
        """Return a Pandas Series for the measurements at the requested bro-id and
        tube-id, im m. Return None when there are no measurements."""
        # get groundwater_level_dossier_id
        table_name = "gld.groundwater_level_dossier"
        query = f"select groundwater_level_dossier_id FROM {table_name} WHERE gmw_bro_id = '{gmw_id}' AND groundwater_monitoring_tube_id = {tube_id}"
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

        # get measurement_time_series_id
        table_name = "gld.measurement_time_series"
        observation_ids_str = str(observation_ids).replace("[", "").replace("]", "")
        query = f"select measurement_time_series_id FROM {table_name} WHERE observation_id in ({observation_ids_str})"
        cursor = self._execute_query(query)
        measurement_time_series_ids = [x[0] for x in cursor.fetchall()]
        if len(measurement_time_series_ids) == 0:
            logger.info(f"No data found for {gmw_id}, {tube_id}")
            return None

        # get measurements from table gld.measurement_tvp
        table_name = "gld.measurement_tvp"
        measurement_time_series_ids_str = (
            str(measurement_time_series_ids).replace("[", "").replace("]", "")
        )
        query = f"select * FROM {table_name} WHERE measurement_time_series_id in ({measurement_time_series_ids_str})"
        df = self._query_to_df(query).set_index("measurement_time")
        # make sure all measurements are in cm
        msg = "Other units than cm not supported yet"
        assert (df["field_value_unit"] == "cm").all(), msg
        # TODO: do we get field_value, calculated_value or corrected_value?
        s = pd.to_numeric(df[column]).sort_index() / 100.0
        return s

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
