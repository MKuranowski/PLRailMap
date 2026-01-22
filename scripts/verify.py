# cSpell: words ztmw
import math
import re
import sys
from collections import Counter, defaultdict
from itertools import chain
from typing import Dict, List, Optional

from .loader import BusStop, OSMLoader, Platform, Station, StopPosition
from .util import distance, group_by, osm_list

ID_WIDTH = 8
IBNR_WIDTH = 4
PKPPLK_WIDTH = 6

HEADING_HINTS = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"}
VALID_HINTS = {"*", "T"} | HEADING_HINTS

FIELDS = [
    "node".ljust(ID_WIDTH),
    "pkpplk".ljust(PKPPLK_WIDTH),
    "ibnr".ljust(IBNR_WIDTH),
    "name",
]


class Color:
    reset = "\x1b[0m"
    bold = "\x1b[1m"
    dim = "\x1b[2m"

    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"

    on_prev_line = "\x1b[F\x1b[K"


def print_station(station: Station, which_col_blue: Optional[int] = None):
    fields = [
        station.id.ljust(ID_WIDTH),
        station.pkpplk.ljust(PKPPLK_WIDTH),
        (station.ibnr or "").ljust(IBNR_WIDTH),
        station.name,
    ]

    if which_col_blue is not None:
        fields[which_col_blue] = Color.blue + fields[which_col_blue] + Color.reset

    print("\t".join(fields))


def verify_uniq_pkpplk(stations: List[Station]) -> bool:
    stations_by_pkpplk: defaultdict[str, List[Station]] = defaultdict(list)
    ok: bool = True

    print(f"{Color.dim}Checking uniqueness of PKP PLK IDs{Color.reset}")

    for station in stations:
        stations_by_pkpplk[station.pkpplk].append(station)

    for invalid_group in filter(
        lambda stations: len(stations) > 1, stations_by_pkpplk.values()
    ):
        if ok:
            ok = False
            print(
                f"{Color.on_prev_line}❌ {Color.red}Found duplicate PKP PLK ids:{Color.reset}"
            )
            print("\t".join(FIELDS))

        for station in invalid_group:
            print_station(station, 1)

    if ok:
        print(
            f"{Color.on_prev_line}✅ {Color.green}PKP PLK ids are unique{Color.reset}"
        )

    return ok


def verify_uniq_names(stations: List[Station]) -> bool:
    stations_by_name: defaultdict[str, List[Station]] = defaultdict(list)
    ok: bool = True

    print(f"{Color.dim}Checking uniqueness of names{Color.reset}")

    for station in stations:
        stations_by_name[station.name].append(station)

    for invalid_group in filter(
        lambda stations: len(stations) > 1, stations_by_name.values()
    ):
        if ok:
            ok = False
            print(
                f"{Color.on_prev_line}❌ {Color.red}Found duplicate names:{Color.reset}"
            )
            print("\t".join(FIELDS))

        for station in invalid_group:
            print_station(station, 3)

    if ok:
        print(
            f"{Color.on_prev_line}✅ {Color.green}Station names are unique{Color.reset}"
        )

    return ok


def verify_uniq_ibnr(stations: List[Station]) -> bool:
    stations_by_ibnr: defaultdict[str, List[Station]] = defaultdict(list)
    ok: bool = True

    print(f"{Color.dim}Checking uniqueness of IBNR codes{Color.reset}")

    for station in stations:
        if station.ibnr is not None:
            stations_by_ibnr[station.ibnr].append(station)

    for invalid_group in filter(
        lambda stations: len(stations) > 1, stations_by_ibnr.values()
    ):
        if ok:
            ok = False
            print(
                f"{Color.on_prev_line}❌ {Color.red}Found duplicate IBNR codes:{Color.reset}"
            )
            print("\t".join(FIELDS))

        for station in invalid_group:
            print_station(station, 2)

    if ok:
        print(f"{Color.on_prev_line}✅ {Color.green}IBNR codes are unique{Color.reset}")

    return ok


def verify_other_attributes(stations: List[Station]) -> bool:
    ok: bool = True

    print(f"{Color.dim}Checking optional attributes{Color.reset}")

    for station in stations:
        issues: List[str] = []

        wheelchair_value = station.other_tags.get("wheelchair")
        if wheelchair_value not in (None, "yes", "no"):
            issues.append(
                f"Invalid wheelchair value: {Color.yellow}{wheelchair_value}{Color.reset}"
            )

        ref_ztmw = station.other_tags.get("ref:ztmw")
        if ref_ztmw is not None and not re.fullmatch(r"[0-9]9[0-9][0-9]", ref_ztmw):
            issues.append(
                f"Invalid ref:ztmw value: {Color.yellow}{ref_ztmw}{Color.reset}"
            )

        if issues:
            ok = False
            print(
                f"Issues in {Color.blue}{station.pkpplk}{Color.reset} ({station.name}):"
            )
            for issue in issues:
                print("    " + issue)

    if ok:
        print(
            f"{Color.on_prev_line}✅ {Color.green}Optional attributes are OK{Color.reset}"
        )

    return ok


def verify_platforms(
    stations_map: Dict[str, Station],
    all_platforms: Dict[str, List[Platform]],
) -> bool:
    ok: bool = True
    print(f"{Color.dim}Checking platforms{Color.reset}")

    for station_id, platforms in all_platforms.items():
        issues: List[str] = []

        # Validate the reference
        station = stations_map.get(station_id)
        if station is None:
            ok = False
            print(
                f"Invalid reference to station {Color.blue}{station_id}{Color.reset} "
                "from platforms:",
                ", ".join(sorted(i.id for i in platforms)),
            )
            continue

        # Validate unique names
        platforms_by_name = group_by(platforms, key=lambda i: i.name)
        for duplicates in filter(lambda i: len(i) > 1, platforms_by_name.values()):
            name = duplicates[0].name
            issues.append(
                f"Platform name {Color.yellow}{name}{Color.reset} reused by nodes: "
                + ", ".join(sorted(i.id for i in duplicates))
            )

        # Validate direction hints
        direction_hints = Counter(
            chain.from_iterable(
                osm_list(i.other_tags.get("direction", "")) for i in platforms
            )
        )
        issues.extend(_validate_station_direction_hints(direction_hints))

        # Validate other attributes
        for platform in platforms:
            # Ensure the platform isn't too far away
            distance_from_station = distance(platform.position, station.position)
            if distance_from_station > 100.0 or math.isnan(distance_from_station):
                issues.append(
                    f"Platform {Color.blue}{platform.name}{Color.reset}: "
                    f"is {Color.yellow}{distance_from_station:.2f} m{Color.reset}"
                    " away from the station node"
                )

            # Validate ref:ztmw
            ztmw_refs = osm_list(platform.other_tags.get("ref:ztmw", ""))
            for ztmw_ref in ztmw_refs:
                match = re.fullmatch(r"[0-9]9[0-9]{4}", ztmw_ref)
                if not match:
                    issues.append(
                        f"Platform {Color.blue}{platform.name}{Color.reset}: "
                        "invalid ZTM Warszawa code: "
                        f"{Color.yellow}{ztmw_ref}{Color.reset}"
                    )

            # Validate wheelchair
            wheelchair_value = platform.other_tags.get("wheelchair")
            if wheelchair_value not in (None, "yes", "no"):
                issues.append(
                    f"Platform {Color.blue}{platform.name}{Color.reset}: "
                    "invalid wheelchair value: "
                    f"{Color.yellow}{wheelchair_value}{Color.reset}"
                )

        # Print the collected issues
        if issues:
            ok = False
            station = stations_map[station_id]
            print(
                f"Issues in {Color.blue}{station.pkpplk}{Color.reset} ({station.name}):"
            )
            for issue in issues:
                print("    " + issue)

    if ok:
        print(f"{Color.on_prev_line}✅ {Color.green}Platforms are OK{Color.reset}")

    return ok


def verify_stop_positions(
    stations_map: Dict[str, Station],
    all_stop_positions: Dict[str, List[StopPosition]],
) -> bool:
    ok: bool = True
    print(f"{Color.dim}Checking stop positions{Color.reset}")

    for station_id, stop_positions in all_stop_positions.items():
        issues: List[str] = []

        # Validate the reference
        station = stations_map.get(station_id)
        if station is None:
            ok = False
            print(
                f"Invalid reference to station {Color.blue}{station_id}{Color.reset} "
                "from stop positions:",
                ", ".join(sorted(i.id for i in stop_positions)),
            )
            continue

        # Validate the stop positions
        fallback_stop_positions = 0
        for sp in stop_positions:
            # Ensure the platform isn't too far away
            distance_from_station = distance(sp.position, station.position)
            if distance_from_station > 100.0 or math.isnan(distance_from_station):
                issues.append(
                    f"Stop Position {Color.blue}{sp.id}{Color.reset}: "
                    f"is {Color.yellow}{distance_from_station:.2f} m{Color.reset}"
                    " away from the station node"
                )

            # Ensure "platforms" are provided
            if not sp.platforms:
                issues.append(
                    f'Stop Position {Color.blue}{sp.id}{Color.reset}: has no "platforms" tag '
                )

            # Validate "towards"
            if sp.towards == "":
                pass
            elif sp.towards == "fallback":
                fallback_stop_positions += 1
            else:
                all_references = set(sp.towards.split(";"))
                unknown_references = {
                    i for i in all_references if i not in stations_map
                }
                if unknown_references:
                    unknown_references_str = ", ".join(sorted(unknown_references))
                    issues.append(
                        f"Stop Position {Color.blue}{sp.id}{Color.reset}: "
                        '"towards" tag references unknown stations - '
                        f"{Color.yellow}{unknown_references_str}{Color.reset}"
                    )

        # Ensure exactly one fallback stop position
        if fallback_stop_positions != 1:
            issues.append(
                f'Got {fallback_stop_positions} "towards=fallback" Stop Positions, '
                "expected exactly 1"
            )

        # Print the collected issues
        if issues:
            ok = False
            station = stations_map[station_id]
            print(
                f"Issues in {Color.blue}{station.pkpplk}{Color.reset} ({station.name}):"
            )
            for issue in issues:
                print("    " + issue)

    if ok:
        print(f"{Color.on_prev_line}✅ {Color.green}Stop Positions are OK{Color.reset}")

    return ok


def verify_bus_stops(
    stations_map: Dict[str, Station],
    all_bus_stops: Dict[str, List[BusStop]],
) -> bool:
    ok: bool = True
    print(f"{Color.dim}Checking bus stops{Color.reset}")

    for station_id, bus_stops in all_bus_stops.items():
        issues: List[str] = []

        # Validate the reference
        station = stations_map.get(station_id)
        if station is None:
            ok = False
            print(
                f"Invalid reference to station {Color.blue}{station_id}{Color.reset} "
                "from bus stops:",
                ", ".join(sorted(i.id for i in bus_stops)),
            )
            continue

        # Check for direction hint existence requirement
        if len(bus_stops) == 1:
            stop_hints = bus_stops[0].direction_hints
            if stop_hints != [] and stop_hints != ["*"]:
                issues.append(
                    "The only bus stop has incomplete direction hint coverage: "
                    f"{Color.yellow}{';'.join(stop_hints)}{Color.reset}. "
                    f"Expected no hints, or sole {Color.yellow}*{Color.reset} hint."
                )
        else:
            without_hints = [i for i in bus_stops if not i.direction_hints]
            for bus_stop in without_hints:
                issues.append(
                    f"Bus stop {Color.blue}{bus_stop.id}{Color.reset} has no hints"
                )

        # Validate direction hints
        direction_hints = Counter(
            chain.from_iterable(i.direction_hints for i in bus_stops)
        )
        issues.extend(_validate_station_direction_hints(direction_hints))

        # Print the collected issues
        if issues:
            ok = False
            station = stations_map[station_id]
            print(
                f"Issues in {Color.blue}{station.pkpplk}{Color.reset} ({station.name}):"
            )
            for issue in issues:
                print("    " + issue)

    if ok:
        print(f"{Color.on_prev_line}✅ {Color.green}Bus Stops are OK{Color.reset}")

    return ok


def _validate_station_direction_hints(direction_hints: "Counter[str]") -> list[str]:
    if not direction_hints:
        return []

    issues = list[str]()

    # Check if only valid values are used, and check rules 1 and 3
    wildcard_used = direction_hints["*"] > 0
    for hint, count in direction_hints.items():
        if hint not in VALID_HINTS:
            issues.append(
                f"Invalid direction hint used: {Color.yellow}{hint}{Color.reset}"
            )

        elif wildcard_used and hint in HEADING_HINTS:
            issues.append(
                f"Uses both the {Color.yellow}*{Color.reset} and "
                f"{Color.yellow}{hint}{Color.reset} hints"
            )

        elif count > 1:
            issues.append(
                f"Hint {Color.blue}{hint}{Color.reset} used "
                f"{Color.yellow}{count}{Color.reset} times"
            )

    used_heading_hints = {i for i in direction_hints if i in HEADING_HINTS}

    # Check rule 4
    if "T" in direction_hints and not wildcard_used and not used_heading_hints:
        issues.append(f"Only the {Color.blue}T{Color.reset} hint is present")

    # Check rule 2
    if not wildcard_used and len(used_heading_hints) < 2:
        issues.append("Only one heading hint is used")

    return issues


if __name__ == "__main__":
    data = OSMLoader.load_all("plrailmap.osm")
    ok = True
    ok = verify_uniq_pkpplk(data.stations) and ok
    ok = verify_uniq_names(data.stations) and ok
    ok = verify_uniq_ibnr(data.stations) and ok
    ok = verify_other_attributes(data.stations) and ok

    stations_map: Dict[str, Station] = {i.pkpplk: i for i in data.stations}

    ok = verify_platforms(stations_map, data.platforms) and ok
    ok = verify_stop_positions(stations_map, data.stop_positions) and ok
    ok = verify_bus_stops(stations_map, data.bus_stops) and ok
    sys.exit(0 if ok else 1)
