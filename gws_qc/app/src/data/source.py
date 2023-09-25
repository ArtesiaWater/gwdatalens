from typing import List
import pandas as pd


class DataSource:
    def __init__(self):
        # init connection to database OR just read in some data from somewhere
        pass

    def list_locations(self) -> List:
        return []

    def get_timeseries(self, name: str) -> pd.Series:
        return pd.Series()
