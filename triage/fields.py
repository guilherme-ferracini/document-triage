"""Deterministic field extraction: CNPJ (with check-digit validation), dates and amounts."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import List, Optional

CNPJ_RE = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
DATE_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
AMOUNT_RE = re.compile(r"R\$\s*([\d.]+,\d{2})")


def cnpj_is_valid(cnpj: str) -> bool:
    digits = re.sub(r"\D", "", cnpj)
    if len(digits) != 14 or len(set(digits)) == 1:
        return False

    def check(base: str, weights: List[int]) -> str:
        total = sum(int(d) * w for d, w in zip(base, weights))
        rest = total % 11
        return "0" if rest < 2 else str(11 - rest)

    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6] + w1
    d1 = check(digits[:12], w1)
    d2 = check(digits[:12] + d1, w2)
    return digits[12:] == d1 + d2


def cnpjs(text: str) -> List[str]:
    return [c for c in CNPJ_RE.findall(text)]


def first_date(text: str) -> Optional[date]:
    m = DATE_RE.search(text)
    if not m:
        return None
    d, mth, y = map(int, m.groups())
    try:
        return date(y, mth, d)
    except ValueError:
        return None


def largest_amount(text: str) -> Optional[Decimal]:
    values = [Decimal(v.replace(".", "").replace(",", ".")) for v in AMOUNT_RE.findall(text)]
    return max(values) if values else None
