#!/usr/bin/env python3
"""Guard for master_companies.csv. Stdlib only, no network.

  python3 csv_guard.py snapshot   # run BEFORE a scan: saves snapshots/master_companies_<timestamp>.csv
  python3 csv_guard.py diff       # run AFTER a scan: lists every changed row vs the latest snapshot

diff exits 1 if a resolved career_url was replaced by NOT_FOUND/empty, or a row disappeared.
"""
import csv, shutil, sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
CSV = BASE / "master_companies.csv"
SNAPS = BASE / "snapshots"

def load(p):
    return {r["name"]: (r.get("career_url") or "").strip() for r in csv.DictReader(open(p, newline=""))}

def is_live(u):
    return bool(u) and not u.startswith("NOT_FOUND")

def snapshot():
    SNAPS.mkdir(exist_ok=True)
    dest = SNAPS / f"master_companies_{datetime.now():%Y-%m-%d_%H%M%S}.csv"
    shutil.copy(CSV, dest)
    print(f"snapshot saved: {dest.name}")

def diff():
    snaps = sorted(SNAPS.glob("master_companies_*.csv"))
    if not snaps:
        sys.exit("no snapshot found. Run `csv_guard.py snapshot` before the scan.")
    old, new = load(snaps[-1]), load(CSV)
    bad, changed, added = [], [], [n for n in new if n not in old]
    for n, u in old.items():
        if n not in new:
            bad.append(f"ROW REMOVED: {n} (was {u})"); continue
        v = new[n]
        if u == v: continue
        if is_live(u) and not is_live(v):
            bad.append(f"RESOLVED URL LOST: {n}: {u} -> {v or '(empty)'}")
        else:
            changed.append(f"{n}: {u or '(empty)'} -> {v or '(empty)'}")
    print(f"compared against {snaps[-1].name}")
    print(f"rows: {len(old)} -> {len(new)} | live URLs: {sum(map(is_live, old.values()))} -> {sum(map(is_live, new.values()))}")
    print(f"\nNEW COMPANIES ({len(added)}): " + ", ".join(f"{n} [{new[n] or 'empty'}]" for n in added))
    print(f"\nCHANGED ({len(changed)}):"); [print("  " + c) for c in changed]
    print(f"\nPROBLEMS ({len(bad)}):"); [print("  " + b) for b in bad]
    sys.exit(1 if bad else 0)

if __name__ == "__main__" and len(sys.argv) == 2 and sys.argv[1] in ("snapshot", "diff"):
    snapshot() if sys.argv[1] == "snapshot" else diff()
else:
    sys.exit(__doc__)
