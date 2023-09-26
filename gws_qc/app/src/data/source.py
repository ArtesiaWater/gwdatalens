from typing import List, Tuple
import pandas as pd
import geopandas as gpd
import psycopg2
import logging
import config

logger = logger = logging.getLogger(__name__)


class DataSource:
    def __init__(self):
        # init connection to database OR just read in some data from somewhere
        # Connect to database using psycopg2
        try:
            self.connection = psycopg2.connect(
                database=config.database,
                user=config.user,
                password=config.password,
                host=config.host,
                port=config.port,
            )

            self.cursor = self.connection.cursor()
            logger.info("Database connected successfully")
        except:
            logger.error("Database not connected successfully")

    def gmw_to_gdf(self):
        """Return all groundwater monitoring wells (gmw) as a GeoDataFrame"""
        # get a DataFrame with the properties of all wells
        df = self._get_table_df("gmw.groundwater_monitoring_wells")

        # get a GeoDataFrame with locations
        table_name = "gmw.delivered_locations"
        query = f"select *  FROM {table_name}"
        locs = gpd.GeoDataFrame.from_postgis(
            query, self.connection, geom_col="coordinates"
        )
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
        # table_name = "gmw.groundwater_monitoring_wells"
        # get all grundwater level dossiers
        df = self.get_table("gld.groundwater_level_dossier")
        # get unique combinations of gmw id and tube id
        loc_df = df[["gmw_bro_id", "groundwater_monitoring_tube_id"]].drop_duplicates()
        locations = list(loc_df.itertuples(index=False, name=None))
        return locations

    def get_timeseries(self, gmw_id: str, tube_id: int) -> pd.Series:
        """Retrun a Pandas Series for the measurements at the requested bro-id and
        tube-id"""
        # get groundwater_level_dossier_id
        table_name = "gld.groundwater_level_dossier"
        query = f"select groundwater_level_dossier_id FROM {table_name} WHERE gmw_bro_id = '{gmw_id}' AND groundwater_monitoring_tube_id = {tube_id}"
        self._execute_query(query)
        gld_ids = [x[0] for x in self.cursor.fetchall()]
        if len(gld_ids) == 0:
            logger.info(f"No data found for {gmw_id}, {tube_id}")
            return None

        # get observation_id
        table_name = "gld.observation"
        gld_ids_str = str(gld_ids).replace("[", "").replace("]", "")
        query = f"select observation_id FROM {table_name} WHERE groundwater_level_dossier_id in ({gld_ids_str})"
        self._execute_query(query)
        observation_ids = [x[0] for x in self.cursor.fetchall()]
        if len(observation_ids) == 0:
            logger.info(f"No data found for {gmw_id}, {tube_id}")
            return None

        # get measurement_time_series_id
        table_name = "gld.measurement_time_series"
        observation_ids_str = str(observation_ids).replace("[", "").replace("]", "")
        query = f"select measurement_time_series_id FROM {table_name} WHERE observation_id in ({observation_ids_str})"
        self._execute_query(query)
        measurement_time_series_ids = [x[0] for x in self.cursor.fetchall()]
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

        # do we get field_value, calculated_value or corrected_value
        s = pd.to_numeric(df["field_value"]).sort_index()
        return s

    def _get_all_tables(self):
        self.cursor.execute("SELECT table_name FROM information_schema.tables")
        tables = [x for x in self.cursor.fetchall()]
        return tables

    def _get_tables(self, schema):
        self.cursor.execute(
            f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}'"
        )
        tables = [x[0] for x in self.cursor.fetchall()]
        return tables

    def _exists_table(self, table):
        self.cursor.execute(
            f"select exists(select * FROM information_schema.tables where table_name={table})"
        )
        return self.cursor.fetchone()[0]

    def _get_table_df(self, table_name):
        query = f"select * FROM {table_name}"
        return self._query_to_df(query)

    def _execute_query(self, query):
        try:
            self.cursor.execute(query)
        except Exception as e:
            self.cursor.execute("rollback")
            raise (Exception(e))

    def _query_to_df(self, query):
        self._execute_query(query)
        colnames = [desc[0] for desc in self.cursor.description]
        records = self.cursor.fetchall()
        df = pd.DataFrame(records, columns=colnames)

        return df
