import json
from typing import Any, Dict, Iterable, List
import sys

from .loader import Station, Platform, OSMLoader
from .util import osm_list


def stations_to_json(raw_stations: Iterable[Station]) -> Dict[str, Dict[str, Any]]:
    json_stations: Dict[str, Dict[str, Any]] = {}

    for raw_station in raw_stations:
        # Base object
        json_station = {
            "name": raw_station.name,
            "lat": raw_station.position[0],
            "lon": raw_station.position[1],
            "code_pkpplk": raw_station.pkpplk,
        }

        # Additional attributes
        if raw_station.ibnr:
            json_station["code_ibnr"] = raw_station.ibnr

        if (second_pkpplk_code := raw_station.other_tags.get("ref:2")):
            json_station["code_pkpplk_2"] = second_pkpplk_code

        if (ztm_code := raw_station.other_tags.get("ref:ztmw")):
            json_station["code_ztmw"] = ztm_code

        if (wheelchair := raw_station.other_tags.get("wheelchair")):
            json_station["wheelchair"] = wheelchair

        json_stations[raw_station.pkpplk] = json_station

    return json_stations


def platforms_to_json(json_stations: Dict[str, Dict[str, Any]],
                      raw_platforms: Dict[str, List[Platform]]) -> None:
    for station_id, platforms in raw_platforms.items():
        if platforms:
            json_stations[station_id]["platforms"] = []

        for platform in platforms:
            platform_json = {
                "name": platform.name,
                "lat": platform.position[0],
                "lon": platform.position[1],
            }

            # Additional attributes
            if (direction_hints := platform.other_tags.get("direction")):
                platform_json["direction_hints"] = osm_list(direction_hints)

            if (ztm_codes := platform.other_tags.get("ref:ztmw")):
                platform_json["codes_ztmw"] = osm_list(ztm_codes)

            if (wheelchair := platform.other_tags.get("wheelchair")):
                platform_json["wheelchair"] = wheelchair

            # Append to station
            json_stations[platform.station]["platforms"].append(platform_json)


if __name__ == "__main__":
    data = OSMLoader.load_all("plrailmap.osm")
    stations_json = stations_to_json(data.stations)
    platforms_to_json(stations_json, data.platforms)
    json.dump(stations_json, sys.stdout, indent=2, ensure_ascii=False)
