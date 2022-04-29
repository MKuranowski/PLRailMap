import math
from typing import Callable, Dict, Iterable, List, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")


def group_by(iterable: Iterable[V], key: Callable[[V], K]) -> Dict[K, List[V]]:
    grouped: Dict[K, List[V]] = {}
    for i in iterable:
        grouped.setdefault(key(i), []).append(i)
    return grouped


def osm_list(value: str) -> List[str]:
    return value.split(";") if value else []


def distance(n1: Tuple[float, float], n2: Tuple[float, float]) -> float:
    """Calculates the distance between two positions (in meters) using the haversine formula.

    The radius used for calculations is taken from the WGS 84 ellipsoid
    at the center of Poland.

    Radius by latitude calculator: https://planetcalc.com/7721/
    Center of Poland: https://pl.wikipedia.org/wiki/Geometryczny_%C5%9Brodek_Polski
    """
    lat1, lon1 = map(math.radians, n1)
    lat2, lon2 = map(math.radians, n2)
    delta_lat_half = (lat2 - lat1) * 0.5
    delta_lon_half = (lon2 - lon1) * 0.5

    sqrt_h = math.sqrt(
        (math.sin(delta_lat_half) ** 2)
        + (math.cos(lat1) * math.cos(lat2) * (math.sin(delta_lon_half) ** 2))
    )

    return math.asin(sqrt_h) * 2.0 * 6364858.7
