from pathlib import Path

import tomli

# %% load settings
DATALENS_APP_PATH = Path(__file__).parent
with open(DATALENS_APP_PATH / "config.toml", "rb") as f:
    config = tomli.load(f)
    settings = config["settings"]

# %% set paths accordingly

if settings["DJANGO_APP"]:
    ASSETS_PATH = PASSETS_PATH = Path(__file__).parent.parent.parent / "static" / "dash"
else:
    ASSETS_PATH = DATALENS_APP_PATH / "assets"

LOCALE_PATH = ASSETS_PATH / "locale"
CUSTOM_CSS_PATH = ASSETS_PATH / "custom.css"
MAPBOX_ACCESS_TOKEN = ASSETS_PATH / ".mapbox_access_token"
