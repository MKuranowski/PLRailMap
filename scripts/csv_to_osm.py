import xml.etree.ElementTree as etree
from argparse import ArgumentParser
import sys
import csv

# Parse CLI arguments

parser = ArgumentParser()
parser.add_argument(
    "-r",
    "--ref",
    type=int,
    default=-999000,
    help="upper bound for generated ref values",
)
args = parser.parse_args()

ref_enumerator = args.ref
assert isinstance(ref_enumerator, int)

# Prepare the root element

root = etree.Element("osm", {"version": "0.6", "generator": "plrailmap.scripts.csv_to_osm"})
tree = etree.ElementTree(root)

# Generate nodes

for station in csv.DictReader(sys.stdin):
    node = etree.Element(
        "node",
        {
            "id": str(ref_enumerator),
            "action": "modify",
            "visible": "true",
            "version": "1",
            "lat": station["lat"],
            "lon": station["lon"],
        },
    )
    node.append(etree.Element("tag", {"k": "railway", "v": "station"}))
    node.append(etree.Element("tag", {"k": "name", "v": station["name"]}))
    node.append(etree.Element("tag", {"k": "ref", "v": station["id"]}))
    if station.get("ibnr"):
        node.append(etree.Element("tag", {"k": "ref:ibnr", "v": station["ibnr"]}))
    node.append(etree.Element("tag", {"k": "fixme", "v": "verify"}))

    root.append(node)
    ref_enumerator -= 1

# Write to stdout

tree.write(sys.stdout.buffer, xml_declaration=True)
