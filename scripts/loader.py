import math
from typing import Dict, List, NamedTuple, Optional, Set, Tuple
from xml.sax import parse as sax_parse
from xml.sax.handler import ContentHandler as SAXContentHandler
from xml.sax.xmlreader import AttributesImpl as SAXAttributes

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
        self.node_refs: List[str] = []

        self.position: Tuple[float, float] = math.nan, math.nan
        self.stations: List[Station] = []
        self.platforms: Dict[str, List[Platform]] = {}
        self.stop_positions: Dict[str, List[StopPosition]] = {}
        self.bus_stops: Dict[str, List[BusStop]] = {}
        self.dangling_nodes: Set[str] = set()

        self.in_way: bool = False
        self.in_node: bool = False

    def startElement(self, name: str, attrs: SAXAttributes[str]) -> None:
        if name == "node":
            self.tags = {"_id": attrs["id"]}
            self.position = (float(attrs["lat"]), float(attrs["lon"]))
            self.in_node = True

        elif name == "way":
            self.tags = {"_id": attrs["id"]}
            self.node_refs.clear()
            self.in_way = True

        elif name == "tag" and (self.in_node or self.in_way):
            if attrs["k"].startswith("_"):
                raise ValueError(
                    "Starting a tag with an underscore messes with processing"
                )
            self.tags[attrs["k"]] = attrs["v"]

        elif name == "nd" and self.in_way:
            self.node_refs.append(attrs["ref"])

    def endElement(self, name: str):
        if name == "node":
            self.in_node = False

            if self.tags.get("railway") == "station":
                self.dangling_nodes.add(self.tags["_id"])
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
                self.dangling_nodes.add(self.tags["_id"])
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

        elif name == "way":
            self.in_way = False

            if self.tags.get("railway") == "rail":
                self.dangling_nodes.difference_update(self.node_refs)

    @classmethod
    def load_all(cls, path: str) -> "OSMLoader":
        handler = cls()
        with open(path, "rb") as stream:
            sax_parse(stream, handler)
        return handler
