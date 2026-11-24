"""
imu_data.py

Reads the text files exported by Xsens MT Manager and finds the moments
when the robot stands still.

The file starts with comment lines ("// ..."), then a header line and one
line per sample:

  PacketCounter, SampleTimeFine, Acc_X, Acc_Y, Acc_Z,
  Gyr_X, Gyr_Y, Gyr_Z, Mag_X, Mag_Y, Mag_Z

  Acc  m/s^2, includes gravity (standing still: Acc_Z = +9.81)
  Gyr  rad/s, rotation rate around each axis
  Mag  magnetic field, in units of the earth field strength

Sensor axes (checked with the short run, see README):
  x = forward, y = left, z = up.
  So a positive Gyr_Z is a turn to the left, a negative one to the right.
"""

import numpy as np

import settings


def load_recording(path):
    """Returns a dictionary: column name -> numpy array, plus "time" in seconds."""
    with open(path) as file:
        lines = [line for line in file if line.strip() and not line.startswith("//")]
    names = lines[0].strip().split(",")
    values = np.array([[float(v) for v in line.split(",")] for line in lines[1:]])
    data = {name: values[:, i] for i, name in enumerate(names)}

    # SampleTimeFine counts in steps of 100 microseconds.
    data["time"] = (data["SampleTimeFine"] - data["SampleTimeFine"][0]) / 10000

    # Quick sanity check: no lost samples (the counter goes up by one).
    lost = np.sum(np.diff(data["PacketCounter"]) != 1)
    if lost:
        print(f"warning: {lost} gaps in {path}")
    return data


def moving_spread(values, half_window):
    """Standard deviation of the values around every sample."""
    spread = np.zeros(len(values))
    for i in range(len(values)):
        window = values[max(0, i - half_window): i + half_window + 1]
        spread[i] = window.std()
    return spread


def find_standstills(data):
    """
    Returns (is_still, blocks).
      is_still: True/False per sample
      blocks:   list of (first, end) sample indices of every standstill
                (end is one past the last sample, like Python slices)
    """
    shaking = moving_spread(data["Acc_Z"], settings.STILL_WINDOW)
    rotation = np.sqrt(data["Gyr_X"] ** 2 + data["Gyr_Y"] ** 2 + data["Gyr_Z"] ** 2)
    is_still = (shaking < settings.STILL_MAX_ACC_SPREAD) & (rotation < settings.STILL_MAX_ROTATION)

    # Group neighbouring "still" samples into blocks.
    blocks = []
    i = 0
    while i < len(is_still):
        if not is_still[i]:
            i += 1
            continue
        end = i
        while end < len(is_still) and is_still[end]:
            end += 1
        if end - i >= settings.STILL_MIN_SAMPLES:
            blocks.append((i, end))
        i = end

    # Very short calm moments don't count.
    is_still = np.zeros(len(is_still), bool)
    for first, end in blocks:
        is_still[first:end] = True
    return is_still, blocks
