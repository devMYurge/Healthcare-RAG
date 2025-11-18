#!/usr/bin/env python3
"""Ingest medquad CSV into the backend documents API.

This script reads a CSV with columns like `question`, `answer`, `source`, `focus_area`
and creates a document per row by POSTing to the backend `/api/documents` endpoint.

Usage:
  python backend/scripts/ingest_medquad.py --file path/to/medquad.csv --backend http://localhost:8000

The script supports a --dry-run mode which prints what would be sent without posting.
"""
import argparse
import csv
import json
import os
import sys
import time
from typing import Optional

try:
    import requests
except Exception:
    print("Missing dependency: requests. Install with `pip install requests`.")
    raise


def ingest_file(file_path: str, backend_url: str, dry_run: bool = False, sleep: float = 0.0):
    api_url = backend_url.rstrip("/") + "/api/documents"
    count = 0
    with open(file_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            question = (row.get('question') or '').strip()
            answer = (row.get('answer') or '').strip()
            source = (row.get('source') or '').strip() or 'medquad'
            focus = (row.get('focus_area') or '').strip()

            # Skip empty rows
            if not question and not answer:
                continue

            content = f"Q: {question}\nA: {answer}".strip()
            metadata = {k: v for k, v in {'source': source, 'focus_area': focus}.items() if v}

            if dry_run:
                print(f"DRY RUN - would POST document #{count+1}:", {'content': content[:200], 'metadata': metadata})
            else:
                payload = {"content": content, "metadata": metadata}
                try:
                    resp = requests.post(api_url, json=payload, timeout=30)
                    if resp.ok:
                        try:
                            doc_id = resp.json().get('document_id')
                        except Exception:
                            doc_id = resp.text
                        print(f"OK   - ingested #{count+1} -> {doc_id}")
                    else:
                        print(f"FAIL - row #{count+1} -> status {resp.status_code}: {resp.text}")
                except Exception as e:
                    print(f"ERROR - row #{count+1} -> exception: {e}")

            count += 1
            if sleep:
                time.sleep(sleep)

    print(f"Finished. Processed {count} rows from {file_path}.")


def main(argv: Optional[list] = None):
    p = argparse.ArgumentParser(description="Ingest medquad CSV into backend documents API")
    p.add_argument('--file', '-f', default='medquad.csv', help='Path to medquad CSV file')
    p.add_argument('--backend', '-b', default=os.getenv('BACKEND_URL', 'http://localhost:8000'), help='Backend base URL')
    p.add_argument('--dry-run', action='store_true', help='Do not POST; just print what would be sent')
    p.add_argument('--sleep', type=float, default=0.0, help='Seconds to sleep between requests')
    args = p.parse_args(argv)

    if not os.path.exists(args.file):
        print(f"CSV file not found: {args.file}")
        sys.exit(2)

    ingest_file(args.file, args.backend, dry_run=args.dry_run, sleep=args.sleep)


if __name__ == '__main__':
    main()
