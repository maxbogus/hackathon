"""Domain data helpers (transit stops, routes, ETA computation).

Pure functions live here — no I/O, no FastAPI dependencies. Tested in
isolation under `tests/test_eta_compute.py` (T-127).
"""
