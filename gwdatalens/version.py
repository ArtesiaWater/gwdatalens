# ruff: noqa: D100
from importlib import import_module, metadata
from platform import python_version

__version__ = "0.3.0"


def show_versions(optional=True) -> None:
    """Print the version of dependencies.

    Parameters
    ----------
    optional : bool, optional
        Print the version of optional dependencies, by default False
    """
    msg = (
        f"GWDataLens version  : {__version__}\n\n"
        f"Python version      : {python_version()}\n"
        f"Plotly version      : {metadata.version('plotly')}\n"
        f"Dash version        : {metadata.version('dash')}\n"
        f"Pastas version      : {metadata.version('pastas')}\n"
        f"Pastastore version  : {metadata.version('pastastore')}\n"
        f"Hydropandas version : {metadata.version('hydropandas')}\n"
    )
    if optional:
        msg += "\ndjango_plotly_dash version : "
        try:
            import_module("django_plotly_dash")
            msg += f"{metadata.version('django_plotly_dash')}"
        except ImportError:
            msg += "Not Installed"

    print(msg)
