# %%
import logging
import pathlib as pl
import shutil

logger = logging.getLogger(__name__)


def copy_datalens_to_django_app(
    DJANGO_APP_PATH, DATALENS_PATH=pl.Path(__file__).parent
):
    logger.info("Copying GWDataLens to Django App...")
    # copy app to gwdatalens folder
    shutil.copytree(DATALENS_PATH / "app", DJANGO_APP_PATH / "gwdatalens" / "app")

    logger.info(" - copying assets")
    # copy assets to static/dash folder
    ASSETS = DJANGO_APP_PATH / "gwdatalens" / "app" / "assets"
    for file in ASSETS.iterdir():
        shutil.move(file, DJANGO_APP_PATH / "static" / "dash" / file.name)

    logger.info(" - copying locale")
    # move locale folder to static/dash folder
    LOCALE = DJANGO_APP_PATH / "gwdatalens" / "app" / "locale"
    shutil.move(LOCALE, DJANGO_APP_PATH / "static" / "dash" / "locale")

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
        "/home/david/github/bro-provincie-zeeland-git/bro_connector"
    )
    copy_datalens_to_django_app(DJANGO_APP_PATH)

# %%
