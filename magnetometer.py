"""
magnetometer.py

The magnetometer is used for two checks, not for the path itself:

1. Compass heading. The robot's own metal and motors add a constant
   magnetic field ("hard iron"), which moves the measured horizontal
   field (Mag_X, Mag_Y) off-centre. When the robot turns a full circle,
   the measured points lie on a circle around that offset. A circle fit
   finds the offset, and after removing it, atan2 gives the heading.

2. "Magnetic fingerprint". Near buildings, cars and street lamps the
   field strength differs from place to place by several percent. If
   the field at the end of a run is the same as at the start, the robot
   is very likely standing at the same spot again.
"""

import numpy as np

import settings


def fit_circle(x, y):
    """
    Least-squares circle through the points: x^2 + y^2 = 2ax + 2by + c.
    That equation is linear in a, b and c, so one lstsq call solves it.
    Returns the centre (a, b) and the radius.
    """
    matrix = np.column_stack([2 * x, 2 * y, np.ones_like(x)])
    a, b, c = np.linalg.lstsq(matrix, x ** 2 + y ** 2, rcond=None)[0]
    return np.array([a, b]), np.sqrt(c + a ** 2 + b ** 2)


def compass_heading(data, centre):
    """
    Heading of the robot's x axis in degrees (0 = north, 90 = east).
    With x forward and y left, the earth field (pointing north) is seen as
    Mag_X = B cos(heading), Mag_Y = B sin(heading). Magnetic north is
    turned into true north with the declination.
    """
    mx = data["Mag_X"] - centre[0]
    my = data["Mag_Y"] - centre[1]
    return (np.degrees(np.arctan2(my, mx)) + settings.DECLINATION) % 360


def field_at_stops(data, blocks):
    """Average field vector and strength during every standstill."""
    rows = []
    for first, end in blocks:
        vector = np.array([data[k][first:end].mean() for k in ("Mag_X", "Mag_Y", "Mag_Z")])
        rows.append((data["time"][first], data["time"][end - 1], vector, np.linalg.norm(vector)))
    return rows
