import math
from typing import Dict, List, Mapping, NamedTuple, Optional, Tuple
from xml.sax import parse as sax_parse
from xml.sax.handler import ContentHandler as SAXContentHandler

from .util import osm_list


class Station(NamedTuple):
    id: str
    name: str
    pkpplk: str
    ibnr: Optional[str]
    position: Tuple[float, float]
    other_tags: Dict[str, str]


class Platform(NamedTuple):
    id: str
    name: str
    station: str
    position: Tuple[float, float]
    other_tags: Dict[str, str]


class StopPosition(NamedTuple):
    id: str
    station: str
    towards: str
    platforms: list[str]
    position: Tuple[float, float]


class BusStop(NamedTuple):
    id: str
    station: str
    direction_hints: list[str]
    position: Tuple[float, float]


class OSMLoader(SAXContentHandler):
    def __init__(self) -> None:
        super().__init__()
        self.tags: Dict[str, str] = {}
        self.position: Tuple[float, float] = math.nan, math.nan
        self.stations: List[Station] = []
        self.platforms: Dict[str, List[Platform]] = {}
        self.stop_positions: Dict[str, List[StopPosition]] = {}
        self.bus_stops: Dict[str, List[BusStop]] = {}
        self.in_node: bool = False

    def startElement(self, name: str, attrs: Mapping[str, str]):
        if name == "node":
            self.tags = {"_id": attrs["id"]}
            self.position = (float(attrs["lat"]), float(attrs["lon"]))
            self.in_node = True
        elif name == "tag" and self.in_node:
            if attrs["k"].startswith("_"):
                raise ValueError(
                    "Starting a tag with an underscore messes with processing"
                )
            self.tags[attrs["k"]] = attrs["v"]

    def endElement(self, name: str):
        if name == "node":
            self.in_node = False

            if self.tags.get("railway") == "station":
                self.stations.append(
                    Station(
                        id=self.tags["_id"],
                        name=self.tags["name"],
                        pkpplk=self.tags["ref"],
                        ibnr=self.tags.get("ref:ibnr"),
                        position=self.position,
                        other_tags=self.tags,
                    )
                )

            elif self.tags.get("public_transport") == "platform":
                station = self.tags["ref:station"]
                self.platforms.setdefault(station, []).append(
                    Platform(
                        id=self.tags["_id"],
                        name=self.tags["name"],
                        station=station,
                        position=self.position,
                        other_tags=self.tags,
                    )
                )

            elif self.tags.get("public_transport") == "stop_position":
                station = self.tags["ref:station"]
                self.stop_positions.setdefault(station, []).append(
                    StopPosition(
                        id=self.tags["_id"],
                        station=station,
                        towards=self.tags.get("towards", ""),
                        platforms=osm_list(self.tags.get("platforms", "")),
                        position=self.position,
                    )
                )

            elif self.tags.get("highway") == "bus_stop":
                station = self.tags["ref:station"]
                self.bus_stops.setdefault(station, []).append(
                    BusStop(
                        id=self.tags["_id"],
                        station=station,
                        position=self.position,
                        direction_hints=osm_list(self.tags.get("direction", "")),
                    )
                )

    @classmethod
    def load_all(cls, path: str) -> "OSMLoader":
        handler = cls()
        with open(path, "rb") as stream:
            sax_parse(stream, handler)
        return handler
