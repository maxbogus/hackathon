"""Domain data helpers (transit stops, routes, ETA computation, geo catalog).

Pure functions plus read-only catalog loaders (`geo.py` reads the static
`data/external/stops_routes.json`). No FastAPI dependencies — tested in
isolation under `tests/`.
"""
