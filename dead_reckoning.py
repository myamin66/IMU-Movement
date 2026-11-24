"""
dead_reckoning.py

Turns the IMU samples into a path:

  heading  = integral of the yaw rate (Gyr_Z)
  speed    = integral of the forward acceleration (Acc_X)
  position = integral of speed in the heading direction

Integrating raw sensor values drifts away quickly, so two simple fixes
are used:
  * gyro bias: measured while the robot stands still and subtracted
  * zero-velocity update: whenever the robot stands still its speed is
    known to be 0, so the speed drift between two stops can be removed
"""

import numpy as np

import settings

DT = settings.SAMPLE_TIME


def yaw_angle(data, is_still):
    """
    Heading change since the start, in radians (left turn = positive).
    Even standing still the gyro shows a small rate (about 0.12 deg/s
    here). Over 3 minutes that alone would add more than 20 degrees, so
    the average rate during the standstills is subtracted first.
    """
    bias = data["Gyr_Z"][is_still].mean()
    return np.cumsum((data["Gyr_Z"] - bias) * DT), bias


def speed_between_stops(data, blocks):
    """
    Forward speed (m/s, negative = reversing) from the x acceleration.

    Between two standstills:
      1. When the robot stands, Acc_X is not 0 but a small offset: the
         ground is not perfectly flat, so a bit of gravity leaks into the
         x axis (plus a tiny sensor bias). This offset is measured at the
         stop before and the stop after, and a straight line between the
         two is subtracted.
      2. The rest is added up (integrated) to get the speed.
      3. At the next stop the speed must be 0 again. Whatever is left is
         drift; it is removed by subtracting a straight line that grows
         from 0 to that leftover value.
    Returns the speed per sample and a list of what was removed per segment.
    """
    ax = data["Acc_X"]
    speed = np.zeros(len(ax))
    report = []
    for (stop_a, end_a), (stop_b, end_b) in zip(blocks[:-1], blocks[1:]):
        first, last = end_a, stop_b          # samples while moving
        offset_before = ax[stop_a:end_a].mean()
        offset_after = ax[stop_b:end_b].mean()
        offset = np.linspace(offset_before, offset_after, last - first)

        moving_speed = np.cumsum((ax[first:last] - offset) * DT)
        leftover = moving_speed[-1]
        moving_speed -= np.linspace(0, leftover, last - first)

        speed[first:last] = moving_speed
        report.append((data["time"][first], data["time"][last], leftover))
    return speed, report


def path_from(speed, yaw, start_heading):
    """
    East/north position (metres) of every sample.
    start_heading: compass direction of the robot's x axis at the start
    (degrees, 0 = north, 90 = east). The gyro yaw turns left-positive,
    the compass turns right-positive, hence the minus.
    """
    heading = np.radians(start_heading) - yaw
    east = np.cumsum(speed * DT * np.sin(heading))
    north = np.cumsum(speed * DT * np.cos(heading))
    return np.column_stack([east, north])


def samples_between(time, phase):
    start, end = phase
    return (time >= start) & (time < end)


def closed_loop_speeds(time, yaw, speed):
    """
    The long middle part of the long run (105 s) has no standstill, and
    integrating the acceleration over such a long time drifts badly
    (the speed climbs to 3.4 m/s, which a robot like this doesn't do).

    The robot came back to where it started (magnetometer.py shows this),
    so the path must close. With one constant speed on the way out and
    one on the way back (and their average in the U-turn), the end point
    is a simple linear function of these two speeds:

        end = known part + speed_out * (sum of out directions)
                         + speed_back * (sum of back directions)

    Two equations (east = 0, north = 0) and two unknowns, so numpy can
    solve them directly. The heading doesn't matter here, it only rotates
    the whole picture, so the gyro yaw is used as it is.
    Returns the new speed array and the two speeds.
    """
    out = samples_between(time, settings.LONG_OUT_LEG)
    u_turn = samples_between(time, settings.LONG_U_TURN)
    back = samples_between(time, settings.LONG_BACK_LEG)
    on_spot = samples_between(time, settings.LONG_TURN_ON_SPOT)

    speed = speed.copy()
    speed[on_spot] = 0.0                       # turning on the spot
    known = ~(out | u_turn | back)

    x_dir, y_dir = np.cos(yaw) * DT, np.sin(yaw) * DT
    known_end = np.array([np.sum(speed[known] * x_dir[known]),
                          np.sum(speed[known] * y_dir[known])])
    out_column = np.array([x_dir[out].sum() + x_dir[u_turn].sum() / 2,
                           y_dir[out].sum() + y_dir[u_turn].sum() / 2])
    back_column = np.array([x_dir[back].sum() + x_dir[u_turn].sum() / 2,
                            y_dir[back].sum() + y_dir[u_turn].sum() / 2])
    speed_out, speed_back = np.linalg.solve(np.column_stack([out_column, back_column]),
                                            -known_end)

    speed[out] = speed_out
    speed[back] = speed_back
    speed[u_turn] = (speed_out + speed_back) / 2
    return speed, speed_out, speed_back


def compass_direction(lat1, lon1, lat2, lon2):
    """Compass direction (degrees) from point 1 to point 2 (short distances)."""
    east = (lon2 - lon1) * np.cos(np.radians(lat1)) * 111320
    north = (lat2 - lat1) * 110540
    return np.degrees(np.arctan2(east, north)) % 360


def start_heading_from_footway(time, yaw):
    """
    The IMU alone can't tell which way the robot faced at the start
    (the magnetometer can, but only to about +-10 degrees here). The
    first leg is 38 m long and ends at the pavement, exactly like the
    asphalt footway that leads from the entrance to Bogdanfy utca.
    So the start heading is chosen to make the first leg's average
    direction equal to the footway's direction.
    """
    footway = compass_direction(settings.ENTRANCE_LAT, settings.ENTRANCE_LON,
                                settings.FOOTWAY_END_LAT, settings.FOOTWAY_END_LON)
    first_leg = samples_between(time, settings.LONG_FIRST_LEG)
    turned = np.degrees(yaw[first_leg]).mean()     # negative = turned right
    return (footway + turned) % 360, footway
