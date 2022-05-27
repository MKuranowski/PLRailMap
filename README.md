PLRailMap
=========

This is a small repository with a OSM file with the Polish Railway Network.

This dataset is not yet complete. For now, it only contains station nodes for
the following operators:

- [x] PolRegio
- [x] Koleje Mazowieckie
- [x] PKP Intercity
- [ ] PKP SKM Trójmiasto
- [x] SKM Warszawa
- [ ] Koleje Śląskie
- [ ] Koleje Dolnośląskie
- [ ] Koleje Wielkopolskie
- [ ] Warszawska Kolej Dojazdowa
- [ ] Koleje Małopolskie
- [ ] Łódzka Kolej Aglomeracyjna
- [ ] Arriva RP

In the future it would also be nice to also draw the rail lines.

Tagging
-------

### Stations

These tags are always required:
- `railway=station`
- `name`: name of the station in the local language
- `ref`: PKP PLK code of the station (not necessarily an integer!)

Optional tags:
- `ref:ibnr`: available for most stations, but not all of them.
- `ref:2`: [Station _Kępno_](https://www.openstreetmap.org/node/1508480102) has 2 PKP PLK codes;
    the secondary code is available under this key.
- `ref:ztmw`: 4-digit station code used by ZTM Warszawa.
- `name:pl`: Must be used if the station name is not in Polish.
- `wheelchair=yes`/`wheelchair/no`: Determines whether the station is wheelchair accessible.


If the station name is not in Polish, `name:pl` should also be present.

Another optional 

### Platforms

These tags are always required:
- `public_transport=platform`
- `name` - number of the platform (e.g. `1`)
- `ref:station` - ID (`ref`) of the whole station

Optional tags:
- `ref:ztmw`: `;`-separated list of 6-digit ZTM stop codes that should map to this platform.
- `wheelchair=yes`/`wheelchair/no`: Determines whether the platform is wheelchair accessible.

Not all stations have platforms (in fact, most of them don't).

##### Direction Hints

To aid with finding the correct platform, the `direction` key might be present.
If present it must contain a list (`;`-separated) of the following values:
- `T`: Platform used for trains terminating and starting at this station
- `N`/`NE`/`E`/`SE`/`S`/`SW`/`W`/`NW`:
    Platform used for trains in a specified heading.
- `*`:
    Platform used for trains in all geographical directions.

The following rules apply:

1. If one platform has a `*` direction hint, no heading hints may be present.
2. If using heading hints - at least 2 platforms with different heading hints must be present.
3. A single hint can only be present in at most one platform.
4. `T` hint has precedence over other hints, however if it's present - a `*` hint, or
    2 heading hints are required.
5. There might be platforms without any direction hints, if they're used irregularly.
6. If there's no clear usage pattern for platforms (or if the pattern is not representable by the hint system),
    none of the platforms can have direction hints.

A pseudo-algorithm for matching a train to a platform based on the hints would be:

```py
BEARING_CODE_TO_DEGREES = {
    "N":   0, "NE":  45, "E":  90, "SE": 135,
    "S": 180, "SW": 225, "W": 270, "NW": 315,
}

if station.has_platform_with_hint("T") and (train.terminates_at(station) or train.starts_at(station)):
    return station.platform_with_hint("T")

if station.has_platform_with_hint("*"):
    return station.platform_with_hint("*")

# Bearing calculation
if train.terminates_at(station):
    # Special case when there's no next station
    train_heading = calculate_heading(previous_station, station)
else:
    train_heading = calculate_heading(station, next_station)

closest_hint = min(
    station.all_available_heading_hints(),
    key=lambda hint: abs(train_heading - BEARING_CODE_TO_DEGREES[hint]),
)
return station.platform_with_hint(closest_hint)
```
