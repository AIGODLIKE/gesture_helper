"""Shared Blender-like neutral theme defaults (scene-linear RGBA)."""

# Panels / buttons
BACKGROUND = (0.045, 0.048, 0.052, 0.97)
OPERATOR_ACTIVE = (0.035, 0.23, 0.52, 1.0)
CHILD_ACTIVE = (0.035, 0.23, 0.52, 1.0)

# Bool: Blender option blue when on, neutral when off.
BOOL_TRUE = (0.035, 0.23, 0.52, 1.0)
BOOL_FALSE = (0.045, 0.048, 0.052, 0.97)

# Number fields: neutral rows with restrained progress accents.
INT = (0.045, 0.048, 0.052, 0.97)
INT_ACTIVE = (0.055, 0.20, 0.42, 0.92)
FLOAT = (0.045, 0.048, 0.052, 0.97)
FLOAT_ACTIVE = (0.045, 0.24, 0.42, 0.92)

TEXT_DEFAULT = (0.78, 0.80, 0.83, 1.0)
TEXT_ACTIVE = (1.0, 1.0, 1.0, 1.0)

TRAJECTORY_MOUSE = (0.12, 0.38, 0.72, 0.72)
TRAJECTORY_GESTURE = (0.08, 0.48, 0.88, 1.0)

DIVIDING_LINE = (0.18, 0.19, 0.21, 1.0)
OUTLINE = (0.18, 0.19, 0.21, 0.92)
OUTLINE_ACTIVE = (0.16, 0.42, 0.78, 0.95)

# Element state accents. The row background remains neutral.
STATUS_DISABLED = (0.24, 0.25, 0.27, 1.0)
STATUS_WARNING = (0.72, 0.30, 0.035, 1.0)
STATUS_ERROR = (0.62, 0.055, 0.045, 1.0)

# BPU-only accents (still scene-linear)
BACKGROUND_HOVER = (0.035, 0.23, 0.52, 0.92)
BACKGROUND_PROPERTY_HOVER = (0.035, 0.23, 0.52, 0.76)
BACKGROUND_PROPERTY = BACKGROUND
BACKGROUND_ALERT = STATUS_ERROR
SEPARATOR = (0.24, 0.25, 0.27, 1.0)
TEXT_ALERT = (1.0, 0.24, 0.20, 1.0)

OUTLINE_WIDTH = 1
