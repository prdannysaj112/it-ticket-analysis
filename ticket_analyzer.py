#!/usr/bin/env python3
"""
IT Support Ticket Analysis Tool (college-level)

What it does:
- Reads tickets from CSV (real or sample)
- Auto-categorizes tickets using keyword rules
- Produces summary stats (top categories, priority distribution, recurring issues)
- Exports JSON report to ./output

This mirrors entry-level IT ops / SOC triage thinking: pattern recognition + reporting.
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

CATEGORY_RULES: Dict[str, List[str]] = {
    "Password / Account Access": ["password", "locked out", "lockout", "mfa", "2fa", "reset"],
    "Network / Connectivity": ["wifi", "dns", "dhcp", "cannot connect", "no internet", "network"],
    "VPN / Remote Access": ["vpn", "remote access", "tunnel", "auth failed"],
    "Email / Collaboration": ["outlook", "mailbox", "email", "teams", "google drive"],
    "Hardware / Peripherals": ["printer", "keyboard", "mouse", "monitor", "dock"],
    "Performance / OS Issues": ["slow", "disk usage", "blue screen", "update", "crash"],
    "Security / Phishing": ["phishing", "suspicious email", "malware", "ransomware", "spoof"],
    "Permissions / Access Control": ["permission", "access request", "shared drive", "role", "privilege"],
}

PRIORITY_ORDER = {"Low": 1, "Medium": 2, "High": 3}


@dataclass
class Ticket:
    ticket_id: str
    created_at: str
    subject: str
    description: str
    priority: str
    status: str
    assigned_team: str
    category: str


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def categorize(subject: str, description: str) -> str:
    blob = normalize(subject) + " " + normalize(description)
    best_cat = "Other"
    best_hits = 0
    for cat, keywords in CATEGORY_RULES.items():
        hits = sum(1 for k in keywords if k in blob)
        if hits > best_hits:
            best_hits = hits
            best_cat = cat
    return best_cat


def read_tickets(csv_path: Path) -> List[Ticket]:
    tickets: List[Ticket] = []
    with csv_path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row.get("category_hint") or categorize(row.get("subject", ""), row.get("description", ""))
            tickets.append(Ticket(
                ticket_id=row.get("ticket_id", ""),
                created_at=row.get("created_at", ""),
                subject=row.get("subject", ""),
                description=row.get("description", ""),
                priority=row.get("priority", "Low"),
                status=row.get("status", ""),
                assigned_team=row.get("assigned_team", ""),
                category=cat
            ))
    return tickets


def build_report(tickets: List[Ticket]) -> dict:
    total = len(tickets)
    cat_counts = Counter(t.category for t in tickets)
    pri_counts = Counter(t.priority for t in tickets)
    status_counts = Counter(t.status for t in tickets)

    # Recurring issue signals: normalize subjects
    subject_counts = Counter(normalize(t.subject) for t in tickets if t.subject)
    recurring = [{"subject": s, "count": c} for s, c in subject_counts.most_common(8)]

    # “Risky” tickets (security + high priority)
    risky = [
        asdict(t) for t in sorted(
            [t for t in tickets if t.category == "Security / Phishing" or t.priority == "High"],
            key=lambda x: PRIORITY_ORDER.get(x.priority, 0),
            reverse=True
        )[:10]
    ]

    return {
        "summary": {
            "total_tickets": total,
            "top_categories": cat_counts.most_common(6),
            "priority_distribution": pri_counts,
            "status_distribution": status_counts,
        },
        "recurring_issues": recurring,
        "high_risk_samples": risky,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/sample_tickets.csv", help="Path to tickets CSV file")
    ap.add_argument("--out", default="output/ticket_report.json", help="Output report path")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    out_path = Path(args.out)
    out_path.parent.mkdir(exist_ok=True)

    tickets = read_tickets(csv_path)
    report = build_report(tickets)

    out_path.write_text(json.dumps(report, indent=2))
    print("\n=== Ticket Analysis Summary ===")
    print(f"Total tickets: {report['summary']['total_tickets']}")
    print("Top categories:")
    for cat, count in report["summary"]["top_categories"]:
        print(f"  - {cat}: {count}")
    print(f"\nSaved report -> {out_path}\n")


if __name__ == "__main__":
    main()
