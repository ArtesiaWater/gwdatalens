# %%
import logging
from pathlib import Path

import pandas as pd
from tqdm.auto import tqdm

from gwdatalens.app.config import config
from gwdatalens.app.src.data import PostgreSQLDataSource

logging.getLogger("gwdatalens").setLevel("WARNING")

# %%

datadir = Path("../../krw_trendanalyse/_projects/tra/data/")

dfkrw = pd.read_excel(
    datadir / "Bijlage 1. KRW resultaten 20200113 gefilterd en gemarkeerd.xlsx",
    sheet_name="resultaten",
    index_col=[0, 1],
)
mask = dfkrw["Provincie"] == "Zeeland"
dfkrw_zeeland = dfkrw.loc[mask]

# %%
db = PostgreSQLDataSource(
    config=config.get_database_config(),
    use_cache=config.get("USE_LRU_CACHE"),
    max_cache_size=config.get("MAX_CACHE_SIZE"),
    cache_timeout=config.get("CACHE_TIMEOUT"),
)


gdf = db._build_gmw_gdf(include_krw_lichaam=True)
db._gmw_gdf_store = gdf

# %%

use_metadata_cols = [
    "display_name",
    "bro_id",
    "nitg_code",
    "well_code",
    "tube_number",
    "ground_level_position",
    "tube_top_position",
    "plain_tube_part_length",
    "screen_length",
    "screen_top",
    "screen_bot",
    "metingen",
    "controlemetingen",
    "first_observation_date",
    "last_observation_date",
    "x",
    "y",
    "lon",
    "lat",
    "krw_lichaam",
    "id",
    "well_static_id",
    "tube_static_id",
    "tube_dynamic_id",
]

use_time_series_cols = [
    "field_value",
    "field_value_unit",
    "calculated_value",
    "status_quality_control",
    "observation_type",
]

metadata = []

missing = []

for idx in tqdm(dfkrw_zeeland.index):
    nitg, tube = idx
    sel = db.query_gdf(nitg_code=nitg, tube_number=tube)
    if sel.empty:
        missing.append(idx)
        continue
    metadata.append(sel.loc[:, use_metadata_cols])
    ts = db.get_timeseries(sel.index[0], columns=tuple(use_time_series_cols))
    if ts.empty:
        missing.append(idx)
        continue
    ts.to_parquet(f"krw/{ts.index.name}.parquet", compression="snappy")

pd.concat(metadata, axis=0).to_parquet("krw/metadata.parquet", compression="snappy")

with open("krw/missing.txt", "w") as f:
    for idx in missing:
        f.write(f"{idx}\n")

# %%
