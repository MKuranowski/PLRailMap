PLRailMap
=========

This is a small repository with a OSM file with the Polish Railway Network.

This dataset is not yet complete. For now, it only contains station nodes for
the following operators:

- [x] PolRegio
- [x] Koleje Mazowieckie
- [x] PKP Intercity
- [ ] PKP SKM Trójmiasto
- [ ] SKM Warszawa (see <https://gist.github.com/MKuranowski/0ca97a012d541899cb1f859cd0bab2e7#file-rail_platforms-json>)
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

These tags are always required
- `railway=station`
- `name` - name of the station in the local language
- `ref` - PKP PLK code of the station (not necessarily an integer!)

`ref:ibnr` is available for most stations, but not all of them.

If the station name is not in Polish, `name:pl` should also be present.

