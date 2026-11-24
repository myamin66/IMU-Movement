"""
reconstruct_long_run.py

Main script. Reconstructs the path of the long run
(MT_0080001528_004-000.txt) and draws it on the map around the CLC.

    python reconstruct_long_run.py
    -> figures/long_run_signals.png      what the sensors show over time
    -> figures/long_run_path_on_map.png  the path on the map
    -> figures/magnetometer_check.png    compass + "same place" check
    -> a timeline in the terminal

Steps:
  1. standstills (calm accelerometer and gyro)
  2. heading from the gyro, bias removed
  3. speed of the first leg by integrating Acc_X between two stops
  4. speed of the long middle part from the loop closure
  5. start direction from the footway the first leg follows
  6. position = speed integrated in the heading direction
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import settings
from dead_reckoning import (DT, closed_loop_speeds, path_from, samples_between,
                            speed_between_stops, start_heading_from_footway, yaw_angle)
from imu_data import find_standstills, load_recording
from magnetometer import compass_heading, field_at_stops, fit_circle
from map_drawing import draw_map, draw_north_arrow, load_map


def reconstruct():
    """Runs steps 1-6 and returns everything the figures need."""
    data = load_recording(settings.LONG_RUN_FILE)
    time = data["time"]
    is_still, blocks = find_standstills(data)
    yaw, gyro_bias = yaw_angle(data, is_still)

    first_try_speed, drift_report = speed_between_stops(data, blocks)
    speed, speed_out, speed_back = closed_loop_speeds(time, yaw, first_try_speed)

    start_heading, footway = start_heading_from_footway(time, yaw)
    return {
        "data": data, "time": time, "blocks": blocks, "is_still": is_still,
        "yaw": yaw, "gyro_bias": gyro_bias, "drift_report": drift_report,
        "first_try_speed": first_try_speed, "speed": speed,
        "speed_out": speed_out, "speed_back": speed_back,
        "start_heading": start_heading, "footway": footway,
        "first_try_path": path_from(first_try_speed, yaw, start_heading),
        "path": path_from(speed, yaw, start_heading),
    }


def print_timeline(r):
    time, yaw, speed, path = r["time"], r["yaw"], r["speed"], r["path"]
    print(f"Long run: {len(time)} samples, {time[-1]:.1f} s")
    print("Standstills:", ", ".join(f"{time[a]:.1f}-{time[b - 1]:.1f} s" for a, b in r["blocks"]))
    print(f"Gyro bias removed: {np.degrees(r['gyro_bias']):.3f} deg/s")
    for start, end, leftover in r["drift_report"]:
        print(f"  first try, segment {start:.1f}-{end:.1f} s: speed drift {leftover:+.2f} m/s")
    end_error = r["first_try_path"][-1]
    print(f"First try (integration only) ends {np.hypot(*end_error):.1f} m from the start")
    print(f"Loop closure speeds: out {r['speed_out']:.2f} m/s, back {r['speed_back']:.2f} m/s")
    print(f"Start heading {r['start_heading']:.0f} deg (footway direction {r['footway']:.0f} deg)")
    print()
    print(f"{'time':>13}  {'what the robot does':34} {'right turn':>12} {'driven':>7} {'heading':>9}")
    for start, end, text in settings.LONG_RUN_STORY:
        part = samples_between(time, (start, end))
        turned = np.degrees(yaw[part][-1] - yaw[part][0])
        driven = np.sum(np.abs(speed[part])) * DT
        heading = (r["start_heading"] - np.degrees(yaw[part][-1])) % 360
        print(f"{start:5.1f}-{end:5.1f} s  {text:34} {-turned:+8.0f} deg {driven:5.1f} m {heading:5.0f} deg")
    print(f"Total distance {np.sum(np.abs(speed)) * DT:.0f} m, total turn "
          f"{np.degrees(yaw[-1]):+.0f} deg (minus = clockwise)")


def shade_story(axes, story):
    for start, end, text in story:
        colour = "#eeeeee" if text.startswith("stands") else "#dde8f5" if "drives" in text else "#f7e3d0"
        axes.axvspan(start, end, color=colour, lw=0)


def plot_signals(r, centre):
    data, time = r["data"], r["time"]
    figure, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    for ax in axes:
        shade_story(ax, settings.LONG_RUN_STORY)
        ax.grid(alpha=0.3)

    axes[0].plot(time, data["Acc_Z"], color="#2a8bc9", lw=0.8)
    axes[0].set_ylabel("Acc_Z m/s²")
    axes[0].set_title("Long run: grey = standing, blue = driving, orange = turning")
    for start, end, text in settings.LONG_RUN_STORY:
        axes[0].text((start + end) / 2, 14.6, text, ha="center", va="top", fontsize=7, rotation=90)
    axes[0].set_ylim(5, 15)

    axes[1].plot(time, np.degrees(data["Gyr_Z"]), color="#7a3fa0", lw=1)
    axes[1].set_ylabel("yaw rate °/s\n(minus = right)")

    gyro_heading = (r["start_heading"] - np.degrees(r["yaw"])) % 360
    axes[2].plot(time, gyro_heading, ".", ms=2, color="#1f4e79", label="gyro (used)")
    axes[2].plot(time, compass_heading(data, centre), ".", ms=2, color="#c0504d", alpha=0.6,
                 label="magnetometer (check)")
    axes[2].set_ylabel("heading °\n(0 = north)")
    axes[2].set_ylim(0, 360)
    axes[2].set_yticks([0, 90, 180, 270, 360])
    axes[2].legend(loc="upper left", markerscale=5)

    axes[3].plot(time, r["first_try_speed"], color="#999999", lw=1, label="first try: integration only")
    axes[3].plot(time, r["speed"], color="#1f4e79", lw=1.8, label="final: with loop closure")
    axes[3].set_ylabel("speed m/s")
    axes[3].set_xlabel("time s")
    axes[3].legend(loc="upper left")

    figure.tight_layout()
    figure.savefig("figures/long_run_signals.png", dpi=110)


def plot_map(r):
    figure, axes = plt.subplots(figsize=(11, 9))
    draw_map(axes, load_map(), settings.MAP_VIEW)
    path, first_try = r["path"], r["first_try_path"]
    axes.plot(first_try[:, 0], first_try[:, 1], "--", color="#888888", lw=1.3, zorder=4,
              label=f"first try (integration only), ends {np.hypot(*first_try[-1]):.0f} m off")
    axes.plot(path[:, 0], path[:, 1], color="#c00000", lw=2.5, zorder=5,
              label="final reconstruction (loop closed)")

    # Arrows every 10 s along the path to show the direction of travel.
    time = r["time"]
    for k in range(250, len(time) - 10, 100):
        if np.linalg.norm(path[k + 5] - path[k]) > 0.5:
            axes.annotate("", xy=path[k + 5], xytext=path[k], zorder=6,
                          arrowprops=dict(arrowstyle="-|>", color="#c00000", lw=1.5, mutation_scale=18))

    # Numbered places of the story.
    places = [(20, "1 start and 4 finish: CLC entrance\n(turns right on the spot before stopping)"),
              (45.6, "2 stop, turns right on the spot"), (101, "3 U-turn")]
    offsets = [(14, 14), (10, -22), (-40, -30)]
    for (moment, text), offset in zip(places, offsets):
        k = np.argmin(np.abs(time - moment))
        axes.plot(*path[k], "o", color="black", ms=6, zorder=7)
        axes.annotate(text, path[k], xytext=offset, textcoords="offset points", fontsize=9,
                      zorder=8, bbox=dict(boxstyle="round", fc="white", alpha=0.85))

    draw_north_arrow(axes)
    axes.legend(loc="upper left", fontsize=9)
    axes.set_title("Long run reconstructed from the IMU, starting at the CLC main entrance")
    figure.tight_layout()
    figure.savefig("figures/long_run_path_on_map.png", dpi=110)


def plot_magnetometer(r, centre, radius):
    data = r["data"]
    short = load_recording(settings.SHORT_RUN_FILE)
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    angles = np.linspace(0, 2 * np.pi, 200)
    axes[0].plot(data["Mag_X"], data["Mag_Y"], ".", ms=2, color="#999999", label="long run samples")
    axes[0].plot(centre[0] + radius * np.cos(angles), centre[1] + radius * np.sin(angles),
                 color="#c0504d", label="fitted circle")
    axes[0].plot(*centre, "+", color="#c0504d", ms=12, label="offset of the robot (hard iron)")
    axes[0].set_aspect("equal")
    axes[0].set_xlabel("Mag_X")
    axes[0].set_ylabel("Mag_Y")
    axes[0].set_title("Horizontal field while the robot turns a full circle")
    axes[0].legend(fontsize=8, loc="lower left")

    names, strengths, colours = [], [], []
    for label, recording, colour in [("long", data, "#1f4e79"), ("short", short, "#d9622b")]:
        for start, end, vector, strength in field_at_stops(recording, find_standstills(recording)[1]):
            names.append(f"{label} run\n{start:.0f}-{end:.0f} s")
            strengths.append(strength)
            colours.append(colour)
    axes[1].bar(range(len(names)), strengths, color=colours)
    axes[1].set_xticks(range(len(names)))
    axes[1].set_xticklabels(names, fontsize=8)
    axes[1].set_ylim(1.15, 1.55)
    axes[1].set_ylabel("field strength (earth field units)")
    axes[1].set_title("Field strength at every stop (same place = same value)")
    for i, value in enumerate(strengths):
        axes[1].text(i, value + 0.005, f"{value:.3f}", ha="center", fontsize=8)

    figure.tight_layout()
    figure.savefig("figures/magnetometer_check.png", dpi=110)


def main():
    r = reconstruct()
    print_timeline(r)

    data = r["data"]
    centre, radius = fit_circle(data["Mag_X"], data["Mag_Y"])
    start_compass = compass_heading(data, centre)[r["is_still"]][:100].mean()
    print(f"\nMagnetometer start heading {start_compass:.0f} deg "
          f"(footway method: {r['start_heading']:.0f} deg)")
    for start, end, vector, strength in field_at_stops(data, r["blocks"]):
        print(f"  field at stop {start:5.1f}-{end:5.1f} s: strength {strength:.3f}")

    plot_signals(r, centre)
    plot_map(r)
    plot_magnetometer(r, centre, radius)
    print("Saved figures/long_run_signals.png, long_run_path_on_map.png, magnetometer_check.png")


if __name__ == "__main__":
    main()
