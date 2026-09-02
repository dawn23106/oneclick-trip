# Offline city fallback data

`cn-prefecture-cities.tsv` is derived from GeoNames `cities15000.zip` and keeps
only Chinese national/provincial/prefecture administrative centres (`PPLC`,
`PPLA`, and `PPLA2`). Chinese alternate names are preferred when present.

- Source: https://download.geonames.org/export/dump/cities15000.zip
- Dataset documentation: https://download.geonames.org/export/dump/readme.txt
- License: Creative Commons Attribution 4.0
- Attribution: GeoNames (https://www.geonames.org/)
- Snapshot generated: 2026-09-02

The runtime resolver uses this compact list only when the configured online
reverse-geocoding provider is unavailable. It performs a nearest-centre match;
it is not an administrative-boundary polygon lookup.
