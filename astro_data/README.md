# Swiss Ephemeris data

Place the Swiss Ephemeris `.se1/.se2` data files in this directory (or set `SWISSEPH_DATA_PATH` to another location).

Suggested flow:
- Download the ephemeris data archives from the official Swiss Ephemeris distribution (e.g., the `sea*.zip` bundles).
- Extract the contents directly into this folder so files like `sepl_18.se1` are present at the top level.
- Mount the same path inside Docker/production (`/app/astro_data` by default) so pyswisseph can locate the files.
- Keep these files out of source control; only this README and `.gitkeep` are tracked.
