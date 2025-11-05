# %%
import logging
import os

import hydropandas as hpd
import pandas as pd
import pastas as ps
import pastastore as pst
from pastastore.extensions import activate_hydropandas_extension
from tqdm.auto import tqdm

from gwdatalens.app.settings import config
from gwdatalens.app.src.data import PostgreSQLDataSource

# %%
hpd.util.get_color_logger("ERROR")
activate_hydropandas_extension()

logger = logging.getLogger("waitress")
logger.setLevel(logging.DEBUG)

ps.logger.setLevel(logging.ERROR)

# %%
name = config["pastastore"]["name"]
pastastore_path = config["pastastore"]["path"]


db = PostgreSQLDataSource(config["database"])

# %%
if name.endswith(".zip") and os.path.exists(pastastore_path / name):
    pstore = pst.PastaStore.from_zip(pastastore_path / name)
else:
    # conn = pst.ArcticDBConnector(name=name, uri=f"lmdb://{pastastore_path}")
    conn = pst.PasConnector(name=name, path=pastastore_path)
    pstore = pst.PastaStore(conn)
    print(pstore)

# %% load head time series into pastastore

no_metadata = []
too_short = []
ts_none = []

value_column = "calculated_value"  # or "field_value"

gdf = db.gmw_gdf.copy()

for name in tqdm(db.list_observation_wells_with_data(), desc="Read timeseries"):
    try:
        metadata = gdf.loc[name, :].to_dict()
    except KeyError:
        no_metadata.append(name)
        continue

    bro_id, tube_number = name.split("-")
    ts = db.get_timeseries(bro_id, tube_number)
    if ts.index.dtype == "O":
        ts.index = pd.to_datetime(ts.index, utc=True)
    ts.index = ts.index.tz_localize(None)

    if ts is None:
        ts_none.append((bro_id, tube_number))
        continue
    else:
        ts = ts.loc[:, value_column]

    if ts.index.size < 50:
        too_short.append((bro_id, tube_number))
        continue

    # drop dupes
    ts = ts.loc[~ts.index.duplicated(keep="first")]

    # drop nans
    pstore.add_oseries(ts.dropna(), name, metadata=metadata, overwrite=True)

print("No. of errors:", len(no_metadata) + len(too_short) + len(ts_none))

# %% add KNMI data

pstore.hpd.download_knmi_precipitation(tmin="1958-01-01")
pstore.hpd.download_knmi_evaporation(tmin="1958-01-01")

# %%

# %% build time series models
# %%

skipped_nobs = []
skipped_period = []
error_model = {}

tmintmax = pstore.get_tmin_tmax("oseries")
obsperiod = (
    tmintmax.diff(axis=1)
    .iloc[:, -1]
    .apply(lambda t: t.total_seconds() / (24 * 60**2 * 365))
)

for oname in tqdm(pstore.oseries_names):
    oseries, meta = pstore.get_oseries(oname, return_metadata=True)

    # if nobs[oname] < 50:
    if oseries.index.size < 50:
        skipped_nobs.append(oname)
        continue
    if obsperiod.loc[oname] < 2:
        skipped_period.append(oname)
        continue
    ml = ps.Model(oseries, metadata=meta)
    pstore.add_recharge(ml, rfunc=ps.Exponential)
    pstore.add_model(ml, overwrite=True)


# %% solve models


def two_step_solve(name):
    ml = pstore.get_model(name)
    ml.solve(report=False)
    nse0 = ml.stats.nse()
    ml.add_noisemodel(ps.ArNoiseModel())
    ml.solve(initial=False, report=False)
    nse1 = ml.stats.nse()
    pstore.add_model(ml, overwrite=True)
    return pd.Series([nse0, nse1], index=["nse0", "nse1"], name=name)


# %%
names = pstore.model_names  # solve all
r = pstore.apply("models", two_step_solve, names=names, parallel=True, max_workers=6)
