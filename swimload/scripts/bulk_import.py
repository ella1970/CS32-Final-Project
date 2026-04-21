#!/usr/bin/env python3
"""
scripts/bulk_import.py

Import all CSV files from a directory into a single subject+session batch.

Usage:
    python scripts/bulk_import.py \
        --dir /path/to/csv/exports \
        --subject SUB_001 \
        --injured-arm left \
        --age 22 \
        --base-url http://localhost:8000

CSV files should be named descriptively; the script uses the filename to
infer the arm side (looks for 'left' or 'right' in filename) and increments
session numbers automatically.
"""
import argparse
import os
import requests

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir',          required=True)
    parser.add_argument('--subject',      required=True, help='Subject code e.g. SUB_001')
    parser.add_argument('--injured-arm',  required=True, choices=['left','right'])
    parser.add_argument('--age',          type=int, default=None)
    parser.add_argument('--base-url',     default='http://localhost:8000')
    args = parser.parse_args()

    base = args.base_url.rstrip('/')

    # Create or get subject
    print(f"Creating subject {args.subject}…")
    try:
        r = requests.post(f'{base}/subjects', json={
            'code': args.subject,
            'age': args.age,
            'injured_arm': args.injured_arm
        })
        r.raise_for_status()
        subject = r.json()
    except requests.HTTPError:
        # May already exist — look it up
        subjects = requests.get(f'{base}/subjects').json()
        subject  = next((s for s in subjects if s['code'] == args.subject), None)
        if not subject:
            print('Failed to create or find subject'); return

    print(f"Subject ID: {subject['id']}")
    subject_id = subject['id']

    csv_files = sorted(f for f in os.listdir(args.dir) if f.endswith('.csv'))
    if not csv_files:
        print(f"No CSV files found in {args.dir}")
        return

    for i, fname in enumerate(csv_files, start=1):
        # Infer arm side from filename
        fname_lower = fname.lower()
        if 'right' in fname_lower:
            arm = 'right'
        elif 'left' in fname_lower:
            arm = 'left'
        else:
            arm = args.injured_arm  # default to injured arm if not specified
            print(f"  [{fname}] arm side not in filename, defaulting to {arm}")

        fpath = os.path.join(args.dir, fname)
        print(f"[{i}/{len(csv_files)}] {fname} → arm={arm}")

        # Start session
        r = requests.post(f'{base}/sessions/start', json={
            'subject_id': subject_id,
            'arm_side': arm,
            'session_number': i,
        })
        r.raise_for_status()
        session = r.json()
        session_id = session['id']
        print(f"  Session #{i} started (id={session_id})")

        # Upload CSV
        with open(fpath, 'rb') as f:
            r = requests.post(f'{base}/imu/{session_id}/upload_csv',
                              files={'file': (fname, f, 'text/csv')})
            r.raise_for_status()
            result = r.json()
        print(f"  Inserted {result['inserted']} samples")

        # End session (no pain score for historical data)
        r = requests.post(f'{base}/sessions/{session_id}/end', json={})
        r.raise_for_status()
        print(f"  Session ended, load computed")

    print(f"\nDone. Imported {len(csv_files)} sessions for {args.subject}")

if __name__ == '__main__':
    main()
