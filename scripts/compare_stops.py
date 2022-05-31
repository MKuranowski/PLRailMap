import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, Mapping, NamedTuple, Tuple

from .loader import OSMLoader, Station
from .util import distance
from .verify import Color

StationLookup: Dict[str, Station]


class GTFSStation(NamedTuple):
    id: str
    name: str
    position: Tuple[float, float]


def load_stations_from(file: Path) -> Iterable[GTFSStation]:
    with file.open(mode="r", encoding="utf-8-sig", newline="") as buffer:
        for row in csv.DictReader(buffer):
            # Only care about GTFS stations or GTFS stops without a parent
            is_main_row = row.get("location_type") == "1" or not row.get("parent_station")
            if not is_main_row:
                continue

            yield GTFSStation(
                row["stop_id"],
                row["stop_name"],
                (float(row["stop_lat"]), float(row["stop_lon"])),
            )


def compare_stations(stations_by_id: Mapping[str, Station], stops_file: Path,
                     announce_file: bool = True) -> bool:
    if announce_file:
        print(f"{Color.dim}Comparing {stops_file}{Color.reset}")

    ok = True
    warned = False

    for gtfs_station in load_stations_from(stops_file):
        match = stations_by_id.get(gtfs_station.id)

        if not match:
            ok = False
            print(
                f"❌ {Color.red}Missing from PLRailMap: {Color.blue}{gtfs_station.name}"
                f"{Color.red} (id: {gtfs_station.id}; pos: {gtfs_station.position[0]:.5f} "
                f"{gtfs_station.position[1]:.5f}){Color.reset}"
            )
            continue

        geo_dist = distance(match.position, gtfs_station.position) / 1000.0

        if geo_dist > 1000.0:
            warned = True
            print(
                f"⚠️ {Color.yellow}Far-away match: {Color.blue}{gtfs_station.name}"
                f"{Color.yellow} is {geo_dist:.3f} km away from PLRailMap station{Color.reset}"
            )

    if announce_file and ok and not warned:
        print(f"{Color.on_prev_line}✅ {Color.green}All stations from "
              f"{Color.blue}{stops_file}{Color.green} are in PLRailMap{Color.reset}")

    return ok


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "stops_txt_files",
        nargs="+",
        type=Path,
    )
    args = argument_parser.parse_args()

    all_stations = OSMLoader.load_all("plrailmap.osm").stations
    stations_by_pkpplk = {i.pkpplk: i for i in all_stations if i.pkpplk}
    stations_by_ibnr = {i.ibnr: i for i in all_stations if i.ibnr}

    ok = True

    for stops_txt_file in args.stops_txt_files:
        assert isinstance(stops_txt_file, Path)

        # FIXME: This should be customizable
        is_ibnr = stops_txt_file.name[:2].casefold() == "kw"

        ok = compare_stations(
            stations_by_ibnr if is_ibnr else stations_by_pkpplk,
            stops_txt_file,
            len(args.stops_txt_files) > 1,
        ) and ok

    if not ok:
        sys.exit(1)
    sys.exit(0)
