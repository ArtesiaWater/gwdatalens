# %%
import logging
import pathlib as pl
import shutil

logger = logging.getLogger(__name__)


def copy_gwdatalens_to_django_app(
    DJANGO_APP_PATH, DATALENS_PATH=pl.Path(__file__).parent
):
    """Copies the GWDataLens application to a specified Django application path.

    Parameters
    ----------
    DJANGO_APP_PATH : str or pathlib.Path
        The path to the Django application where the GWDataLens app and assets will be
        copied.
    DATALENS_PATH : pathlib.Path, optional
        The path to the GWDataLens source directory. Defaults to the parent directory
        of the current file.

    Notes
    -----
    - Copies the GWDataLens app to the `gwdatalens` folder within the specified Django
      app path.
    - Copies assets to the `static/dash` folder within the specified Django app path.
    - Copies Django-specific files to the `gwdatalens` folder within the specified
      Django app path.
    - Copies the Dash template to the `templates` folder within the specified Django
      app path.

    Raises
    ------
    shutil.Error
        If an error occurs during the copying process.
    """
    if isinstance(DJANGO_APP_PATH, str):
        DJANGO_APP_PATH = pl.Path(DJANGO_APP_PATH)

    logger.info("Copying GWDataLens to Django App...")
    # copy app to gwdatalens folder
    shutil.copytree(
        DATALENS_PATH / "app",
        DJANGO_APP_PATH / "gwdatalens" / "app",
        ignore=shutil.ignore_patterns(
            "__pycache__",
            ".cache",
            ".pi_cache",
            ".ruff_cache",
            "database.toml",
            "*.zip",
        ),
        dirs_exist_ok=True,
    )

    logger.info(" - copying assets")
    # copy assets to static/dash folder
    ASSETS = DATALENS_PATH / "assets"
    shutil.copytree(
        ASSETS,
        DJANGO_APP_PATH / "static" / "dash",
        ignore=shutil.ignore_patterns(
            ".mapbox_access_token",
        ),
        dirs_exist_ok=True,
    )

    # copy django files to gwdatalens folder
    logger.info(" - copying django files")
    DJANGO_FILES = [
        f for f in (DATALENS_PATH / "django").iterdir() if f.suffix == ".py"
    ]
    for f in DJANGO_FILES:
        shutil.copy(f, DJANGO_APP_PATH / "gwdatalens")

    # copy dash template to templates folder
    logger.info(" - copying dash template")
    shutil.copy(
        DATALENS_PATH / "django" / "templates" / "dash.html",
        DJANGO_APP_PATH / "templates",
    )
    logger.info(f"Done! Copied GWDataLens to Django project in '{DJANGO_APP_PATH}/'.")


# %%
if __name__ == "__main__":
    logging.basicConfig()
    logger.setLevel(logging.INFO)
    # david
    DJANGO_APP_PATH = pl.Path("/home/david/github/bro-connector/bro_connector")
    # provincie zeeland
    # DJANGO_APP_PATH = pl.Path("C:/BRO/bro-provincie-zeeland/bro_connector")
    copy_gwdatalens_to_django_app(DJANGO_APP_PATH)

# %%
