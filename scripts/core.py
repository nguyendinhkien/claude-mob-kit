#!/usr/bin/env python3
"""Shared utilities for loading and searching CSV data."""

import csv
import json
import os
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DOMAIN_MAP = {
    "app_type": "mobile-app-types.csv",
    "colors": "mobile-colors.csv",
    "typography": "mobile-typography.csv",
    "components": "mobile-components.csv",
    "tokens": "platform-tokens.csv",
    "ux": "mobile-ux-guidelines.csv",
    "reasoning": "mobile-reasoning.csv",
}


def load_csv(filename: str) -> list[dict]:
    """Load a CSV file from the data directory and return a list of dicts."""
    filepath = DATA_DIR / filename
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _score_row(row: dict, query: str) -> int:
    """Score a row against a query string. Higher is better."""
    query_lower = query.lower()
    keywords = query_lower.split()
    score = 0

    for value in row.values():
        val_lower = str(value).lower()
        if val_lower == query_lower:
            score += 10
        elif query_lower in val_lower:
            score += 3
        else:
            for kw in keywords:
                if kw in val_lower:
                    score += 1

    return score


def search(query: str, domain: str, max_results: int = 3) -> dict:
    """Search a CSV domain for rows matching the query.

    Returns a dict with a "results" key containing the top matches.
    """
    filename = DOMAIN_MAP.get(domain)
    if not filename:
        return {"error": f"Unknown domain '{domain}'. Valid: {list(DOMAIN_MAP.keys())}"}

    rows = load_csv(filename)
    scored = [(row, _score_row(row, query)) for row in rows]
    scored = [(r, s) for r, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)

    results = []
    for row, score in scored[:max_results]:
        results.append({**row, "_score": score})

    return {"results": results, "query": query, "domain": domain, "total_matches": len(scored)}


def get_by_app_type(app_type: str, domain: str) -> dict | None:
    """Get a single row by exact App_Type match (case-insensitive)."""
    filename = DOMAIN_MAP.get(domain)
    if not filename:
        return None

    rows = load_csv(filename)
    app_type_lower = app_type.lower()
    for row in rows:
        if row.get("App_Type", "").lower() == app_type_lower:
            return row

    return None


def main():
    if len(sys.argv) < 3:
        print("Usage: python core.py search <query> <domain> [max_results]")
        print("       python core.py get <app_type> <domain>")
        print(f"\nDomains: {list(DOMAIN_MAP.keys())}")
        sys.exit(1)

    command = sys.argv[1]

    if command == "search":
        query = sys.argv[2]
        domain = sys.argv[3] if len(sys.argv) > 3 else "app_type"
        max_results = int(sys.argv[4]) if len(sys.argv) > 4 else 3
        result = search(query, domain, max_results)
        print(json.dumps(result, indent=2))

    elif command == "get":
        app_type = sys.argv[2]
        domain = sys.argv[3] if len(sys.argv) > 3 else "app_type"
        result = get_by_app_type(app_type, domain)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps({"error": f"No match for app_type='{app_type}' in domain='{domain}'"}))

    else:
        print(f"Unknown command '{command}'. Use 'search' or 'get'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
