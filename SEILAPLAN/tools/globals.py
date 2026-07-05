from enum import Enum, IntEnum


class PolesOrigin(Enum):
    """Describes how the pole data was derived."""

    SavedFile = 1  # User loaded a save file with pole data
    Optimization = 2  # Optimization algorithm calculated poles
    OnlyStartEnd = 3  # Only start and end pole  and maybe some fixed poles are defined


class ResultQuality(IntEnum):
    """Describes the quality of the calculated result."""

    # Optimization produced a complete cable line
    SuccessfulOptimization = 1
    # Cable line was recalculated after change in adjustment window
    SuccessfulRerun = 2
    # Cable line lifts off a pole
    CableLiftsOff = 3
    # Optimization was partially successful but cable line stops before end point
    LineNotComplete = 4
    # Optimization or rerun threw an unexpected error
    Error = 5
