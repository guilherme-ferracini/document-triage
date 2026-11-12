"""python -m triage samples/inbox [--provider mock|anthropic|openai] [--out out/routing.csv]"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from .classify import rule_classifier, triage_folder
from .llm import LLMClient


def main() -> None:
    p = argparse.ArgumentParser(description="Classify and route documents received from clients")
    p.add_argument("inbox", type=Path)
    p.add_argument("--provider", default=None, help="mock (default, keyword rules), anthropic or openai")
    p.add_argument("--model", default=None)
    p.add_argument("--out", type=Path, default=None, help="write the routing table as CSV")
    a = p.parse_args()

    results = triage_folder(a.inbox, LLMClient(a.provider, a.model, mock_fn=rule_classifier))
    for r in results:
        print(f"{r.file:<34} {r.category:<20} -> {r.team:<14} conf {r.confidence:.2f}  "
              f"CNPJ {r.fields['cnpj'] or '-':<18}  date {r.fields['date'] or '-':<10}  R$ {r.fields['amount'] or '-'}")
        for w in r.warnings:
            print(f"{'':34} ! {w}")
    print("\nQueue sizes: " + ", ".join(f"{k}: {v}" for k, v in Counter(r.team for r in results).most_common()))

    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["file", "category", "team", "confidence", "cnpj", "date", "amount", "warnings"])
            for r in results:
                w.writerow([r.file, r.category, r.team, r.confidence, r.fields["cnpj"], r.fields["date"],
                            r.fields["amount"], " | ".join(r.warnings)])
        print(f"Routing table written to {a.out}")


if __name__ == "__main__":
    main()
