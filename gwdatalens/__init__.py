# ruff: noqa: F401 D104
from gwdatalens.app.config import config
from gwdatalens.app.main import get_app, run_dashboard
from gwdatalens.django_copy import copy_gwdatalens_to_django_app
from gwdatalens.version import __version__, show_versions
