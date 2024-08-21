from enum import Enum


class PolesOrigin(Enum):
    """Describes how the pole data was derived."""
    SavedFile = 1           # User loaded a save file with pole data
    Optimization = 2        # Optimization algorithm calculated poles
    OnlyStartEnd = 3        # Only start and end pole  and maybe some fixed poles are defined


class ResultQuality(Enum):
    """Describes the quality of the calculated result."""
    SuccessfulOptimization = 1      # Optimization produced a complete cable line
    SuccessfulRerun = 2             # Cable line was recalculated after change in adjustment window
    CableLiftsOff = 3               # Cable line lifts off a pole
    LineNotComplete = 4             # Optimization was partially successful but cable line stops before end point
    Error = 5                       # Optimization or rerun threw an unexpected error
