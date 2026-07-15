"""CLI for roam-graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from roam_graph.roam import Roam, Audience


def main(argv=None):
    p = argparse.ArgumentParser(prog="roam-graph")
    p.add_argument("--root", required=True, help="directory to scan")
    p.add_argument("--out", default="roam-report.md", help="output report path")
    p.add_argument("--show", choices=["engineer", "philosopher", "builder", "agent", "explorer"], help="list docs in one audience")
    p.add_argument("--orphans", action="store_true", help="list orphan docs only")
    p.add_argument("--connected", type=int, default=10, help="top N most connected")
    args = p.parse_args(argv)

    r = Roam.from_directory(args.root)
    r.build_graph()

    if args.orphans:
        for n in r.orphans():
            print(f"{n.path}\t{n.title}")
        return 0

    if args.show:
        try:
            aud = Audience(args.show)
        except ValueError:
            print(f"unknown audience: {args.show}", file=sys.stderr)
            return 1
        for n in r.by_audience(aud, limit=200):
            print(f"{n.path}\t{n.title}\t{n.word_count}")
        return 0

    out = r.write(out_path=args.out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
