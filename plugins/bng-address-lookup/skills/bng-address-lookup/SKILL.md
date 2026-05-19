---
name: bng-address-lookup
description: >
  Look up the closest addresses to a location using the British National Grid (BNG)
  Buchanan Gazetteer API. Use this skill whenever the user wants to find addresses
  near a grid reference or easting/northing coordinate, look up what's at a BNG
  location, geocode coordinates to addresses, or batch-process a list of grid
  references from a CSV file. Trigger on phrases like "find addresses near",
  "what's at grid ref", "look up coordinates", "geocode these", "nearest address
  to", or whenever the user provides easting/northing (X/Y) values or a CSV of
  grid references. Always save results to a downloadable CSV file.
---

# BNG Address Lookup

You have access to the Buchanan Gazetteer address search API, which returns the
closest postal addresses to a given British National Grid (or other CRS) coordinate.

## API Details

**Endpoint:** `https://gaz.buchananservices.uk/addsearch/v2/georef/address`

**Auth:** the script appends `api_token=...` as a query parameter. The token is
read from the `BNG_API_TOKEN` environment variable — **no fallback is shipped**.
If the variable is unset, the script exits with an error before making any API
calls.

**Parameters:**

| Param    | Description                                  | Default |
|----------|----------------------------------------------|---------|
| `coordx` | Easting (X) coordinate                       | required |
| `coordy` | Northing (Y) coordinate                      | required |
| `epsg`   | Coordinate reference system code             | `27700` (British National Grid) |
| `limit`  | Max results to return per query              | `5` |
| `page`   | Pagination page number                       | `1` |

## Modes of Operation

### Single query
The user gives you a coordinate pair (easting + northing), or describes a location
with grid ref values. Parse the numbers, run the lookup script, and return results.

### Batch mode
The user provides a CSV file with coordinates for multiple locations. The CSV must
contain at minimum `coordX` and `coordY` columns (case-insensitive). Any other
columns are treated as metadata and passed through to the output unchanged —
this is useful for keeping site names, IDs, or other context alongside results.

Optional per-row overrides in the CSV: `epsg`, `limit`.

## Steps — follow these every time

1. **Check the API token is configured.** Run `printenv BNG_API_TOKEN` (or
   `echo "${BNG_API_TOKEN:-MISSING}"`). If it prints `MISSING` or is empty:
   - Ask the user for their Buchanan Gazetteer API token. Do *not* invent one.
   - For the current call, prefix the python command with
     `BNG_API_TOKEN=<token> python3 ...` so the value is passed inline and not
     persisted into shell history beyond the current command.
   - After the lookup succeeds, offer to persist it: tell the user they can add
     `export BNG_API_TOKEN=<token>` to `~/.zshrc` (or `~/.bashrc`) so they
     won't be asked again. Do *not* write to their shell rc without their
     explicit OK.
   Never paste or log the token in your text replies to the user.

2. **Determine the mode** — is the user giving you a single coordinate pair, or
   a CSV file with multiple coordinates?

3. **Find the script** — it lives at `scripts/lookup.py` in this skill's directory.
   You can find the skill directory by looking at where this SKILL.md file is.

4. **Construct the output path** — pick a writable location:
   - If the environment defines `CLAUDE_OUTPUT_DIR`, use that.
   - Otherwise default to `/tmp/bng_outputs/` (created automatically if missing).
   - File name: `bng_results_<timestamp>.csv` where `<timestamp>` is the current
     date/time (e.g. `20260519_143022`).

5. **Run the script** with the correct subcommand (see below). Use `python3`,
   not `python` — many systems (incl. recent macOS) only have `python3` on `PATH`.

6. **Share the file** with the user — give them the full path and a brief
   human-readable summary, e.g. "Found 5 addresses for your coordinate" or
   "Processed 12 locations — results saved."

## Running the Script

**Single coordinate:**
```bash
python3 <skill_dir>/scripts/lookup.py single \
  --coordx <X> \
  --coordy <Y> \
  --epsg 27700 \
  --limit 5 \
  --output <output_path>
```

**Batch from CSV:**
```bash
python3 <skill_dir>/scripts/lookup.py batch \
  --input <csv_file_path> \
  --epsg 27700 \
  --limit 5 \
  --output <output_path>
```

The `--epsg` and `--limit` flags set the *defaults* for the batch run; individual
rows can override them with their own `epsg` or `limit` columns.

## Output Format

The script produces a CSV where every row is one address result. Columns include:

- `query_coordx`, `query_coordy` — the input coordinates, for traceability
- All address fields returned by the API (automatically extracted from the JSON)
- Any passthrough columns from the input CSV (batch mode)
- `error` — only present if a lookup failed; contains the error message

If a lookup fails for a particular row (e.g. no results, API error), that row
will appear in the output with an `error` value instead of address data. In batch
mode, the script continues to the next row rather than stopping.

## Edge Cases

- **Coordinates not recognised**: If the user's message contains coordinates but
  you're not sure which is X (easting) and which is Y (northing), ask — BNG
  eastings are typically 6 digits (e.g. 530000), northings also 6 digits but a
  different range.
- **Missing CSV columns**: If the CSV lacks `coordX` or `coordY`, tell the user
  and stop — don't guess at column names.
- **EPSG not specified**: Default to `27700` (British National Grid). If the user
  seems to be giving lat/long values (small numbers like 51.5, -0.1), ask whether
  they mean WGS84 (`4326`) and use that instead.
- **Large batches**: The API is called once per row. For very large CSVs (hundreds
  of rows), let the user know it may take a moment.
