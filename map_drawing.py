"""
map_drawing.py

Draws the area around the CLC building from OpenStreetMap data
(data/osm_clc_area.json, downloaded once with get_osm_map.py) and puts
the reconstructed path on top.

Map coordinates are metres east and north of the CLC main entrance.
Map data (c) OpenStreetMap contributors, ODbL.
"""

import json

import numpy as np

import settings

BUILDING = "#d9cfc4"
PARKING = "#e6e6ef"
GRASS = "#d6ebcb"
ROAD = "#555555"
FOOTWAY = "#e09060"


def to_metres(lat, lon):
    """
    Latitude/longitude -> metres east and north of the entrance.
    Over a few hundred metres the earth is flat enough for this:
    one degree of latitude is about 110.5 km, one degree of longitude
    is 111.3 km times cos(latitude).
    """
    east = (lon - settings.ENTRANCE_LON) * np.cos(np.radians(settings.ENTRANCE_LAT)) * 111320
    north = (lat - settings.ENTRANCE_LAT) * 110540
    return east, north


def load_map():
    with open(settings.OSM_FILE, encoding="utf-8") as file:
        return json.load(file)["elements"]


def draw_map(axes, elements, view, label_building=True):
    """
    Buildings, parking, grass, roads and footways.
    view = (west, east, south, north) in metres: the visible area. Things
    completely outside it are skipped, which makes drawing (and the
    animation) much faster.
    """
    west, east_limit, south, north_limit = view
    for element in elements:
        if element["type"] != "way":
            continue
        tags = element.get("tags", {})
        points = np.array([to_metres(p["lat"], p["lon"]) for p in element["geometry"]])
        east, north = points[:, 0], points[:, 1]
        if (east.max() < west or east.min() > east_limit
                or north.max() < south or north.min() > north_limit):
            continue

        if "building" in tags:
            axes.fill(east, north, color=BUILDING, ec="#8a7a6a", lw=0.6, zorder=2)
            if label_building and tags.get("name") == "ELTE Bogdánfy utcai csarnok":
                axes.text(east.mean() - 12, north.mean() + 4, "CLC building", fontsize=10,
                          ha="center", color="#5a4a3a", zorder=3)
        elif tags.get("amenity") == "parking":
            axes.fill(east, north, color=PARKING, ec="#aaaacc", lw=0.5, zorder=1)
        elif tags.get("landuse") == "grass" or tags.get("leisure") == "park" or "natural" in tags:
            axes.fill(east, north, color=GRASS, ec="none", zorder=0)
        elif "highway" in tags:
            if tags["highway"] in ("footway", "path", "pedestrian", "steps", "cycleway"):
                axes.plot(east, north, color=FOOTWAY, lw=1.0, zorder=1)
            else:
                axes.plot(east, north, color=ROAD, lw=1.6, zorder=1)

    axes.set_xlim(west, east_limit)
    axes.set_ylim(south, north_limit)
    axes.set_aspect("equal")
    axes.set_xlabel("metres east of the entrance")
    axes.set_ylabel("metres north of the entrance")
    axes.text(0.99, 0.01, "Map data (c) OpenStreetMap contributors", transform=axes.transAxes,
              fontsize=7, ha="right", va="bottom", color="#666666")


def draw_north_arrow(axes, x=0.94, y=0.86):
    axes.annotate("N", xy=(x, y + 0.08), xytext=(x, y), xycoords="axes fraction",
                  ha="center", fontsize=12, fontweight="bold",
                  arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5))
