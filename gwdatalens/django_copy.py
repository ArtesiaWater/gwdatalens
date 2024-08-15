# %%
import logging
import pathlib as pl
import shutil

logger = logging.getLogger(__name__)


def copy_gwdatalens_to_django_app(
    DJANGO_APP_PATH, DATALENS_PATH=pl.Path(__file__).parent
):
    logger.info("Copying GWDataLens to Django App...")
    # copy app to gwdatalens folder
    shutil.copytree(
        DATALENS_PATH / "app",
        DJANGO_APP_PATH / "gwdatalens" / "app",
        ignore=shutil.ignore_patterns(
            "__pycache__", ".cache", ".pi_cache", ".ruff_cache"
        ),
        dirs_exist_ok=True,
    )

    logger.info(" - copying assets")
    # copy assets to static/dash folder
    ASSETS = DATALENS_PATH / "assets"
    shutil.copytree(
        ASSETS,
        DJANGO_APP_PATH / "static" / "dash",
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
    (DJANGO_APP_PATH / "templates").mkdir(exist_ok=True)
    shutil.copy(
        DATALENS_PATH / "django" / "templates" / "dash.html",
        DJANGO_APP_PATH / "templates",
    )
    logger.info(f"Done! Copied GWDataLens to Django project in {DJANGO_APP_PATH}.")


# %%
if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    DJANGO_APP_PATH = pl.Path(
        "/home/david/github/bro-provincie-zeeland-12aug/bro_connector"
    )
    copy_gwdatalens_to_django_app(DJANGO_APP_PATH)

# %%
