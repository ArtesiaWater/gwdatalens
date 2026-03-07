# %%
import logging
import os
from pathlib import Path

import hydropandas as hpd
import pandas as pd
import pastas as ps
import pastastore as pst
from pastastore.extensions import activate_hydropandas_extension
from tqdm.auto import tqdm

from gwdatalens.app.config import config
from gwdatalens.app.src.data import PostgreSQLDataSource

# %%
hpd.util.get_color_logger("ERROR")
activate_hydropandas_extension()

logger = logging.getLogger("waitress")
logger.setLevel(logging.DEBUG)

ps.logger.setLevel(logging.ERROR)

# %%
pastastore_name = config["pastastore"]["name"]
pastastore_path = config["pastastore"]["path"]
root = Path("../")

db = PostgreSQLDataSource(config=config.get_database_config())

# %%
if pastastore_name.endswith(".zip") and os.path.exists(
    pastastore_path / pastastore_name
):
    pstore = pst.PastaStore.from_zip(pastastore_path / pastastore_name)
else:
    # conn = pst.ArcticDBConnector(name=name, uri=f"lmdb://{pastastore_path}")
    conn = pst.PasConnector(name=pastastore_name, path=root / pastastore_path)
    pstore = pst.PastaStore(conn)
    print(pstore)

# %% load head time series into pastastore

no_metadata = []
too_short = []
ts_none = []

gdf = db.gmw_gdf.copy()

for wid in tqdm(db.list_observation_wells_with_data.index, desc="Read timeseries"):
    try:
        metadata = gdf.loc[wid, :]
        if isinstance(metadata, pd.DataFrame):
            raise ValueError("Duplicate entries in metadata table")
        metadata = metadata.to_dict()
    except KeyError:
        no_metadata.append(wid)
        continue

    if isinstance(metadata["x"], dict):
        raise Exception(wid)

    display_name = metadata["display_name"]
    ts = db.get_timeseries(wid, columns=db.value_column)

    if ts is None:
        ts_none.append(display_name)
        continue

    if ts.dtype == "O":
        ts = pd.to_numeric(ts, errors="coerce").dropna()

    if ts.index.size < 50:
        too_short.append(display_name)
        continue

    # drop dupes
    if ts.index.duplicated().any():
        logger.warning("Dropping duplicated timestamps for well %s", wid)
        ts = ts.loc[~ts.index.duplicated(keep="first")]

    # drop nans
    pstore.add_oseries(
        ts.dropna(),
        display_name,
        metadata=metadata,
        overwrite=True,
    )

print("No. of errors:", len(no_metadata) + len(too_short) + len(ts_none))

# %% add KNMI data

pstore.hpd.download_knmi_precipitation(tmin="1958-01-01")
pstore.hpd.download_knmi_evaporation(tmin="1958-01-01")

# %% build time series models

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

solve_adjustments = {
    "GMW48F000190-001": {"tmin": "1975"},
    "GMW42H000186-003": {"tmax": "2004"},
    "GMW42H000195-001": {"tmax": "2002"},
    "GMW48A000132-002": {"tmax": "2002"},
    "GMW43C000271-001": {"tmax": "2015"},
    "GMW48H000308-002": {"tmin": "1976"},
    "GMW49C000146-002": {"tmax": "2002"},
    "GMW54F000065-002": {"tmax": "2024"},
    "GMW42E000276-001": {"tmax": "2011"},
    "GMW42H000195-003": {"tmax": "2000"},
    "GMW48H000308-001": {"tmin": "1976"},
    "GMW48F000190-002": {"tmin": "1975"},
    "GMW48F000080-003": {"tmin": "1994", "tmax": "2008"},
    "GMW42D000486-001": {"tmax": "2025"},
    "GMW42H000047-003": {"tmax": "1998"},
    "GMW48B000181-003": {"tmax": "2002"},
    "GMW42B000144-001": {"tmax": "2014"},
    "GMW48F000236-001": {"tmax": "2004"},
}


def two_step_solve(name):
    ml = pstore.get_model(name)
    if name in solve_adjustments:
        kwargs = solve_adjustments[name]
    else:
        kwargs = {}
    ml.solve(report=False, **kwargs)
    nse0 = ml.stats.nse()
    ml.add_noisemodel(ps.ArNoiseModel())
    ml.solve(initial=False, report=False, **kwargs)
    nse1 = ml.stats.nse()
    pstore.add_model(ml, overwrite=True)
    return pd.Series([nse0, nse1], index=["nse0", "nse1"], name=name)


# %%
weird_data = [
    "GMW42B000155-001",  # flipped series?
    "GMW42E000993-001",  # flipped series?
    "GMW42E000994-001",  # flipped series?
    "GMW42B000154-001",  # flipped series?
    "GMW42B000153-001",  # flipped series?
    "GMW42E000992-001",  # flipped series?
    "GMW49D000060-004",  # missende invloed onttrekkingen
    "GMW48F000075-001",  # missende invloed onttrekking, moeilijke reeks
    "GMW49D000120-005",  # missende invloed onttrekking?
    "GMW43C000348-001",  # vreemde reeks
    "GMW48E000128-004",  # getijde?
    "GMW42H000186-001",  # te kort
    "GMW48E000128-002",  # getijde?
    "GMW48E000128-002",  # getijde?
    "GMW48E000128-002",  # hele vreemde reeks...
    "GMW54F000093-002",  # hele vreemde reeks...
    "GMW42B000114-001",  # missende invloed, maar wat?
    "GMW49D000120-004",  # missende invloed onttrekkingen
    "GMW49D000114-005",  # missende invloed onttrekkingen
    "GMW43C000380-002",  # te weinig data
    "GMW48F000075-002",  # missende invloed onttrekking, moeilijke reeks
    "GMW48B000061-001",  # getijde?
    "GMW49D000060-003",  # missende invloed onttrekking, moeilijke reeks
    "GMW49D000114-004",  # missende invloed onttrekking, moeilijke reeks
    "GMW54E000285-001",  # vreemde reeks
    "GMW49D000114-002",  # missende invloed onttrekking, moeilijke reeks
    "GMW49D000120-003",  # missende  invloed onttrekking, moeilijke reeks
    "GMW48E000128-003",  # getijde?
    "GMW55A000340-001",  # vreemde reeks
    "GMW48E000218-003",  # getijde?
    "GMW42G000063-002",  # moeilijke reeks?
    "GMW49A000255-001",  # te kort
    "GMW48B000061-003",  # getijde?
    "GMW48B000061-002",  # getijde?
    "GMW48E000128-001",  # getijde?
    "GMW49C000107-002",  # getijde?
    "GMW42G000063-003",  # getijde?
    "GMW49C000107-001",  # moeilijke reeks?
]

for name in weird_data:
    try:
        pstore.del_model(name)
    except FileNotFoundError:
        pass

# %%
names = pstore.model_names  # solve all
r = pstore.apply("models", two_step_solve, names=names, parallel=True)

r.T.to_csv("solve_stats.csv")
# %%

# inspect badly performing models
i = 0
name = r.T.sort_values("nse1").index[i]
ml = pstore.models[name]
# ml.solve(tmax="2004")
ml.plots.results()
print(name, "\n", r.T.loc[name])

# %%
