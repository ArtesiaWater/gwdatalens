from typing import List, Tuple
import logging
import os
import pickle
import pandas as pd
import geopandas as gpd

logger = logger = logging.getLogger(__name__)


class DataSourceHydropandas:
    def __init__(self, oc=None):
        if oc is None:
            fname = "obs_collection.pickle"
            if os.path.isfile(fname):
                with open(fname, "rb") as file:
                    oc = pickle.load(file)
            else:
                import hydropandas as hpd

                extent = [18000, 38000, 384000, 403000]
                extent = [18000, 25000, 393000, 403000]
                extent = [48000, 52000, 422000, 427000]
                oc = hpd.read_bro(extent, tmin="2020", tmax="2024")
                with open(fname, "wb") as file:
                    pickle.dump(oc, file)
            # only keep locations with time series
            oc = oc[[not oc.loc[index]["obs"].empty for index in oc.index]]
        self.oc = oc

        self.value_column = "values"
        self.qualifier_column = "qualifier"

    def gmw_to_gdf(self):
        """Return all groundwater monitoring wells (gmw) as a GeoDataFrame"""
        oc = self.oc
        gdf = gpd.GeoDataFrame(oc, geometry=gpd.points_from_xy(oc.x, oc.y))
        columns = {
            "monitoring_well": "bro_id",
            "screen_bottom": "screen_bot",
            "tube_nr": "tube_number",
        }
        gdf = gdf.rename(columns=columns)
        gdf["nitg_code"] = ""
        return gdf

    def list_locations(self) -> List[Tuple[str, int]]:
        """Return a list of locations that contain groundwater level dossiers, where
        each location is defines by a tuple of length 2: bro-id and tube_id"""
        oc = self.oc
        locations = []
        mask = [not x.empty for x in oc["obs"]]
        for index in oc[mask].index:
            locations.append(tuple(oc.loc[index, ["monitoring_well", "tube_nr"]]))
        return locations

    def get_timeseries(self, gmw_id: str, tube_id: int, column="values") -> pd.Series:
        """Return a Pandas Series for the measurements at the requested bro-id and
        tube-id, im m. Return None when there are no measurements."""
        name = f"{gmw_id}_{tube_id}"
        columns = [self.value_column, self.qualifier_column]
        df = pd.DataFrame(self.oc.loc[name, "obs"][columns])
        return df
