#!/usr/bin/env python3
"""
BNG Address Lookup Script
=========================
Queries the Buchanan Gazetteer API for the closest addresses to a
British National Grid coordinate (or any EPSG-specified CRS).

Usage
-----
Single coordinate:
    python3 lookup.py single --coordx 530000 --coordy 180000 --output results.csv

Batch from CSV:
    python3 lookup.py batch --input coords.csv --output results.csv

The CSV for batch mode must contain at minimum `coordX` and `coordY` columns
(case-insensitive). All other columns are passed through to the output.

Authentication
--------------
Reads the API token from the BNG_API_TOKEN environment variable.
The script exits with an error if it is not set.
"""

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ── API configuration ──────────────────────────────────────────────────────────
API_BASE = "https://gaz.buchananservices.uk/addsearch/v2/georef/address"
API_TOKEN_ENV = "BNG_API_TOKEN"
DEFAULT_EPSG = "27700"
DEFAULT_LIMIT = "5"
DEFAULT_PAGE = "1"
REQUEST_TIMEOUT = 20  # seconds


# ── API call ───────────────────────────────────────────────────────────────────
def call_api(coordx, coordy, epsg=DEFAULT_EPSG, limit=DEFAULT_LIMIT, page=DEFAULT_PAGE):
    """
    Call the gazetteer API for a single coordinate.
    Returns (parsed_json, error_string). One of these will be None.
    """
    token = os.environ.get(API_TOKEN_ENV)
    if not token:
        return None, (
            f"Missing API token: set the {API_TOKEN_ENV} environment variable "
            f"to your Buchanan Gazetteer token before running this script."
        )

    params = {
        "api_token": token,
        "coordx": str(coordx),
        "coordy": str(coordy),
        "epsg": str(epsg),
        "limit": str(limit),
        "page": str(page),
    }
    url = f"{API_BASE}?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body), None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return None, f"HTTP {e.code}: {body[:200]}"
    except urllib.error.URLError as e:
        return None, f"Connection error: {e.reason}"
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in response: {e}"
    except Exception as e:
        return None, str(e)


# ── JSON flattening ────────────────────────────────────────────────────────────
def flatten(obj, prefix="", sep="_"):
    """
    Recursively flatten a nested dict/list into a single-level dict.

    {"address": {"street": "High St", "postcode": "AB1 2CD"}}
    → {"address_street": "High St", "address_postcode": "AB1 2CD"}
    """
    items = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{prefix}{sep}{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                items.update(flatten(v, new_key, sep))
            else:
                items[new_key] = v
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{prefix}{sep}{i}" if prefix else str(i)
            if isinstance(v, (dict, list)):
                items.update(flatten(v, new_key, sep))
            else:
                items[new_key] = v
    else:
        items[prefix] = obj
    return items


def extract_results(data):
    """
    Pull the list of address records out of the API response.

    The API may return results under different top-level keys depending on
    the endpoint version. We try the most common patterns in order.
    """
    if isinstance(data, list):
        return data

    for key in ("results", "addresses", "data", "features", "items", "records"):
        val = data.get(key)
        if isinstance(val, list):
            return val

    # If the response itself looks like a single address record, wrap it.
    return [data]


# ── Output helpers ─────────────────────────────────────────────────────────────
def priority_columns():
    """Return columns that should appear first in the CSV, in order."""
    return ["query_coordx", "query_coordy", "error"]


def write_csv(rows, output_path):
    """Write a list of dicts to CSV, with priority columns first."""
    if not rows:
        print("No data to write — the output file will be empty.")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("query_coordx,query_coordy,error\n")
        return

    prio = priority_columns()
    # Collect all keys encountered across all rows, in stable insertion order
    seen = dict.fromkeys(prio)
    for row in rows:
        seen.update(dict.fromkeys(row.keys()))
    all_keys = [k for k in seen if any(k in row for row in rows)]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def make_result_rows(data, coordx, coordy, metadata=None):
    """
    Convert an API response into a list of output row dicts.
    Each address result in the response becomes one row.
    """
    metadata = metadata or {}
    results = extract_results(data)

    if not results:
        return [{
            **metadata,
            "query_coordx": coordx,
            "query_coordy": coordy,
            "error": "No results returned by API",
        }]

    rows = []
    for item in results:
        flat = flatten(item)
        row = {
            "query_coordx": coordx,
            "query_coordy": coordy,
            **flat,
            **metadata,  # metadata (passthrough CSV cols) wins on key conflict
        }
        rows.append(row)
    return rows


# ── Single mode ────────────────────────────────────────────────────────────────
def lookup_single(coordx, coordy, epsg, limit, output_path):
    print(f"Looking up addresses near ({coordx}, {coordy}) [EPSG:{epsg}] ...")
    data, err = call_api(coordx, coordy, epsg, limit)

    if err:
        rows = [{
            "query_coordx": coordx,
            "query_coordy": coordy,
            "error": err,
        }]
        print(f"  ✗ API error: {err}", file=sys.stderr)
    else:
        rows = make_result_rows(data, coordx, coordy)
        print(f"  ✓ {len(rows)} result(s) found")

    write_csv(rows, output_path)
    print(f"\nResults saved to: {output_path}")
    return len(rows)


# ── Batch mode ─────────────────────────────────────────────────────────────────
COORD_COLS = {"coordx", "coordy"}
PARAM_COLS = {"coordx", "coordy", "epsg", "limit", "page"}


def lookup_batch(input_csv, epsg_default, limit_default, output_path):
    # ── Read the input CSV ──────────────────────────────────────────────────
    with open(input_csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)
        raw_headers = reader.fieldnames or []

    if not raw_rows:
        print("ERROR: The input CSV is empty.", file=sys.stderr)
        sys.exit(1)

    # Normalise header names for lookup (keep originals for passthrough)
    norm_headers = [h.lower().strip() for h in raw_headers]

    missing = COORD_COLS - set(norm_headers)
    if missing:
        print(
            f"ERROR: CSV is missing required column(s): {', '.join(sorted(missing))}.\n"
            f"  Found columns: {', '.join(raw_headers)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build a map from normalised name → original header name
    norm_to_orig = {h.lower().strip(): h for h in raw_headers}

    # ── Process each row ────────────────────────────────────────────────────
    all_output_rows = []
    total = len(raw_rows)

    for i, raw_row in enumerate(raw_rows, start=1):
        # Normalise keys for this row
        row = {k.lower().strip(): v for k, v in raw_row.items()}

        coordx = row.get("coordx", "").strip()
        coordy = row.get("coordy", "").strip()
        epsg = row.get("epsg", epsg_default).strip() or epsg_default
        limit = row.get("limit", limit_default).strip() or limit_default

        # Passthrough metadata: everything that isn't a param column
        metadata = {
            norm_to_orig.get(k, k): v
            for k, v in raw_row.items()
            if k.lower().strip() not in PARAM_COLS
        }

        print(f"[{i}/{total}] ({coordx}, {coordy}) EPSG:{epsg} limit:{limit} ...", end=" ")

        if not coordx or not coordy:
            print("SKIP — missing coordinates")
            all_output_rows.append({
                **metadata,
                "query_coordx": coordx,
                "query_coordy": coordy,
                "error": "Missing coordinate value(s)",
            })
            continue

        data, err = call_api(coordx, coordy, epsg, limit)

        if err:
            print(f"ERROR — {err}")
            all_output_rows.append({
                **metadata,
                "query_coordx": coordx,
                "query_coordy": coordy,
                "error": err,
            })
        else:
            rows = make_result_rows(data, coordx, coordy, metadata)
            print(f"{len(rows)} result(s)")
            all_output_rows.extend(rows)

    # ── Write output ────────────────────────────────────────────────────────
    write_csv(all_output_rows, output_path)
    errors = sum(1 for r in all_output_rows if r.get("error"))
    print(
        f"\nDone. {total} coordinate(s) processed → "
        f"{len(all_output_rows)} result row(s) written "
        f"({errors} error(s)).\nSaved to: {output_path}"
    )
    return len(all_output_rows)


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Look up closest addresses to BNG/grid coordinates via the Buchanan Gazetteer API."
    )
    sub = parser.add_subparsers(dest="mode", required=True, metavar="{single,batch}")

    # single ──────────────────────────────────────────────────────────────────
    p_single = sub.add_parser("single", help="Look up a single coordinate pair")
    p_single.add_argument("--coordx", required=True, help="Easting (X) value")
    p_single.add_argument("--coordy", required=True, help="Northing (Y) value")
    p_single.add_argument("--epsg", default=DEFAULT_EPSG, help=f"CRS code (default: {DEFAULT_EPSG})")
    p_single.add_argument("--limit", default=DEFAULT_LIMIT, help=f"Max results (default: {DEFAULT_LIMIT})")
    p_single.add_argument("--output", required=True, help="Path for the output CSV")

    # batch ───────────────────────────────────────────────────────────────────
    p_batch = sub.add_parser("batch", help="Process a CSV of coordinate pairs")
    p_batch.add_argument("--input", required=True, help="Path to input CSV")
    p_batch.add_argument("--epsg", default=DEFAULT_EPSG, help=f"Default CRS code (default: {DEFAULT_EPSG})")
    p_batch.add_argument("--limit", default=DEFAULT_LIMIT, help=f"Default max results per row (default: {DEFAULT_LIMIT})")
    p_batch.add_argument("--output", required=True, help="Path for the output CSV")

    args = parser.parse_args()

    if not os.environ.get(API_TOKEN_ENV):
        print(
            f"ERROR: the {API_TOKEN_ENV} environment variable is not set.\n"
            f"  Get a token from Buchanan Services and run:\n"
            f"    export {API_TOKEN_ENV}=your-token-here\n"
            f"  Or pass it inline:\n"
            f"    {API_TOKEN_ENV}=your-token-here python3 {sys.argv[0]} ...",
            file=sys.stderr,
        )
        sys.exit(2)

    if args.mode == "single":
        lookup_single(args.coordx, args.coordy, args.epsg, args.limit, args.output)
    elif args.mode == "batch":
        lookup_batch(args.input, args.epsg, args.limit, args.output)


if __name__ == "__main__":
    main()
