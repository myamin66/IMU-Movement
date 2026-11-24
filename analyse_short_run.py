"""
analyse_short_run.py

The short run (MT_0080001528_006-000.txt) has a known story: start from
rest, speed up, constant speed, stop, reverse, stop close to the start.
I use it to
  * find out which IMU axis points forward and which way is positive,
  * test the speed integration on a case where the answer is known
    (the robot should end up close to where it started).

    python analyse_short_run.py
    -> figures/short_run.png and a summary in the terminal
"""

import matplotlib
matplotlib.use("Agg")   # draw into files, no window
import matplotlib.pyplot as plt
import numpy as np

import settings
from dead_reckoning import DT, speed_between_stops, yaw_angle
from imu_data import find_standstills, load_recording


def shade_phases(axes, story):
    """Light background colour for every phase (moving phases darker)."""
    for start, end, text in story:
        colour = "#eeeeee" if text.startswith("stands") else "#dde8f5"
        axes.axvspan(start, end, color=colour, lw=0)


def main():
    data = load_recording(settings.SHORT_RUN_FILE)
    time = data["time"]
    is_still, blocks = find_standstills(data)
    speed, report = speed_between_stops(data, blocks)
    yaw, gyro_bias = yaw_angle(data, is_still)
    # Signed distance along the robot's x axis (forward +, backward -).
    # The robot turned less than 10 degrees, so this is close enough.
    distance = np.cumsum(speed * DT)

    print(f"Short run: {len(time)} samples, {time[-1]:.1f} s")
    print("Standstills:", ", ".join(f"{time[a]:.1f}-{time[b - 1]:.1f} s" for a, b in blocks))
    print(f"Acc_X while standing at the start: {data['Acc_X'][blocks[0][0]:blocks[0][1]].mean():+.2f} m/s^2"
          " (gravity leaking in: the ground is tilted by about 2 degrees)")
    # The first strong push after the standstill is the start, and the
    # professor says the robot started forward. So its sign tells us
    # which way the x axis points.
    first_push = np.argmax(np.abs(data["Acc_X"] - data["Acc_X"][0]) > 1.0)
    print(f"First strong Acc_X value: {data['Acc_X'][first_push]:+.2f} m/s^2 at "
          f"{time[first_push]:.1f} s -> positive x = forward")
    for start, end, leftover in report:
        print(f"  segment {start:.1f}-{end:.1f} s: speed drift removed {leftover:+.2f} m/s")

    forward = speed > 0
    turn_point = distance[blocks[1][0]]
    print(f"Top speed forward {speed.max():.2f} m/s, backward {speed.min():.2f} m/s")
    print(f"Forward {turn_point:.1f} m, then back {turn_point - distance[-1]:.1f} m")
    print(f"End position: {distance[-1]:+.1f} m from the start "
          f"(total driven {np.sum(np.abs(speed)) * DT:.1f} m)")
    print(f"Heading change over the run: {np.degrees(yaw[-1]):+.1f} deg")

    figure, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    for ax in axes:
        shade_phases(ax, settings.SHORT_RUN_STORY)
        ax.grid(alpha=0.3)

    axes[0].plot(time, data["Acc_X"], color="#d9622b", lw=1, label="Acc_X (forward)")
    axes[0].plot(time, data["Acc_Y"], color="#2b7a2b", lw=0.8, alpha=0.6, label="Acc_Y (left)")
    axes[0].set_ylabel("m/s²")
    axes[0].set_title("Short run: forward, stop, reverse, stop")
    axes[0].legend(loc="lower left")
    for start, end, text in settings.SHORT_RUN_STORY:
        axes[0].text((start + end) / 2, 2.6, text, ha="center", fontsize=7, rotation=90, va="top")
    axes[0].set_ylim(-2.6, 3.0)

    axes[1].plot(time, speed, color="#1f4e79", lw=1.5)
    axes[1].axhline(0, color="black", lw=0.6)
    axes[1].set_ylabel("speed m/s")

    axes[2].plot(time, distance, color="#1f4e79", lw=1.5)
    axes[2].axhline(0, color="black", lw=0.6)
    axes[2].set_ylabel("distance from start m")
    axes[2].set_xlabel("time s")
    axes[2].annotate(f"ends {distance[-1]:+.1f} m from the start", (time[-1], distance[-1]),
                     xytext=(-150, 25), textcoords="offset points",
                     arrowprops=dict(arrowstyle="->"))

    figure.tight_layout()
    figure.savefig("figures/short_run.png", dpi=110)
    print("Saved figures/short_run.png")


if __name__ == "__main__":
    main()
