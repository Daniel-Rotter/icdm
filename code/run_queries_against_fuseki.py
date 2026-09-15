"""
run_queries_against_fuseki.py

Executes every .rq file in a directory against a running Fuseki dataset,
using the standard SPARQL 1.1 Protocol (a plain HTTP GET/POST with the
query passed as a form parameter), the same protocol any SPARQL client,
including Fuseki's own web UI, uses under the hood. No Fuseki-specific
client library is required.

Usage:
    python run_queries_against_fuseki.py \\
        --endpoint http://localhost:3030/icdm/sparql \\
        --queries queries/

Prerequisites (see the accompanying guide for full setup):
    1. materialize_ontology.py has been run, producing materialized.ttl
    2. Fuseki is running with that file loaded into a dataset
    3. `pip install requests` (the only dependency beyond the standard library)
"""

import argparse
import glob
import sys

import requests


def run_query(endpoint: str, query_text: str) -> dict:
    response = requests.post(
        endpoint,
        data={"query": query_text},
        headers={"Accept": "application/sparql-results+json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def print_results(name: str, results: dict) -> None:
    vars_ = results["head"]["vars"]
    bindings = results["results"]["bindings"]
    print(f"=== {name} ===")
    if not bindings:
        print("  (no results)")
    for row in bindings:
        values = []
        for v in vars_:
            if v in row:
                val = row[v]["value"]
                # Shorten full IRIs to their local name for readability
                short = val.split("#")[-1] if "#" in val else val
                values.append(short)
            else:
                values.append(None)
        print(" ", tuple(values))
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--endpoint",
        required=True,
        help="Fuseki SPARQL query endpoint, e.g. http://localhost:3030/icdm/sparql",
    )
    parser.add_argument(
        "--queries",
        default="queries/",
        help="Directory containing .rq files to run (default: queries/)",
    )
    args = parser.parse_args()

    query_files = sorted(glob.glob(f"{args.queries.rstrip('/')}/*.rq"))
    if not query_files:
        print(f"No .rq files found in {args.queries}", file=sys.stderr)
        return 1

    for qfile in query_files:
        with open(qfile, encoding="utf-8") as f:
            query_text = f.read()
        try:
            results = run_query(args.endpoint, query_text)
            print_results(qfile, results)
        except requests.exceptions.RequestException as e:
            print(f"=== {qfile} ===\n  REQUEST FAILED: {e}\n", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
