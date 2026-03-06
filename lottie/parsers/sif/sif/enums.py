import enum


class Smooth(enum.Enum):
    NearestNeighbour = 0
    Linear = 1
    Cosine = 2
    Spline = 3
    Cubic = 4
