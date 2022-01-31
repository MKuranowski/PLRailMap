#!/usr/bin/env python3
# cSpell: words ztmw
import re
import sys
from collections import Counter, defaultdict
from itertools import chain
from typing import (Callable, Dict, Iterable, List, Mapping, NamedTuple,
                    Optional, TypeVar)
from xml.sax import parse as sax_parse
from xml.sax.handler import ContentHandler as SAXContentHandler

K = TypeVar("K")
V = TypeVar("V")

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
    reset = "\x1B[0m"
    bold = "\x1B[1m"
    dim = "\x1B[2m"

    red = "\x1B[31m"
    green = "\x1B[32m"
    yellow = "\x1B[33m"
    blue = "\x1B[34m"

    on_prev_line = "\x1B[F\x1B[K"


class Station(NamedTuple):
    id: str
    name: str
    pkpplk: str
    ibnr: Optional[str]
    other_tags: Dict[str, str]

    def print(self, which_col_blue: Optional[int] = None) -> None:
        fields = [
            self.id.ljust(ID_WIDTH),
            self.pkpplk.ljust(PKPPLK_WIDTH),
            (self.ibnr or "").ljust(IBNR_WIDTH),
            self.name
        ]

        if which_col_blue is not None:
            fields[which_col_blue] = Color.blue + fields[which_col_blue] + Color.reset

        print("\t".join(fields))


class Platform(NamedTuple):
    id: str
    name: str
    station: str
    other_tags: Dict[str, str]


class OSMLoader(SAXContentHandler):
    def __init__(self) -> None:
        super().__init__()
        self.tags: Dict[str, str] = {}
        self.stations: List[Station] = []
        self.platforms: Dict[str, List[Platform]] = {}
        self.in_node: bool = False

    def startElement(self, name: str, attrs: Mapping[str, str]):
        if name == "node":
            self.tags = {"_id": attrs["id"]}
            self.in_node = True
        elif name == "tag" and self.in_node:
            if attrs["k"].startswith("_"):
                raise ValueError("Starting a tag with an underscore messes with processing")
            self.tags[attrs["k"]] = attrs["v"]

    def endElement(self, name: str):
        if name == "node":
            self.in_node = False

            if self.tags.get("railway") == "station":
                self.stations.append(Station(
                    id=self.tags["_id"],
                    name=self.tags["name"],
                    pkpplk=self.tags["ref"],
                    ibnr=self.tags.get("ref:ibnr"),
                    other_tags=self.tags,
                ))

            elif self.tags.get("public_transport") == "platform":
                station = self.tags["ref:station"]
                self.platforms.setdefault(station, []).append(Platform(
                    id=self.tags["_id"],
                    name=self.tags["name"],
                    station=station,
                    other_tags=self.tags,
                ))

    @classmethod
    def load_all(cls, path: str) -> "OSMLoader":
        handler = cls()
        with open(path, "rb") as stream:
            sax_parse(stream, handler)
        return handler


def group_by(iterable: Iterable[V], key: Callable[[V], K]) -> Dict[K, List[V]]:
    grouped: Dict[K, List[V]] = {}
    for i in iterable:
        grouped.setdefault(key(i), []).append(i)
    return grouped


def osm_list(value: str) -> List[str]:
    return value.split(";") if value else []


def verify_uniq_pkpplk(stations: List[Station]) -> bool:
    stations_by_pkpplk: defaultdict[str, List[Station]] = defaultdict(list)
    ok: bool = True

    print(f"{Color.dim}Checking uniqueness of PKP PLK IDs{Color.reset}")

    for station in stations:
        stations_by_pkpplk[station.pkpplk].append(station)

    for invalid_group in filter(lambda stations: len(stations) > 1, stations_by_pkpplk.values()):
        if ok:
            ok = False
            print(f"{Color.on_prev_line}❌ {Color.red}Found duplicate PKP PLK ids:{Color.reset}")
            print("\t".join(FIELDS))

        for station in invalid_group:
            station.print(1)

    if ok:
        print(f"{Color.on_prev_line}✅ {Color.green}PKP PLK ids are unique{Color.reset}")

    return ok


def verify_uniq_names(stations: List[Station]) -> bool:
    stations_by_name: defaultdict[str, List[Station]] = defaultdict(list)
    ok: bool = True

    print(f"{Color.dim}Checking uniqueness of names{Color.reset}")

    for station in stations:
        stations_by_name[station.name].append(station)

    for invalid_group in filter(lambda stations: len(stations) > 1, stations_by_name.values()):
        # Warszawa Zachodnia is represented by 3 nodes, 2 "Warszawa Zachodnia" parent+main stop,
        # and 1 "Warszawa Zachodnia (Peron 8)"
        if all(s.ibnr == "404" for s in invalid_group):
            continue

        if ok:
            ok = False
            print(f"{Color.on_prev_line}❌ {Color.red}Found duplicate names:{Color.reset}")
            print("\t".join(FIELDS))

        for station in invalid_group:
            station.print(3)

    if ok:
        print(f"{Color.on_prev_line}✅ {Color.green}Station names are unique{Color.reset}")

    return ok


def verify_uniq_ibnr(stations: List[Station]) -> bool:
    stations_by_ibnr: defaultdict[str, List[Station]] = defaultdict(list)
    ok: bool = True

    print(f"{Color.dim}Checking uniqueness of IBNR codes{Color.reset}")

    for station in stations:
        if station.ibnr is not None:
            stations_by_ibnr[station.ibnr].append(station)

    for invalid_group in filter(lambda stations: len(stations) > 1, stations_by_ibnr.values()):
        # Warszawa Zachodnia is a special group where 2 stations can
        # have the same IBNR code (404)
        if len(invalid_group) == 2 and {s.pkpplk for s in invalid_group} \
                == {"33506", "34868"}:
            continue

        if ok:
            ok = False
            print(f"{Color.on_prev_line}❌ {Color.red}Found duplicate IBNR codes:{Color.reset}")
            print("\t".join(FIELDS))

        for station in invalid_group:
            station.print(2)

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
            issues.append("Invalid wheelchair value: "
                          f"{Color.yellow}{wheelchair_value}{Color.reset}")

        ref_ztmw = station.other_tags.get("ref:ztmw")
        if ref_ztmw is not None and not re.fullmatch(r"[0-9]9[0-9][0-9]", ref_ztmw):
            issues.append("Invalid ref:ztmw value: "
                          f"{Color.yellow}{ref_ztmw}{Color.reset}")

        if issues:
            ok = False
            print(f"Issues in {Color.blue}{station.pkpplk}{Color.reset} ({station.name}):")
            for issue in issues:
                print("    " + issue)

    if ok:
        print(f"{Color.on_prev_line}✅ {Color.green}Optional attributes are OK{Color.reset}")

    return ok


def verify_platforms(stations_map: Dict[str, Station], all_platforms: Dict[str, List[Platform]]) \
        -> bool:
    ok: bool = True
    print(f"{Color.dim}Checking platforms{Color.reset}")

    for station_id, platforms in all_platforms.items():
        issues: List[str] = []

        # Validate the reference
        if station_id not in stations_map:
            ok = False
            print(f"Invalid reference to station {Color.blue}{station_id}{Color.reset} "
                  "from platforms:", ", ".join(sorted(i.id for i in platforms)))
            continue

        # Validate unique names
        platforms_by_name = group_by(platforms, key=lambda i: i.name)
        for duplicates in filter(lambda i: len(i) > 1, platforms_by_name.values()):
            name = duplicates[0].name
            issues.append(f"Platform name {Color.yellow}{name}{Color.reset} reused by nodes: " +
                          ", ".join(sorted(i.id for i in duplicates)))

        # Validate direction hints
        direction_hints = Counter(chain.from_iterable(
            osm_list(i.other_tags.get("direction", "")) for i in platforms
        ))
        if direction_hints:
            # Check if only valid values are used, and check rules 1 and 3
            wildcard_used = direction_hints["*"] > 0
            for hint, count in direction_hints.items():
                if hint not in VALID_HINTS:
                    issues.append("Invalid direction hint used: "
                                  f"{Color.yellow}{hint}{Color.reset}")

                elif wildcard_used and hint in HEADING_HINTS:
                    issues.append(f"Station uses both the {Color.yellow}*{Color.reset} and "
                                  f"{Color.yellow}{hint}{Color.reset} hints")

                elif count > 1:
                    issues.append(f"Hint {Color.blue}{hint}{Color.reset} used "
                                  f"{Color.yellow}{count}{Color.reset} times")

            used_heading_hints = {i for i in direction_hints if i in HEADING_HINTS}

            # Check rule 4
            if "T" in direction_hints and not wildcard_used and not used_heading_hints:
                issues.append(f"Only the {Color.blue}T{Color.reset} is present")

            # Check rule 2
            if not wildcard_used and len(used_heading_hints) < 2:
                issues.append("Only one heading hint is used")

        # Validate other attributes
        for platform in platforms:
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
            print(f"Issues in {Color.blue}{station.pkpplk}{Color.reset} ({station.name}):")
            for issue in issues:
                print("    " + issue)

    if ok:
        print(f"{Color.on_prev_line}✅ {Color.green}Platforms are OK{Color.reset}")

    return ok


if __name__ == "__main__":
    data = OSMLoader.load_all("plrailmap.osm")
    ok = True
    ok = verify_uniq_pkpplk(data.stations) and ok
    ok = verify_uniq_names(data.stations) and ok
    ok = verify_uniq_ibnr(data.stations) and ok
    ok = verify_other_attributes(data.stations) and ok

    stations_map: Dict[str, Station] = {i.pkpplk: i for i in data.stations}

    ok = verify_platforms(stations_map, data.platforms) and ok
    sys.exit(0 if ok else 1)
