# ruff: noqa: F401 D104
from gwdatalens.app.main import get_app, run_dashboard
from gwdatalens.app.settings import config
from gwdatalens.django_copy import copy_gwdatalens_to_django_app

from .version import __version__
