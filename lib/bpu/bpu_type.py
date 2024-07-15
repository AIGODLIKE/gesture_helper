from enum import Enum


class BPUType(Enum):
    ROW = 10
    COLUMN = 20
    BOX = 30
    SPLIT = 40
    LABEL = 50
    PROPERTY = 60
    SEPARATOR = 70
    OPERATOR = 200
