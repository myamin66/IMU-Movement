"""
settings.py

All fixed numbers of the project in one place. Times are in seconds,
angles in degrees, distances in metres.
"""

# Input files (copies of the two recordings from the professor)
SHORT_RUN_FILE = "data/short_run.txt"   # MT_0080001528_006-000.txt
LONG_RUN_FILE = "data/long_run.txt"     # MT_0080001528_004-000.txt
OSM_FILE = "data/osm_clc_area.json"     # OpenStreetMap data around the CLC

# The IMU sends 10 samples per second.
SAMPLE_TIME = 0.1


# Standstill detection
#
# When the robot stands, the accelerometer only sees gravity and a little
# noise (spread about 0.01 m/s^2). As soon as the wheels turn, the robot
# shakes and the vertical acceleration jumps around by 0.2 - 1.5 m/s^2.
# So a calm Acc_Z together with a calm gyro means "standing still".
STILL_WINDOW = 5            # samples on each side (= +-0.5 s)
STILL_MAX_ACC_SPREAD = 0.05 # m/s^2, standard deviation of Acc_Z in the window
STILL_MAX_ROTATION = 0.02   # rad/s, total gyro rate
STILL_MIN_SAMPLES = 5       # shorter calm moments are ignored (0.5 s)


# Where the robot started (from OpenStreetMap)
#
# Main entrance of the CLC building (EIT Digital Budapest CLC, ELTE
# Bogdanfy utca hall), OSM node 4803720391.
ENTRANCE_LAT = 47.4741372
ENTRANCE_LON = 19.0579051
# End of the asphalt footway that leads from the entrance south to the
# pavement of Bogdanfy utca (OSM way 487995117).
FOOTWAY_END_LAT = 47.4737677
FOOTWAY_END_LON = 19.0579976

# Magnetic declination in Budapest (2026): magnetic north is about
# 6 degrees east of true north. Only used for the magnetometer check.
DECLINATION = 6.0

# Part of the map shown in the figures: metres (west, east, south, north)
# of the entrance.
MAP_VIEW = (-95, 55, -70, 45)


# Phases of the long run
#
# Read off the plots of speed, yaw rate and vibration (figures/long_run_signals.png).
# The first leg starts and ends with a standstill, so its speed can be found
# by integrating the acceleration (see dead_reckoning.py). The long middle
# part has no standstill for 105 s, so there I use the professor's model
# for this robot: speed up briefly, then roughly constant speed.
LONG_FIRST_LEG = (20.0, 45.4)     # entrance -> pavement
LONG_TURN_ON_SPOT = (45.9, 51.0)  # turns right on the spot, speed 0
LONG_OUT_LEG = (51.0, 101.0)      # west along the pavement
LONG_U_TURN = (101.0, 114.5)      # wide right U-turn
LONG_BACK_LEG = (114.5, 155.5)    # back along the front of the building

# Short description of every phase, used for the figures and the printout.
LONG_RUN_STORY = [
    (0.0, 20.0, "stands at the entrance"),
    (20.0, 45.4, "drives south down the footway"),
    (45.4, 51.0, "stops, turns right on the spot"),
    (51.0, 101.0, "drives west along the pavement"),
    (101.0, 114.5, "U-turn to the right"),
    (114.5, 156.1, "drives back along the building"),
    (156.1, 168.1, "turns right on the spot"),
    (168.1, 175.6, "stands at the entrance again"),
]

SHORT_RUN_STORY = [
    (0.0, 4.7, "stands"),
    (4.7, 7.0, "speeds up forward"),
    (7.0, 16.8, "constant speed forward"),
    (16.8, 19.3, "brakes"),
    (19.3, 20.6, "stands"),
    (20.6, 23.0, "speeds up backward"),
    (23.0, 35.8, "constant speed backward"),
    (35.8, 38.7, "brakes"),
    (38.7, 42.5, "stands"),
]
