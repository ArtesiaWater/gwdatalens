"""Application constants and configuration values.

Centralizes magic strings and numbers used throughout the application.
"""

from pathlib import Path

from gwdatalens.app.src.components import ids


class ConfigDefaults:
    """Default configuration values."""

    DEFAULT_TAB = ids.TAB_OVERVIEW
    STARTUP_LOG_LEVEL = "INFO"

    # Series constraints
    MAX_WELLS_SELECTION = 50

    # Display defaults
    DEFAULT_MAP_STYLE = "outdoors"
    # public styles: "carto-positron", "open-street-map", "stamen-terrain",
    # "basic", "streets", "light", "dark", "satellite", "satellite-streets"

    # Caching
    CACHE_TIMEOUT = 3600  # 1 hour

    # Date/Time
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class ColumnNames:
    """Column names in DataFrames and database queries."""

    # Geographic/Location columns
    X = "x"
    Y = "y"
    LATITUDE = "latitude"
    LONGITUDE = "longitude"
    GEOMETRY = "geometry"

    # Well/tube columns
    WELL_STATIC_ID = "well_static_id"
    WELL_CODE = "well_code"
    WELL_NITG_CODE = "nitg_code"
    BRO_ID = "bro_id"
    LOCATION_NAME = "location_name"

    TUBE_STATIC_ID = "tube_static_id"
    TUBE_NUMBER = "tube_number"
    DISPLAY_NAME = "display_name"

    # Elevation/depth columns
    GROUND_LEVEL_POSITION = "ground_level_position"
    TUBE_TOP_POSITION = "tube_top_position"
    SCREEN_TOP = "screen_top"
    SCREEN_BOT = "screen_bot"
    SCREEN_LENGTH = "screen_length"
    PLAIN_TUBE_PART_LENGTH = "plain_tube_part_length"

    # Time series columns
    TIMESTAMP = "timestamp"
    STATUS_QUALIFIER = "status_qualifier"
    CORRECTION_QUALIFIER = "correction_qualifier"
    UNIT = "unit"
    NUMBER_OF_OBSERVATIONS = "metingen"

    # Internal columns
    INTERNAL_ID = "internal_id"
    ID = "id"

    # Observation/correction columns
    FIELD_VALUE = "field_value"
    CALCULATED_VALUE = "calculated_value"
    VALUE_TO_BE_CORRECTED = "value_to_be_corrected"

    # QC results & corrections
    FLAGGED = "flagged"
    VALUE = "value"
    COMMENT = "comment"
    INCOMING_STATUS_QUALITY_CONTROL = "incoming_status_quality_control"
    STATUS_QUALITY_CONTROL = "status_quality_control"
    CATEGORY = "category"
    DATETIME = "datetime"
    CORRECTED_VALUE = "corrected_value"


class QCDefaults:
    """Default QC (TRAVAL) configuration values."""

    # always show pastas model results in figures, even if pastas rule
    # is not included in Traval RuleSet.
    ALWAYS_SHOW_PASTAS_MODEL = True

    THRESHOLD = 0.0
    WINDOW_SIZE = 7

    # spike rule
    SPIKE_THRESHOLD = 0.40
    SPIKE_TOLERANCE = 0.20
    SPIKE_MAX_GAP = "30D"

    # flat signal rule
    FLAT_SIGNAL_WINDOW = 100
    FLAT_SIGNAL_MIN_OBS = 5
    FLAT_SIGNAL_STD_THRESHOLD = 2e-2

    # pastas rule
    PASTAS_CI = 0.99
    PASTAS_MIN_CI = 0.05  # minimum interval when mean prediction interval < min_ci
    PASTAS_CI_SMOOTHFREQ = "30D"
    PASTAS_CI_DIR = Path(".pi_cache/")


class QCFlags:
    """Quality control constants."""

    # flags
    FLAGGED = 1
    NOT_FLAGGED = 0
    SKIP = -1
    # QC status labels in en and nl
    UNKNOWN = "unknown"
    UNDECIDED = "undecided"
    UNRELIABLE = "unreliable"
    RELIABLE = "reliable"
    ONBEKEND = "onbekend"
    ONBESLIST = "onbeslist"
    AFGEKEURD = "afgekeurd"
    GOEDGEKEURD = "goedgekeurd"
    BRO_STATUS_TRANSLATION_NL_TO_EN = {
        # nl --> en
        ONBEKEND: UNKNOWN,
        ONBESLIST: UNDECIDED,
        AFGEKEURD: UNRELIABLE,
        GOEDGEKEURD: RELIABLE,
        # en --> en (identity)
        UNKNOWN: UNKNOWN,
        UNDECIDED: UNDECIDED,
        UNRELIABLE: UNRELIABLE,
        RELIABLE: RELIABLE,
    }
    BRO_STATUS_TRANSLATION_EN_TO_NL = {
        # en --> nl
        UNKNOWN: ONBEKEND,
        UNDECIDED: ONBESLIST,
        UNRELIABLE: AFGEKEURD,
        RELIABLE: GOEDGEKEURD,
        # nl --> nl (identity)
        ONBEKEND: ONBEKEND,
        ONBESLIST: ONBESLIST,
        AFGEKEURD: AFGEKEURD,
        GOEDGEKEURD: GOEDGEKEURD,
    }


class UI:
    """UI-related constants."""

    # Default spacing
    MARGIN_TOP = 10
    MARGIN_BOTTOM = 10

    # Compact spacing
    MARGIN_ZERO = 0
    MARGIN_TOP_COMPACT = 5
    MARGIN_BOTTOM_COMPACT = 5

    # Large spacing
    MARGIN_TOP_LARGE = 15
    MARGIN_BOTTOM_LARGE = 20

    # Button colors
    DEFAULT_BUTTON_COLOR = "#006f92"
    CLEAR_BUTTON_COLOR = "darkred"


class PlotConstants:
    """Plot color constants."""

    # overview map colors
    OVERVIEW_MAP_MARKER_COLOR = "black"
    OVERVIEW_MAP_MARKER_SIZE = 6
    OVERVIEW_MAP_MARKER_OPACITY = 0.6
    OVERVIEW_MAP_MARKER_SYMBOL = "circle"
    OVERVIEW_MAP_SELECTED_MARKER_COLOR = "red"
    OVERVIEW_MAP_SELECTED_MARKER_SIZE = 12
    OVERVIEW_MAP_SELECTED_MARKER_OPACITY = 1.0
    OVERVIEW_MAP_SELECTED_MARKER_SYMBOL = "circle"
    OVERVIEW_MAP_UNSELECTED_MARKER_OPACITY = 0.5
    OVERVIEW_MAP_NO_DATA_MARKER_COLOR = "orange"
    OVERVIEW_MAP_NO_DATA_MARKER_SIZE = 7
    OVERVIEW_MAP_NO_DATA_MARKER_OPACITY = 1.0
    OVERVIEW_MAP_SELECTED_NO_DATA_MARKER_OPACITY = 1.0
    OVERVIEW_MAP_SELECTED_NO_DATA_MARKER_COLOR = "red"
    OVERVIEW_MAP_SELECTED_NO_DATA_MARKER_SIZE = 12

    # status colors
    STATUS_RELIABLE = "green"  # goedgekeurd
    STATUS_UNDECIDED = "orange"  # onbeslist
    STATUS_UNRELIABLE = "red"  # afgekeurd
    STATUS_UNKNOWN = "gray"  # onbekend
    STATUS_NO_QUALIFIER = "#636EFA"

    # table cell background colors (translucent)
    STATUS_RELIABLE_BG = "#d4edda"  # light green
    STATUS_UNRELIABLE_BG = "#f8d7da"  # light red
    STATUS_UNDECIDED_BG = "#fff3cd"  # light amber
    STATUS_UNKNOWN_BG = "#e2e3e5"  # light grey

    # control observations
    CONTROL_OBS_COLOR = "red"
    CONTROL_OBS_SIZE = 7

    # pastas ci
    CI_FILL_COLOR = "rgba(100,149,237,0.1)"
    CI_LINE_COLOR = "rgba(100,149,237,0.35)"
    SIM_LINE_COLOR = "cornflowerblue"


class UnitConversion:
    CM_TO_M = 0.01
    M_TO_CM = 100.0
