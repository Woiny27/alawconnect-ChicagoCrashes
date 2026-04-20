"""
run_audit.py — CLI entrypoint for security and civic alert audits.

Usage
-----
# Security: scan a portal for sequential ID vulnerabilities
python -m src.audit.run_audit security \\
    --url https://example.gov/crashes/report/ \\
    --ids 2501001 2501002 2501003

# Civic: detect crash clusters and generate victim support alerts
python -m src.audit.run_audit civic \\
    --input data/merged_output.csv \\
    --clusters-out data/cluster_alerts.csv \\
    --support-out data/support_alerts.csv \\
    --min-crashes 3

# PII scan: check a live portal URL for PII leakage
python -m src.audit.run_audit pii \\
    --url https://example.gov/crashes/report/2501001
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def _cmd_security(args: argparse.Namespace) -> None:
    from src.audit.portal_security import SequentialIDScanner

    scanner = SequentialIDScanner(
        base_url=args.url,
        request_delay_s=args.delay,
    )
    report = scanner.run(sample_ids=args.ids)

    print(f"\n=== Sequential ID Audit: {report.portal_url} ===")
    print(f"IDs probed : {len(report.ids_probed)}")
    print(f"Hit rate   : {report.hit_rate:.0%}")
    print(f"Gap rate   : {report.gap_rate:.0%}  (consecutive-ID density)")
    print(f"Severity   : {report.severity.value}")
    print(f"\nRecommendation:\n  {report.recommendation}\n")

    if report.findings:
        print("Findings:")
        for f in report.findings:
            print(f"  [{f.severity.value}] {f.category}: {f.description}")
            if f.evidence:
                print(f"           Evidence: {f.evidence}")


def _cmd_pii(args: argparse.Namespace) -> None:
    import requests
    from src.audit.portal_security import PIILeakageScanner

    print(f"Fetching {args.url} …")
    try:
        resp = requests.get(args.url, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        print(f"ERROR: Could not fetch URL — {exc}", file=sys.stderr)
        sys.exit(1)

    scanner = PIILeakageScanner(redact_samples=not args.no_redact)
    findings = scanner.scan(html, source_url=args.url)
    print(scanner.summary(findings))


def _cmd_civic(args: argparse.Namespace) -> None:
    from src.audit.civic_alerts import CrashClusterDetector, VictimSupportTrigger

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(input_path, low_memory=False)
    print(f"Loaded {len(df):,} rows from {input_path}")

    # --- Cluster detection ---
    detector = CrashClusterDetector(min_crashes=args.min_crashes)
    clusters = detector.detect(df)
    print(f"\n=== Crash Cluster Alerts ({len(clusters)} segments flagged) ===")
    for c in clusters[:10]:
        print(
            f"  [{c.severity_label:10s}] score={c.risk_score:5.1f}  "
            f"{c.crash_count} crashes  {c.injury_count} injured  {c.fatal_count} fatal  "
            f"— {c.segment_key}"
        )
    if len(clusters) > 10:
        print(f"  … ({len(clusters) - 10} more)")

    if args.clusters_out:
        out = Path(args.clusters_out)
        detector.to_dataframe(clusters).to_csv(out, index=False)
        print(f"\nCluster alerts saved to: {out}")

    # --- Victim support triggers ---
    trigger = VictimSupportTrigger(city=args.city)
    alerts = trigger.evaluate(df)
    print(f"\n=== Victim Support Alerts ({len(alerts)} rows triggered) ===")
    for a in alerts[:5]:
        print(
            f"  {a.injury_severity:30s}  {a.crash_date[:10]}  "
            f"{a.location_desc or '(no location)'}  "
            f"contact: {a.contact_name or '(none)'}"
        )
    if len(alerts) > 5:
        print(f"  … ({len(alerts) - 5} more)")

    if args.support_out:
        out = Path(args.support_out)
        trigger.to_dataframe(alerts).to_csv(out, index=False)
        print(f"\nSupport alerts saved to: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="run_audit",
        description="Civic security and crash alert auditing tool.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- security subcommand --
    sec = sub.add_parser("security", help="Sequential ID enumeration audit")
    sec.add_argument("--url",   required=True, help="Portal base URL")
    sec.add_argument("--ids",   nargs="+", required=True, metavar="ID", help="Report IDs to probe")
    sec.add_argument("--delay", type=float, default=1.0, help="Seconds between requests (default 1.0)")

    # -- pii subcommand --
    pii = sub.add_parser("pii", help="PII leakage scan on a portal URL")
    pii.add_argument("--url", required=True, help="Full URL of the page to scan")
    pii.add_argument("--no-redact", action="store_true", help="Show full unredacted matches (secure environments only)")

    # -- civic subcommand --
    civ = sub.add_parser("civic", help="Crash cluster detection and victim support alerts")
    civ.add_argument("--input",        required=True, help="Path to merged_output.csv")
    civ.add_argument("--min-crashes",  type=int, default=3, help="Minimum crashes to flag a segment (default 3)")
    civ.add_argument("--city",         default="chicago", help="City key for support resource URLs (default: chicago)")
    civ.add_argument("--clusters-out", default="", metavar="PATH", help="Write cluster alerts CSV here")
    civ.add_argument("--support-out",  default="", metavar="PATH", help="Write victim support alerts CSV here")

    args = parser.parse_args()

    if args.command == "security":
        _cmd_security(args)
    elif args.command == "pii":
        _cmd_pii(args)
    elif args.command == "civic":
        _cmd_civic(args)


if __name__ == "__main__":
    main()
