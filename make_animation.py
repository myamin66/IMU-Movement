"""
make_animation.py

Short video of the reconstructed long run: the robot (red triangle)
drives over the map, 4 times faster than in reality.

    python make_animation.py
    -> figures/long_run_animation.mp4   (needs ffmpeg on the PATH)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter

import settings
from map_drawing import draw_map, draw_north_arrow, load_map
from reconstruct_long_run import reconstruct

SPEED_UP = 4
FPS = 20


def phase_text(moment):
    for start, end, text in settings.LONG_RUN_STORY:
        if start <= moment < end:
            return text
    return settings.LONG_RUN_STORY[-1][2]


def robot_triangle(position, heading_deg, size=3.5):
    """Corners of a triangle pointing in the driving direction (map metres)."""
    heading = np.radians(heading_deg)
    forward = np.array([np.sin(heading), np.cos(heading)])
    side = np.array([forward[1], -forward[0]])
    return np.array([position + forward * size,
                     position - forward * size * 0.6 + side * size * 0.6,
                     position - forward * size * 0.6 - side * size * 0.6])


def main():
    r = reconstruct()
    time, path, speed = r["time"], r["path"], r["speed"]
    heading = (r["start_heading"] - np.degrees(r["yaw"])) % 360

    figure, axes = plt.subplots(figsize=(10, 8))
    draw_map(axes, load_map(), settings.MAP_VIEW)
    draw_north_arrow(axes)
    axes.plot(path[:, 0], path[:, 1], color="#c00000", lw=1, alpha=0.25)   # whole path, faint
    trail, = axes.plot([], [], color="#c00000", lw=2.5, zorder=5)
    robot = plt.Polygon(robot_triangle(path[0], heading[0]), color="#c00000", zorder=6)
    axes.add_patch(robot)
    info = axes.text(0.02, 0.97, "", transform=axes.transAxes, va="top", fontsize=11,
                     family="monospace", bbox=dict(boxstyle="round", fc="white", alpha=0.9))
    axes.set_title("IMU reconstruction of the long run (4x speed)")
    figure.tight_layout()

    step = int(SPEED_UP / (FPS * settings.SAMPLE_TIME))   # samples per video frame
    writer = FFMpegWriter(fps=FPS, codec="libx264", extra_args=["-pix_fmt", "yuv420p"])
    with writer.saving(figure, "figures/long_run_animation.mp4", dpi=100):
        for k in range(0, len(time), step):
            trail.set_data(path[:k + 1, 0], path[:k + 1, 1])
            robot.set_xy(robot_triangle(path[k], heading[k]))
            info.set_text(f"t = {time[k]:5.1f} s   speed {abs(speed[k]):.1f} m/s   "
                          f"heading {heading[k]:3.0f}°\n{phase_text(time[k])}")
            writer.grab_frame()
    print("Saved figures/long_run_animation.mp4")


if __name__ == "__main__":
    main()
