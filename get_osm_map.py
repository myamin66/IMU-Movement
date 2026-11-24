"""
get_osm_map.py

Downloads the OpenStreetMap data (buildings, roads, footways, parking,
grass) within 350 m of the CLC entrance and saves it to
data/osm_clc_area.json. The file is already included, so this is only
needed to refresh it.

    python get_osm_map.py
"""

import urllib.parse
import urllib.request

import settings

URL = "https://overpass-api.de/api/interpreter"


def main():
    around = f"around:350,{settings.ENTRANCE_LAT},{settings.ENTRANCE_LON}"
    query = f"""[out:json][timeout:60];
    (way({around})[building];
     way({around})[highway];
     way({around})[amenity=parking];
     way({around})[landuse];
     way({around})[leisure];
     way({around})[natural];
     node({around})[entrance];);
    out body geom;"""
    request = urllib.request.Request(URL, data=urllib.parse.urlencode({"data": query}).encode(),
                                     headers={"User-Agent": "student-imu-project/1.0"})
    with urllib.request.urlopen(request) as response, open(settings.OSM_FILE, "wb") as file:
        file.write(response.read())
    print(f"Saved {settings.OSM_FILE}")


if __name__ == "__main__":
    main()
