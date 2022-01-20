#!/usr/bin/env python3
from collections import defaultdict
from typing import Dict, List, Mapping, NamedTuple, Optional
from xml.sax import parse as sax_parse
from xml.sax.handler import ContentHandler as SAXContentHandler
import sys

ID_WIDTH = 8
IBNR_WIDTH = 4
PKPPLK_WIDTH = 6

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
    name: str
    id: str
    pkpplk: str
    ibnr: Optional[str] = None

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


class OSMStationLoader(SAXContentHandler):
    def __init__(self) -> None:
        super().__init__()
        self.tags: Dict[str, str] = {}
        self.stations: List[Station] = []
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
        if name == "node" and self.tags.get("railway") == "station":
            self.in_node = False
            self.stations.append(Station(
                name=self.tags["name"],
                id=self.tags["_id"],
                pkpplk=self.tags["ref"],
                ibnr=self.tags.get("ref:ibnr"),
            ))

    @classmethod
    def load_all(cls, path: str) -> List[Station]:
        with open(path, "rb") as stream:
            handler = cls()
            sax_parse(stream, handler)
            return handler.stations


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
        # Warszawa Zachodnia is a special group where 3 stations can
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


if __name__ == "__main__":
    stations = OSMStationLoader.load_all("plrailmap.osm")
    ok = True
    ok = verify_uniq_pkpplk(stations) and ok
    ok = verify_uniq_names(stations) and ok
    ok = verify_uniq_ibnr(stations) and ok
    sys.exit(0 if ok else 1)
