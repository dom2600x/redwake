"""Verify retained experiment bundles without network or model calls."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from redwake.artifacts import verify_bundle, verify_comparison_controls


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="*", type=Path)
    args = parser.parse_args(argv)
    bundles = args.bundles or sorted(p.parent for p in (ROOT / "docs" / "experiments").glob("*/manifest.json"))
    if not bundles:
        parser.error("No retained experiment bundles found")
    try:
        totals = [verify_bundle(p) for p in bundles]
    except (KeyError, OSError, TypeError, ValueError) as exc:
        print("Verification failed: " + str(exc), file=sys.stderr)
        return 1
    for row in totals:
        print("%(bundle)s: %(runs)d runs, %(files)d files verified offline." % row)
    print("%d saved runs/trials verified; no network or model calls." % sum(r["runs"] for r in totals))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
